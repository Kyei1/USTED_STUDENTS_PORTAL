"""GPA calculation and grading utilities for the USTED Students Portal."""


def score_to_point(score):
    """Convert numeric score to grade point (0.0-4.0)."""
    if score >= 80:
        return 4.0
    if score >= 75:
        return 3.5
    if score >= 70:
        return 3.0
    if score >= 65:
        return 2.5
    if score >= 60:
        return 2.0
    if score >= 55:
        return 1.5
    if score >= 50:
        return 1.0
    return 0.0


def classify_cgpa(cgpa):
    """Return degree classification metadata for a CGPA value."""
    try:
        value = float(cgpa)
    except (TypeError, ValueError):
        value = 0.0

    value = max(0.0, min(4.0, value))

    if value >= 3.5:
        return {
            'label': 'First Class Honours',
            'badge_class': '',
            'badge_style': 'background: var(--usted-gold); color: var(--usted-ink);',
        }
    if value >= 3.0:
        return {
            'label': 'Second Class Honours (Upper Division)',
            'badge_class': 'bg-success',
            'badge_style': '',
        }
    if value >= 2.5:
        return {
            'label': 'Second Class Honours (Lower Division)',
            'badge_class': 'bg-primary',
            'badge_style': '',
        }
    if value >= 2.0:
        return {
            'label': 'Third Class Honours',
            'badge_class': 'bg-warning text-dark',
            'badge_style': '',
        }
    if value >= 1.0:
        return {
            'label': 'Pass',
            'badge_class': 'bg-secondary',
            'badge_style': '',
        }
    return {
        'label': 'Fail / Complete Withdrawal',
        'badge_class': 'bg-danger',
        'badge_style': '',
    }


def score_to_letter(score):
    """Convert numeric score to letter grade."""
    if score >= 80:
        return 'A'
    if score >= 75:
        return 'B+'
    if score >= 70:
        return 'B'
    if score >= 65:
        return 'C+'
    if score >= 60:
        return 'C'
    if score >= 55:
        return 'D+'
    if score >= 50:
        return 'D'
    return 'E'


def point_to_min_total_score(grade_point):
    """Convert grade point to minimum total score required."""
    if grade_point >= 4.0:
        return 80
    if grade_point >= 3.5:
        return 75
    if grade_point >= 3.0:
        return 70
    if grade_point >= 2.5:
        return 65
    if grade_point >= 2.0:
        return 60
    if grade_point >= 1.5:
        return 55
    if grade_point >= 1.0:
        return 50
    return 0


def scaled_exam_score(raw_exam_score):
    """Scale raw exam score (0-100) to exam component score (0-60)."""
    return (raw_exam_score / 100.0) * 60.0


def course_difficulty_weight(course):
    """Calculate difficulty weight for a course based on type and credit hours."""
    # Higher values indicate relatively harder courses.
    type_weight = {
        'Core': 1.25,
        'General': 1.0,
        'Elective': 0.9,
    }
    base = type_weight.get(course.course_type, 1.0)
    credit_adjustment = max(course.credit_hours - 2, 0) * 0.08
    return base + credit_adjustment


def difficulty_label(weight):
    """Convert difficulty weight to human-readable label."""
    if weight >= 1.3:
        return 'High'
    if weight >= 1.05:
        return 'Medium'
    return 'Low'


def allocate_uneven_target_points(active_enrollments, target_sgpa):
    """
    Allocate required grade points across active enrollments to achieve a target SGPA.
    
    Uses weighted allocation: easier courses get higher targets first, harder courses
    get lower targets to balance the workload.
    """
    total_credit_hours = sum(enrollment.course.credit_hours for enrollment in active_enrollments)
    if not total_credit_hours:
        return []

    rows = []
    for enrollment in active_enrollments:
        weight = course_difficulty_weight(enrollment.course)
        inverse_weight = 1.0 / weight if weight else 1.0
        rows.append(
            {
                'enrollment': enrollment,
                'credit_hours': enrollment.course.credit_hours,
                'difficulty_weight': weight,
                'inverse_weight': inverse_weight,
                'required_point': 0.0,
            }
        )

    weighted_inverse_avg = (
        sum(row['credit_hours'] * row['inverse_weight'] for row in rows) / total_credit_hours
    )

    for row in rows:
        scaled_target = target_sgpa * (row['inverse_weight'] / weighted_inverse_avg)
        row['required_point'] = min(4.0, max(0.0, scaled_target))

    required_total_points = target_sgpa * total_credit_hours
    current_total_points = sum(row['required_point'] * row['credit_hours'] for row in rows)
    delta_points = required_total_points - current_total_points

    if abs(delta_points) > 1e-9:
        # If points must be added, bias easier courses first; if reduced, bias harder courses first.
        rows.sort(
            key=lambda row: row['difficulty_weight'],
            reverse=delta_points < 0,
        )

        for row in rows:
            if abs(delta_points) <= 1e-9:
                break

            if delta_points > 0:
                capacity = 4.0 - row['required_point']
                if capacity <= 0:
                    continue
                available_points = capacity * row['credit_hours']
                consume = min(delta_points, available_points)
                row['required_point'] += consume / row['credit_hours']
                delta_points -= consume
            else:
                capacity = row['required_point']
                if capacity <= 0:
                    continue
                available_points = capacity * row['credit_hours']
                consume = min(abs(delta_points), available_points)
                row['required_point'] -= consume / row['credit_hours']
                delta_points += consume

    return rows
