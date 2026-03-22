"""Student service for data access and business logic."""

from flask import session
from models import Student, Course
from services.academic_service import academic_period_rank, build_semester_number_lookup


def get_current_student():
    """Retrieve the currently logged-in student from the session."""
    student_id = session.get('student_id')
    if not student_id:
        return None
    return Student.query.filter_by(student_id=student_id).first()


def build_next_period(period):
    """Build the next period tuple from (academic_year, semester)."""
    year, semester = period
    if semester == 'First':
        return (year, 'Second')
    try:
        start = int(str(year).split('/')[0])
        return (f'{start + 1}/{start + 2}', 'First')
    except (ValueError, IndexError):
        return (year, 'First')


def build_semester_course_offering(department_id, excluded_codes=None, general_target=2, it_target=5, max_courses=7):
    """Build semester offering list using target mix and safe backfill."""
    excluded_codes = excluded_codes or set()

    base_q = Course.query.filter_by(department_id=department_id)
    if excluded_codes:
        base_q = base_q.filter(~Course.course_code.in_(excluded_codes))

    all_candidates = base_q.order_by(Course.course_code.asc()).all()
    educational = [course for course in all_candidates if course.course_type == 'General']
    it_related = [course for course in all_candidates if course.course_type != 'General']

    selected = educational[:general_target] + it_related[:it_target]

    if len(selected) < max_courses:
        selected_codes = {course.course_code for course in selected}
        for course in all_candidates:
            if course.course_code not in selected_codes:
                selected.append(course)
                selected_codes.add(course.course_code)
                if len(selected) >= max_courses:
                    break

    return selected[:max_courses]


def build_past_period_catalog(enrollments, current_period):
    """Group past enrollments by period with metadata for UI selection."""
    period_map = {}
    for enrollment in enrollments:
        period_key = (enrollment.academic_year, enrollment.semester)
        if period_key == current_period:
            continue

        if period_key not in period_map:
            period_map[period_key] = {
                'academic_year': enrollment.academic_year,
                'semester': enrollment.semester,
                'count': 0,
                'credits': 0,
                'enrollments': [],
            }

        period_map[period_key]['count'] += 1
        period_map[period_key]['credits'] += enrollment.course.credit_hours
        period_map[period_key]['enrollments'].append(enrollment)

    period_lookup = build_semester_number_lookup(
        [(enrollment.academic_year, enrollment.semester) for enrollment in enrollments]
    )

    rows = list(period_map.values())
    for row in rows:
        row['semester_number'] = period_lookup.get((row['academic_year'], row['semester']))
        row['enrollments'].sort(key=lambda enrollment: enrollment.course.course_code)

    rows.sort(
        key=lambda row: academic_period_rank(
            type('PeriodObj', (), {'academic_year': row['academic_year'], 'semester': row['semester']})
        ),
        reverse=True,
    )
    return rows
