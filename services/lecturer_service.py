"""Lecturer service for page-level aggregation logic."""

from sqlalchemy import func

from models import Course, CourseLecturer, Enrollment, Grade, Resource, db


def _valid_value(raw_value, valid_options, fallback='All'):
    """Return a validated filter value from user input."""
    value = (raw_value or fallback).strip()
    return value if value in valid_options else fallback


def _period_sort_key(academic_year, semester):
    """Sort periods chronologically using the academic year and semester."""
    try:
        start_year = int(str(academic_year).split('/')[0])
    except (TypeError, ValueError, IndexError):
        start_year = 0
    semester_rank = 2 if str(semester).strip().lower().startswith('second') else 1
    return (start_year, semester_rank)


def build_lecturer_course_worklist(staff_id, academic_year='All', class_group='All', semester='All'):
    """Build lecturer-scoped course rows with grading workload metrics."""
    base_allocations = (
        CourseLecturer.query
        .join(Course, Course.course_code == CourseLecturer.course_code)
        .filter(CourseLecturer.staff_id == staff_id)
        .order_by(CourseLecturer.academic_year.desc(), Course.course_code.asc())
        .all()
    )

    year_options = sorted({row.academic_year for row in base_allocations}, reverse=True)
    class_group_options = sorted({row.class_group for row in base_allocations})

    selected_year = _valid_value(academic_year, {'All', *year_options})
    selected_class_group = _valid_value(class_group, {'All', *class_group_options})
    selected_semester = _valid_value(semester, {'All', 'First', 'Second'})

    filtered_allocations = [
        row
        for row in base_allocations
        if (selected_year == 'All' or row.academic_year == selected_year)
        and (selected_class_group == 'All' or row.class_group == selected_class_group)
    ]

    filtered_course_codes = sorted({row.course_code for row in filtered_allocations})
    if not filtered_course_codes:
        return {
            'course_rows': [],
            'year_options': year_options,
            'class_group_options': class_group_options,
            'selected_year': selected_year,
            'selected_class_group': selected_class_group,
            'selected_semester': selected_semester,
            'totals': {
                'enrolled_count': 0,
                'draft_count': 0,
                'pending_hod_count': 0,
                'pending_board_count': 0,
                'published_count': 0,
            },
        }

    enrollment_counts_query = (
        Enrollment.query
        .with_entities(Enrollment.course_code, func.count(Enrollment.enrollment_id))
        .filter(Enrollment.course_code.in_(filtered_course_codes))
    )

    status_counts_query = (
        Enrollment.query
        .with_entities(Enrollment.course_code, Grade.approval_status, func.count(Grade.grade_id))
        .join(Grade, Grade.enrollment_id == Enrollment.enrollment_id)
        .filter(Enrollment.course_code.in_(filtered_course_codes))
    )

    if selected_year != 'All':
        enrollment_counts_query = enrollment_counts_query.filter(Enrollment.academic_year == selected_year)
        status_counts_query = status_counts_query.filter(Enrollment.academic_year == selected_year)

    if selected_semester != 'All':
        enrollment_counts_query = enrollment_counts_query.filter(Enrollment.semester == selected_semester)
        status_counts_query = status_counts_query.filter(Enrollment.semester == selected_semester)

    enrollment_count_map = {
        code: count
        for code, count in enrollment_counts_query.group_by(Enrollment.course_code).all()
    }

    status_count_map = {
        code: {
            'Draft': 0,
            'Pending_HOD': 0,
            'Pending_Board': 0,
            'Published': 0,
        }
        for code in filtered_course_codes
    }
    for code, status, count in status_counts_query.group_by(Enrollment.course_code, Grade.approval_status).all():
        status_count_map.setdefault(
            code,
            {
                'Draft': 0,
                'Pending_HOD': 0,
                'Pending_Board': 0,
                'Published': 0,
            },
        )
        status_count_map[code][status] = count

    roster_semester = selected_semester if selected_semester in {'First', 'Second'} else 'First'
    course_rows = []
    for allocation in filtered_allocations:
        status_metrics = status_count_map.get(
            allocation.course_code,
            {
                'Draft': 0,
                'Pending_HOD': 0,
                'Pending_Board': 0,
                'Published': 0,
            },
        )
        course_rows.append(
            {
                'allocation': allocation,
                'course': allocation.course,
                'enrolled_count': enrollment_count_map.get(allocation.course_code, 0),
                'draft_count': status_metrics['Draft'],
                'pending_hod_count': status_metrics['Pending_HOD'],
                'pending_board_count': status_metrics['Pending_Board'],
                'published_count': status_metrics['Published'],
                'roster_year': selected_year if selected_year != 'All' else allocation.academic_year,
                'roster_semester': roster_semester,
            }
        )

    totals = {
        'enrolled_count': sum(row['enrolled_count'] for row in course_rows),
        'draft_count': sum(row['draft_count'] for row in course_rows),
        'pending_hod_count': sum(row['pending_hod_count'] for row in course_rows),
        'pending_board_count': sum(row['pending_board_count'] for row in course_rows),
        'published_count': sum(row['published_count'] for row in course_rows),
    }

    return {
        'course_rows': course_rows,
        'year_options': year_options,
        'class_group_options': class_group_options,
        'selected_year': selected_year,
        'selected_class_group': selected_class_group,
        'selected_semester': selected_semester,
        'totals': totals,
    }


