"""Academic period and enrollment utilities for the USTED Students Portal."""


def _to_float(value):
    """Safely convert SQLAlchemy numeric values to float."""
    if value is None:
        return None
    return float(value)


def _build_result_snapshot(record, score_to_point_func, score_to_letter_func, scaled_exam_func):
    """Build normalized grade snapshot for an enrollment using grading spec rules."""
    grade = getattr(record, 'grade', None)
    if not grade:
        return {
            'has_grade': False,
            'is_incomplete': True,
            'ca_score': None,
            'raw_exam_score': None,
            'scaled_exam_score': None,
            'total_score': None,
            'grade_letter': 'IC',
            'remark': 'Incomplete / Pending',
            'grade_point': 0.0,
            'sgp': 0.0,
            'credits_counted': 0,
        }

    ca_score = _to_float(grade.ca_score)
    raw_exam_score = _to_float(grade.exam_score)
    credit_hours = int(record.course.credit_hours or 0)

    # IC intercept: if CA or Exam is missing, do not count credits in SCR.
    if ca_score is None or raw_exam_score is None:
        return {
            'has_grade': True,
            'is_incomplete': True,
            'ca_score': ca_score,
            'raw_exam_score': raw_exam_score,
            'scaled_exam_score': None,
            'total_score': None,
            'grade_letter': 'IC',
            'remark': 'Incomplete / Pending',
            'grade_point': 0.0,
            'sgp': 0.0,
            'credits_counted': 0,
        }

    scaled_exam = scaled_exam_func(raw_exam_score)
    total_score = round(ca_score + scaled_exam, 2)
    grade_point = score_to_point_func(total_score)
    sgp = round(credit_hours * grade_point, 2)

    return {
        'has_grade': True,
        'is_incomplete': False,
        'ca_score': round(ca_score, 2),
        'raw_exam_score': round(raw_exam_score, 2),
        'scaled_exam_score': round(scaled_exam, 2),
        'total_score': total_score,
        'grade_letter': score_to_letter_func(total_score),
        'remark': 'Pass' if total_score >= 50 else 'Re-sit',
        'grade_point': grade_point,
        'sgp': sgp,
        'credits_counted': credit_hours,
    }


def semester_rank(semester):
    """Rank semester for sorting (First=1, Second=2)."""
    return 2 if semester == 'Second' else 1


def academic_period_rank(enrollment):
    """
    Create a sortable rank tuple for academic periods.
    
    Returns tuple of (start_year, semester_rank) for proper chronological sorting.
    """
    try:
        start_year = int(str(enrollment.academic_year).split('/')[0])
    except (ValueError, IndexError):
        start_year = 0
    return (start_year, semester_rank(enrollment.semester))


