"""Academic period and enrollment utilities for the USTED Students Portal."""


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


def compute_results_analytics(records, score_to_point_func):
    """Compute reusable analytics payload for results page and transcript PDF."""
    graded_records = [record for record in records if record.grade]
    published_count = sum(1 for record in graded_records if record.grade.approval_status == 'Published')
    pending_count = len(
        [
            record
            for record in records
            if (not record.grade) or (record.grade.approval_status != 'Published')
        ]
    )

    total_credits = sum(record.course.credit_hours for record in graded_records)
    total_grade_points = sum(
        score_to_point_func(float(record.grade.total_score)) * record.course.credit_hours
        for record in graded_records
    )
    cgpa = (total_grade_points / total_credits) if total_credits else 0.0

    by_period = {}
    for record in graded_records:
        key = (record.academic_year, record.semester)
        if key not in by_period:
            by_period[key] = {'credits': 0, 'points': 0.0, 'courses': 0}
        by_period[key]['credits'] += record.course.credit_hours
        by_period[key]['points'] += score_to_point_func(float(record.grade.total_score)) * record.course.credit_hours
        by_period[key]['courses'] += 1

    period_rows = []
    for (year, semester), stats in by_period.items():
        sgpa = (stats['points'] / stats['credits']) if stats['credits'] else 0.0
        period_rows.append(
            {
                'academic_year': year,
                'semester': semester,
                'courses': stats['courses'],
                'credits': stats['credits'],
                'points': round(stats['points'], 2),
                'sgpa': round(sgpa, 2),
            }
        )

    period_rows_desc = sorted(
        period_rows,
        key=lambda row: academic_period_rank(
            type(
                'PeriodObj',
                (),
                {
                    'academic_year': row['academic_year'],
                    'semester': row['semester'],
                },
            )
        ),
        reverse=True,
    )

    best_period = max(period_rows_desc, key=lambda row: row['sgpa']) if period_rows_desc else None
    latest_period = period_rows_desc[0] if period_rows_desc else None

    abbreviation_summary = {
        'ccr': total_credits,
        'cgv': round(total_grade_points, 2),
        'cgpa': round(cgpa, 2),
        'scr': latest_period['credits'] if latest_period else 0,
        'sgp': latest_period['points'] if latest_period else 0.0,
        'sgpa': latest_period['sgpa'] if latest_period else 0.0,
        'period_label': (
            f"{latest_period['academic_year']} {latest_period['semester']}"
            if latest_period
            else 'N/A'
        ),
    }

    analytics = {
        'total_records': len(records),
        'graded_records': len(graded_records),
        'pending_records': pending_count,
        'published_records': published_count,
        'cgpa': round(cgpa, 2),
        'best_period': best_period,
    }

    return {
        'graded_records': graded_records,
        'total_credits': total_credits,
        'total_grade_points': total_grade_points,
        'cgpa': cgpa,
        'period_rows_desc': period_rows_desc,
        'best_period': best_period,
        'latest_period': latest_period,
        'abbreviation_summary': abbreviation_summary,
        'analytics': analytics,
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