def build_lecturer_resource_hub(staff_id):
    """Build lecturer-scoped resource management cards."""
    allocations = (
        CourseLecturer.query
        .join(Course, Course.course_code == CourseLecturer.course_code)
        .filter(CourseLecturer.staff_id == staff_id)
        .order_by(CourseLecturer.academic_year.desc(), Course.course_code.asc())
        .all()
    )

    if not allocations:
        return {
            'resource_cards': [],
            'totals': {
                'course_count': 0,
                'resource_count': 0,
                'courses_with_resources': 0,
            },
        }

    resource_rows = (
        Resource.query
        .with_entities(
            Resource.course_code,
            func.count(Resource.resource_id),
            func.max(Resource.upload_date),
        )
        .filter(
            Resource.course_code.in_([allocation.course_code for allocation in allocations]),
            Resource.resource_type == 'Course',
        )
        .group_by(Resource.course_code)
        .all()
    )

    resource_map = {
        course_code: {
            'resource_count': count,
            'latest_upload': latest_upload,
        }
        for course_code, count, latest_upload in resource_rows
    }

    resource_cards = []
    for allocation in allocations:
        resource_metrics = resource_map.get(
            allocation.course_code,
            {
                'resource_count': 0,
                'latest_upload': None,
            },
        )
        resource_cards.append(
            {
                'allocation': allocation,
                'course': allocation.course,
                'resource_count': resource_metrics['resource_count'],
                'latest_upload': resource_metrics['latest_upload'],
            }
        )

    totals = {
        'course_count': len(resource_cards),
        'resource_count': sum(card['resource_count'] for card in resource_cards),
        'courses_with_resources': len([card for card in resource_cards if card['resource_count']]),
    }

    return {
        'resource_cards': resource_cards,
        'totals': totals,
    }


def _lecturer_scope_maps(staff_id):
    """Build quick-lookup maps for lecturer authorization scope."""
    allocations = CourseLecturer.query.filter_by(staff_id=staff_id).all()
    years_by_course = {}
    for allocation in allocations:
        years_by_course.setdefault(allocation.course_code, set()).add(allocation.academic_year)
    return allocations, years_by_course


def _grade_validation_errors(grade):
    """Validate grade row completeness and score integrity."""
    errors = []
    if not grade:
        return ['Missing grade row']

    ca_score = float(grade.ca_score) if grade.ca_score is not None else None
    exam_score = float(grade.exam_score) if grade.exam_score is not None else None
    total_score = float(grade.total_score) if grade.total_score is not None else None
    grade_letter = (grade.grade_letter or '').strip()

    if ca_score is None:
        errors.append('Missing CA score')
    elif not (0 <= ca_score <= 40):
        errors.append('CA out of range')

    if exam_score is None:
        errors.append('Missing exam component')
    elif not (0 <= exam_score <= 60):
        errors.append('Exam component out of range')

    if total_score is None:
        errors.append('Missing total score')
    elif not (0 <= total_score <= 100):
        errors.append('Total score out of range')

    if not grade_letter:
        errors.append('Missing grade letter')

    if ca_score is not None and exam_score is not None and total_score is not None:
        if abs((ca_score + exam_score) - total_score) > 0.11:
            errors.append('Total mismatch (CA + Exam)')

    return errors