def compute_results_analytics(
    records,
    score_to_point_func,
    score_to_letter_func,
    scaled_exam_func,
    selected_period=None,
):
    """Compute analytics with spec-compliant grade recomputation and optional semester scope."""
    published_records = [
        record
        for record in records
        if record.grade and record.grade.approval_status == 'Published'
    ]

    result_snapshots = {}
    for record in records:
        snapshot = _build_result_snapshot(
            record,
            score_to_point_func,
            score_to_letter_func,
            scaled_exam_func,
        )
        result_snapshots[record.enrollment_id] = snapshot
        # Attach computed values for template/PDF rendering without mutating DB values.
        record.result_snapshot = snapshot

    def _in_selected_period(record):
        if not selected_period:
            return True
        return (record.academic_year, record.semester) == selected_period

    scoped_all_records = [record for record in records if _in_selected_period(record)]
    scoped_published_records = [record for record in published_records if _in_selected_period(record)]

    completed_published_records = [
        record
        for record in published_records
        if not result_snapshots[record.enrollment_id]['is_incomplete']
    ]

    total_credits = sum(result_snapshots[record.enrollment_id]['credits_counted'] for record in published_records)
    total_grade_points = sum(result_snapshots[record.enrollment_id]['sgp'] for record in published_records)
    cgpa = (total_grade_points / total_credits) if total_credits else 0.0

    by_period = {}
    for record in published_records:
        key = (record.academic_year, record.semester)
        snapshot = result_snapshots[record.enrollment_id]
        if key not in by_period:
            by_period[key] = {'credits': 0, 'points': 0.0, 'courses': 0, 'completed_courses': 0, 'incomplete_courses': 0}
        by_period[key]['credits'] += snapshot['credits_counted']
        by_period[key]['points'] += snapshot['sgp']
        by_period[key]['courses'] += 1
        if snapshot['is_incomplete']:
            by_period[key]['incomplete_courses'] += 1
        else:
            by_period[key]['completed_courses'] += 1

    period_rows = []
    for (year, semester), stats in by_period.items():
        sgpa = (stats['points'] / stats['credits']) if stats['credits'] else 0.0
        period_rows.append(
            {
                'academic_year': year,
                'semester': semester,
                'courses': stats['courses'],
                'completed_courses': stats['completed_courses'],
                'incomplete_courses': stats['incomplete_courses'],
                'credits': stats['credits'],
                'points': round(stats['points'], 2),
                'sgpa': round(sgpa, 2),
            }
        )

    period_rows_desc = sorted(
        period_rows,
        key=lambda row: academic_period_rank(
            type('PeriodObj', (), {'academic_year': row['academic_year'], 'semester': row['semester']})
        ),
        reverse=True,
    )

    best_period = max(period_rows_desc, key=lambda row: row['sgpa']) if period_rows_desc else None

    if selected_period:
        selected_period_row = next(
            (
                row
                for row in period_rows_desc
                if (row['academic_year'], row['semester']) == selected_period
            ),
            None,
        )
    else:
        selected_period_row = period_rows_desc[0] if period_rows_desc else None

    abbreviation_summary = {
        'ccr': total_credits,
        'cgv': round(total_grade_points, 2),
        'cgpa': round(cgpa, 2),
        'scr': selected_period_row['credits'] if selected_period_row else 0,
        'sgp': selected_period_row['points'] if selected_period_row else 0.0,
        'sgpa': selected_period_row['sgpa'] if selected_period_row else 0.0,
        'period_label': (
            f"{selected_period_row['academic_year']} {selected_period_row['semester']}"
            if selected_period_row
            else 'N/A'
        ),
    }

    analytics = {
        'total_records': len(scoped_all_records),
        'graded_records': len(
            [record for record in scoped_published_records if not result_snapshots[record.enrollment_id]['is_incomplete']]
        ),
        'pending_records': len(scoped_all_records) - len(
            [record for record in scoped_published_records if not result_snapshots[record.enrollment_id]['is_incomplete']]
        ),
        'published_records': len(scoped_published_records),
        'cgpa': round(cgpa, 2),
        'best_period': best_period,
    }

    return {
        'published_records': published_records,
        'scoped_all_records': scoped_all_records,
        'scoped_published_records': scoped_published_records,
        'total_credits': total_credits,
        'total_grade_points': round(total_grade_points, 2),
        'cgpa': round(cgpa, 2),
        'period_rows_desc': period_rows_desc,
        'best_period': best_period,
        'selected_period_row': selected_period_row,
        'abbreviation_summary': abbreviation_summary,
        'analytics': analytics,
        'result_snapshots': result_snapshots,
        'completed_published_records': completed_published_records,
    }


def build_semester_number_lookup(periods):
    """Map (academic_year, semester) to sequential semester numbers by chronology."""
    normalized = []
    for item in periods:
        if isinstance(item, tuple):
            year, semester = item
        else:
            year = getattr(item, 'academic_year', None)
            semester = getattr(item, 'semester', None)
        if year and semester:
            normalized.append((year, semester))

    ordered = sorted(
        set(normalized),
        key=lambda period: academic_period_rank(
            type('PeriodObj', (), {'academic_year': period[0], 'semester': period[1]})
        ),
    )
    return {period: idx + 1 for idx, period in enumerate(ordered)}


def group_records_by_period(records, semester_number_lookup):
    """Group enrollment records by period with semester number metadata."""
    grouped = {}
    for record in records:
        key = (record.academic_year, record.semester)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(record)

    rows = []
    for (year, semester), period_records in grouped.items():
        rows.append(
            {
                'academic_year': year,
                'semester': semester,
                'semester_number': semester_number_lookup.get((year, semester)),
                'records': period_records,
                'count': len(period_records),
            }
        )

    rows.sort(
        key=lambda row: academic_period_rank(
            type('PeriodObj', (), {'academic_year': row['academic_year'], 'semester': row['semester']})
        ),
        reverse=True,
    )
    return rows