def build_lecturer_draft_workspace(staff_id, academic_year='All', semester='All', course_code='All'):
    """Build cross-course Draft grade workspace for lecturer-owned scope."""
    allocations, years_by_course = _lecturer_scope_maps(staff_id)
    assigned_course_codes = sorted({allocation.course_code for allocation in allocations})
    year_options = sorted({allocation.academic_year for allocation in allocations}, reverse=True)

    selected_year = _valid_value(academic_year, {'All', *year_options})
    selected_semester = _valid_value(semester, {'All', 'First', 'Second'})
    selected_course_code = _valid_value(course_code, {'All', *assigned_course_codes})

    filtered_allocations = [
        allocation
        for allocation in allocations
        if (selected_year == 'All' or allocation.academic_year == selected_year)
        and (selected_course_code == 'All' or allocation.course_code == selected_course_code)
    ]

    if not assigned_course_codes:
        return {
            'draft_rows': [],
            'year_options': year_options,
            'course_options': assigned_course_codes,
            'selected_year': selected_year,
            'selected_semester': selected_semester,
            'selected_course_code': selected_course_code,
            'totals': {
                'draft_count': 0,
                'valid_count': 0,
                'invalid_count': 0,
            },
        }

    query = (
        Grade.query
        .join(Enrollment, Enrollment.enrollment_id == Grade.enrollment_id)
        .join(Course, Course.course_code == Enrollment.course_code)
        .filter(
            Grade.approval_status == 'Draft',
            Enrollment.course_code.in_(assigned_course_codes),
        )
        .order_by(Enrollment.academic_year.desc(), Enrollment.semester.desc(), Course.course_code.asc())
    )

    if selected_year != 'All':
        query = query.filter(Enrollment.academic_year == selected_year)
    if selected_semester != 'All':
        query = query.filter(Enrollment.semester == selected_semester)
    if selected_course_code != 'All':
        query = query.filter(Enrollment.course_code == selected_course_code)

    draft_rows = []
    for grade in query.all():
        enrollment = grade.enrollment
        if not enrollment:
            continue

        allowed_years = years_by_course.get(enrollment.course_code, set())
        if enrollment.academic_year not in allowed_years:
            continue

        errors = _grade_validation_errors(grade)
        draft_rows.append(
            {
                'grade': grade,
                'enrollment': enrollment,
                'student': enrollment.student,
                'course': enrollment.course,
                'is_valid': not errors,
                'validation_errors': errors,
            }
        )

    draft_counts_by_course = {}
    latest_period_by_course = {}
    for row in draft_rows:
        course_code_key = row['course'].course_code
        if course_code_key not in draft_counts_by_course:
            draft_counts_by_course[course_code_key] = {'draft_count': 0, 'valid_count': 0}
        draft_counts_by_course[course_code_key]['draft_count'] += 1
        if row['is_valid']:
            draft_counts_by_course[course_code_key]['valid_count'] += 1

        row_period = (row['enrollment'].academic_year, row['enrollment'].semester)
        current_latest = latest_period_by_course.get(course_code_key)
        if not current_latest or _period_sort_key(*row_period) > _period_sort_key(*current_latest):
            latest_period_by_course[course_code_key] = row_period

    course_cards = []
    for allocation in filtered_allocations:
        counts = draft_counts_by_course.get(allocation.course_code, {'draft_count': 0, 'valid_count': 0})
        latest_period = latest_period_by_course.get(allocation.course_code)
        if not latest_period:
            latest_period = (allocation.academic_year, 'First')
        course_cards.append(
            {
                'course_code': allocation.course_code,
                'course_name': allocation.course.course_name,
                'class_group': allocation.class_group,
                'academic_year': allocation.academic_year,
                'draft_count': counts['draft_count'],
                'valid_count': counts['valid_count'],
                'roster_year': latest_period[0],
                'roster_semester': latest_period[1],
            }
        )

    totals = {
        'draft_count': len(draft_rows),
        'valid_count': len([row for row in draft_rows if row['is_valid']]),
        'invalid_count': len([row for row in draft_rows if not row['is_valid']]),
    }

    return {
        'draft_rows': draft_rows,
        'course_cards': course_cards,
        'year_options': year_options,
        'course_options': assigned_course_codes,
        'selected_year': selected_year,
        'selected_semester': selected_semester,
        'selected_course_code': selected_course_code,
        'totals': totals,
    }


def submit_lecturer_drafts_to_hod(staff_id, enrollment_ids):
    """Submit valid lecturer-owned Draft grade rows to HOD queue."""
    if not enrollment_ids:
        return {
            'submitted': 0,
            'invalid': 0,
            'unauthorized': 0,
            'missing': 0,
        }

    _, years_by_course = _lecturer_scope_maps(staff_id)
    requested_ids = {int(row_id) for row_id in enrollment_ids}

    rows = (
        Enrollment.query
        .join(Grade, Grade.enrollment_id == Enrollment.enrollment_id)
        .filter(Enrollment.enrollment_id.in_(requested_ids))
        .all()
    )

    submitted = 0
    invalid = 0
    unauthorized = 0

    seen_ids = set()
    for enrollment in rows:
        seen_ids.add(enrollment.enrollment_id)
        grade = enrollment.grade

        allowed_years = years_by_course.get(enrollment.course_code, set())
        if enrollment.academic_year not in allowed_years:
            unauthorized += 1
            continue

        if not grade or grade.approval_status != 'Draft':
            invalid += 1
            continue

        if _grade_validation_errors(grade):
            invalid += 1
            continue

        grade.approval_status = 'Pending_HOD'
        submitted += 1

    missing = len(requested_ids - seen_ids)

    if submitted:
        db.session.commit()

    return {
        'submitted': submitted,
        'invalid': invalid,
        'unauthorized': unauthorized,
        'missing': missing,
    }