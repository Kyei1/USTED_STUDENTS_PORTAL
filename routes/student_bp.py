"""Student dashboard and protected routes blueprint for the USTED Students Portal."""

from functools import wraps
from io import BytesIO
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file, jsonify, current_app
from models import db, Student, Enrollment, Grade, FinancialStatus, SupportTicket, Course, Resource, Announcement, StudentAnnouncementRead
from services import (
    get_current_student,
    build_next_period,
    build_semester_course_offering,
    build_past_period_catalog,
    score_to_point,
    score_to_letter,
    classify_cgpa,
    point_to_min_total_score,
    scaled_exam_score,
    difficulty_label,
    allocate_uneven_target_points,
    academic_period_rank,
    compute_results_analytics,
    build_semester_number_lookup,
    group_records_by_period,
    get_default_logo_path,
    draw_logo_and_titles,
    draw_two_column_metadata,
)

student_bp = Blueprint(
    'student',
    __name__,
    url_prefix=None,  # Routes at root level
)


def login_required(view_func):
    """Decorator to require login for protected routes."""
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get('student_id'):
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('public.login'))
        return view_func(*args, **kwargs)
    return wrapped_view


@student_bp.route('/announcements/mark-read', methods=['POST'])
@login_required
def mark_announcements_read():
    """Mark current top student-facing announcements as read for badge updates."""
    student = get_current_student()
    if not student:
        return jsonify({'ok': False, 'error': 'student-not-found'}), 404

    announcements = (
        Announcement.query
        .filter(Announcement.target_audience.in_(['All', 'Students']))
        .order_by(Announcement.date_posted.desc())
        .limit(5)
        .all()
    )
    announcement_ids = [item.announcement_id for item in announcements]

    if not announcement_ids:
        return jsonify({'ok': True, 'unread_count': 0})

    existing_ids = {
        row.announcement_id
        for row in StudentAnnouncementRead.query.filter_by(student_id=student.student_id)
        .filter(StudentAnnouncementRead.announcement_id.in_(announcement_ids))
        .all()
    }

    for announcement_id in announcement_ids:
        if announcement_id not in existing_ids:
            db.session.add(
                StudentAnnouncementRead(
                    student_id=student.student_id,
                    announcement_id=announcement_id,
                )
            )

    db.session.commit()
    return jsonify({'ok': True, 'unread_count': 0})


@student_bp.route('/dashboard')
@login_required
def dashboard():
    """Student dashboard showing enrolled courses and financial status."""
    student = get_current_student()
    if not student:
        session.clear()
        flash('Student record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    enrollments = (
        Enrollment.query.filter_by(student_id=student.student_id)
        .order_by(Enrollment.academic_year.desc())
        .limit(6)
        .all()
    )

    all_enrollments = Enrollment.query.filter_by(student_id=student.student_id).all()
    latest_financial = (
        FinancialStatus.query.filter_by(student_id=student.student_id)
        .order_by(FinancialStatus.academic_year.desc())
        .first()
    )

    hour = datetime.now().hour
    if 5 <= hour < 12:
        greeting_phrase = 'Good Morning'
        greeting_emoji = '☀️'
    elif 12 <= hour < 17:
        greeting_phrase = 'Good Afternoon'
        greeting_emoji = '🌤️'
    elif 17 <= hour < 22:
        greeting_phrase = 'Good Evening'
        greeting_emoji = '🌙'
    else:
        greeting_phrase = 'Good Night'
        greeting_emoji = '✨'

    if all_enrollments:
        active_enrollment = max(all_enrollments, key=academic_period_rank)
        current_period = (active_enrollment.academic_year, active_enrollment.semester)
    else:
        start_year = datetime.now().year
        current_period = (f'{start_year}/{start_year + 1}', 'First')

    current_period_enrolled_codes = {
        row.course_code
        for row in Enrollment.query.filter_by(
            student_id=student.student_id,
            academic_year=current_period[0],
            semester=current_period[1],
        ).all()
    }

    if current_period_enrolled_codes:
        offered_current_courses = [
            row.course
            for row in Enrollment.query.filter_by(
                student_id=student.student_id,
                academic_year=current_period[0],
                semester=current_period[1],
            ).all()
            if row.course
        ]
    else:
        offered_current_courses = build_semester_course_offering(student.department_id)
    offered_current_codes = {course.course_code for course in offered_current_courses}

    if not offered_current_codes:
        registration_status = 'No active offering yet'
        registration_status_note = 'No current-semester course list is available yet.'
        registration_complete = False
    elif offered_current_codes.issubset(current_period_enrolled_codes):
        registration_status = 'Registration complete'
        registration_status_note = 'You are fully registered for the current semester.'
        registration_complete = True
    elif current_period_enrolled_codes:
        remaining = len(offered_current_codes - current_period_enrolled_codes)
        registration_status = 'Registration in progress'
        registration_status_note = f'{remaining} offered course(s) are still pending registration.'
        registration_complete = False
    else:
        registration_status = 'Not registered yet'
        registration_status_note = 'Start your course registration for the current semester.'
        registration_complete = False

    dashboard_registration = {
        'current_period': current_period,
        'offered_count': len(offered_current_codes),
        'enrolled_count': len(current_period_enrolled_codes),
        'status': registration_status,
        'note': registration_status_note,
        'is_complete': registration_complete,
    }

    dashboard_records = (
        Enrollment.query.filter_by(student_id=student.student_id)
        .join(Course, Enrollment.course_code == Course.course_code)
        .outerjoin(Grade, Grade.enrollment_id == Enrollment.enrollment_id)
        .order_by(Enrollment.academic_year.desc(), Enrollment.semester.desc(), Course.course_code.asc())
        .all()
    )
    dashboard_results_payload = compute_results_analytics(
        dashboard_records,
        score_to_point,
        score_to_letter,
        scaled_exam_score,
    )
    dashboard_cgpa = dashboard_results_payload['analytics']['cgpa']
    dashboard_ccr = dashboard_results_payload['abbreviation_summary']['ccr']
    dashboard_classification = classify_cgpa(dashboard_cgpa)

    dashboard_academic = {
        'cgpa': dashboard_cgpa,
        'ccr': dashboard_ccr,
        'classification': dashboard_classification,
    }

    return render_template(
        'student/dashboard.html',
        student=student,
        enrollments=enrollments,
        latest_financial=latest_financial,
        greeting_phrase=greeting_phrase,
        greeting_emoji=greeting_emoji,
        dashboard_registration=dashboard_registration,
        dashboard_academic=dashboard_academic,
    )


@student_bp.route('/profile')
@login_required
def profile():
    """Display the current student's profile details."""
    student = get_current_student()
    if not student:
        session.clear()
        flash('Student record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    return render_template('student/profile.html', student=student)


@student_bp.route('/account-settings', methods=['GET', 'POST'])
@login_required
def account_settings():
    """Allow a student to update profile identity and password."""
    student = get_current_student()
    if not student:
        session.clear()
        flash('Student record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    if request.method == 'POST':
        action = request.form.get('action', '').strip()

        if action == 'profile':
            first_name = request.form.get('first_name', '').strip()
            middle_name = request.form.get('middle_name', '').strip() or None
            last_name = request.form.get('last_name', '').strip()
            email_address = request.form.get('email_address', '').strip().lower()

            if not first_name or not last_name or not email_address:
                flash('First name, last name, and email are required.', 'danger')
                return redirect(url_for('student.account_settings'))

            email_owner = Student.query.filter(
                Student.email_address == email_address,
                Student.student_id != student.student_id,
            ).first()
            if email_owner:
                flash('That email address is already in use by another account.', 'danger')
                return redirect(url_for('student.account_settings'))

            student.first_name = first_name
            student.middle_name = middle_name
            student.last_name = last_name
            student.email_address = email_address
            db.session.commit()
            session['first_name'] = student.first_name
            flash('Profile details updated successfully.', 'success')
            return redirect(url_for('student.account_settings'))

        if action == 'password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not current_password or not new_password or not confirm_password:
                flash('All password fields are required.', 'danger')
                return redirect(url_for('student.account_settings'))
            if not check_password_hash(student.password_hash, current_password):
                flash('Current password is incorrect.', 'danger')
                return redirect(url_for('student.account_settings'))
            if len(new_password) < 8:
                flash('New password must be at least 8 characters long.', 'danger')
                return redirect(url_for('student.account_settings'))
            if new_password != confirm_password:
                flash('New password and confirmation do not match.', 'danger')
                return redirect(url_for('student.account_settings'))

            student.password_hash = generate_password_hash(new_password)
            db.session.commit()
            flash('Password updated successfully.', 'success')
            return redirect(url_for('student.account_settings'))

        flash('Unsupported account settings action.', 'warning')
        return redirect(url_for('student.account_settings'))

    return render_template('student/account_settings.html', student=student)


@student_bp.route('/my-courses', methods=['GET', 'POST'])
@login_required
def my_courses():
    """Course registration hub with current, past, and next-semester views."""
    student = get_current_student()
    if not student:
        session.clear()
        flash('Student record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    all_enrollments = (
        Enrollment.query.filter_by(student_id=student.student_id)
        .join(Course, Enrollment.course_code == Course.course_code)
        .outerjoin(Grade, Grade.enrollment_id == Enrollment.enrollment_id)
        .order_by(Enrollment.academic_year.desc(), Enrollment.semester.desc(), Course.course_code.asc())
        .all()
    )

    if all_enrollments:
        active_enrollment = max(all_enrollments, key=academic_period_rank)
        current_period = (active_enrollment.academic_year, active_enrollment.semester)
    else:
        start_year = datetime.now().year
        current_period = (f'{start_year}/{start_year + 1}', 'First')

    next_period = build_next_period(current_period)

    current_period_enrolled_codes = {
        row.course_code
        for row in Enrollment.query.filter_by(
            student_id=student.student_id,
            academic_year=current_period[0],
            semester=current_period[1],
        ).all()
    }

    if current_period_enrolled_codes:
        offered_current_courses = [
            row.course
            for row in Enrollment.query.filter_by(
                student_id=student.student_id,
                academic_year=current_period[0],
                semester=current_period[1],
            ).all()
            if row.course
        ]
    else:
        offered_current_courses = build_semester_course_offering(student.department_id)
    offered_current_codes = {course.course_code for course in offered_current_courses}

    past_periods = build_past_period_catalog(all_enrollments, current_period)
    selected_past_period_key = (request.args.get('past_period') or '').strip()

    if selected_past_period_key:
        selected_past_period = next(
            (
                period
                for period in past_periods
                if f"{period['academic_year']}|{period['semester']}" == selected_past_period_key
            ),
            None,
        )
    else:
        selected_past_period = past_periods[0] if past_periods else None

    if selected_past_period:
        selected_past_period_key = f"{selected_past_period['academic_year']}|{selected_past_period['semester']}"

    def _validate_selected_codes(codes, semester, year):
        if not codes:
            return 'Select at least one offered course before submitting registration.'
        if semester not in {'First', 'Second'}:
            return 'Invalid semester selected for registration.'
        if (year, semester) != current_period:
            return 'Registration is only allowed for the active semester period shown.'
        invalid_codes = [code for code in codes if code not in offered_current_codes]
        if invalid_codes:
            return 'One or more selected courses are not available for this semester.'
        if len(codes) > len(offered_current_codes):
            return 'You cannot register more courses than are offered this semester.'
        return None

    if request.method == 'POST':
        action = request.form.get('action', 'preview').strip().lower()
        selected_course_codes = sorted(set(request.form.getlist('course_codes')))
        if action == 'complete':
            selected_course_codes = sorted(set(request.form.getlist('selected_course_codes')))
        reg_year = request.form.get('academic_year', current_period[0]).strip()
        reg_semester = request.form.get('semester', current_period[1]).strip()

        validation_error = _validate_selected_codes(selected_course_codes, reg_semester, reg_year)
        if validation_error:
            flash(validation_error, 'danger')
            return redirect(url_for('student.my_courses'))

        existing_selected = {
            row.course_code
            for row in Enrollment.query.filter_by(
                student_id=student.student_id,
                academic_year=reg_year,
                semester=reg_semester,
            )
            .filter(Enrollment.course_code.in_(selected_course_codes))
            .all()
        }
        if existing_selected:
            flash(
                'Duplicate registration blocked. You are already registered for: '
                + ', '.join(sorted(existing_selected)),
                'warning',
            )
            return redirect(url_for('student.my_courses'))

        selected_courses = [
            course for course in offered_current_courses if course.course_code in set(selected_course_codes)
        ]

        if action != 'complete':
            preview_current_enrollments = [
                enrollment
                for enrollment in all_enrollments
                if (enrollment.academic_year, enrollment.semester) == current_period
            ]
            return render_template(
                'student/my_courses.html',
                student=student,
                current_period=current_period,
                next_period=next_period,
                current_enrollments=preview_current_enrollments,
                current_period_enrolled_codes=current_period_enrolled_codes,
                available_current_courses=offered_current_courses,
                available_next_courses=build_semester_course_offering(student.department_id),
                total_current_credits=sum(
                    enrollment.course.credit_hours
                    for enrollment in preview_current_enrollments
                ),
                pending_selected_courses=selected_courses,
                pending_selected_codes=selected_course_codes,
                pending_missing_count=max(0, len(offered_current_codes) - len(current_period_enrolled_codes) - len(selected_course_codes)),
                has_registration_download=False,
                past_periods=past_periods,
                selected_past_period=selected_past_period,
                selected_past_period_key=selected_past_period_key,
            )

        for course_code in selected_course_codes:
            db.session.add(
                Enrollment(
                    student_id=student.student_id,
                    course_code=course_code,
                    academic_year=reg_year,
                    semester=reg_semester,
                )
            )

        db.session.commit()

        session['registration_receipt'] = {
            'student_id': student.student_id,
            'academic_year': reg_year,
            'semester': reg_semester,
            'course_codes': selected_course_codes,
        }

        if len(selected_course_codes) < len(offered_current_codes):
            missing_count = len(offered_current_codes) - len(selected_course_codes)
            flash(
                f'Registered {len(selected_course_codes)} course(s). Warning: {missing_count} offered course(s) still not registered.',
                'warning',
            )
        else:
            flash(
                f'All offered courses registered successfully for {reg_year} {reg_semester} semester.',
                'success',
            )
        return redirect(url_for('student.my_courses'))

    current_enrollments = [
        enrollment
        for enrollment in all_enrollments
        if (enrollment.academic_year, enrollment.semester) == current_period
    ]
    next_course_codes = {
        enrollment.course_code
        for enrollment in all_enrollments
        if (enrollment.academic_year, enrollment.semester) == next_period
    }

    available_current_courses = offered_current_courses

    available_next_courses = build_semester_course_offering(
        student.department_id,
        next_course_codes,
    )

    total_current_credits = sum(enrollment.course.credit_hours for enrollment in current_enrollments)

    registration_receipt = session.get('registration_receipt') or {}
    has_registration_download = (
        registration_receipt.get('student_id') == student.student_id
        and bool(registration_receipt.get('course_codes'))
    )

    return render_template(
        'student/my_courses.html',
        student=student,
        current_period=current_period,
        next_period=next_period,
        current_enrollments=current_enrollments,
        current_period_enrolled_codes=current_period_enrolled_codes,
        available_current_courses=available_current_courses,
        available_next_courses=available_next_courses,
        total_current_credits=total_current_credits,
        pending_selected_courses=None,
        pending_selected_codes=[],
        pending_missing_count=max(0, len(offered_current_codes) - len(current_period_enrolled_codes)),
        has_registration_download=has_registration_download,
        past_periods=past_periods,
        selected_past_period=selected_past_period,
        selected_past_period_key=selected_past_period_key,
    )


def _build_registration_pdf(student, academic_year, semester, courses):
    """Build a registration slip PDF and return it as an in-memory buffer."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
    except ImportError:
        return None

    total_credits = sum(course.credit_hours for course in courses)
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    page_width, page_height = A4

    margin_left = 18 * mm
    logo_path = get_default_logo_path(current_app.root_path)

    pdf.setFillColor(colors.white)
    pdf.rect(0, 0, page_width, page_height, stroke=0, fill=1)

    draw_logo_and_titles(
        pdf,
        page_height,
        margin_left,
        colors,
        mm,
        logo_path,
        [
            ('Course Registration Slip', 'Helvetica-Bold', 11, 18),
        ],
    )

    generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    details_left = [
        ('Student', f'{student.first_name} {student.last_name}'),
        ('ID', student.student_id),
        ('Academic Year', academic_year or 'N/A'),
        ('Semester', semester or 'N/A'),
    ]
    details_right = [
        ('Generated', generated_at),
        ('No. of Courses', str(len(courses))),
        ('Total Credits', str(total_credits)),
    ]

    metadata_bottom = draw_two_column_metadata(
        pdf,
        page_height,
        margin_left,
        details_left,
        details_right,
        colors,
        mm,
    )

    line_y = metadata_bottom - (8 * mm)
    pdf.setFillColor(colors.HexColor('#7a0016'))
    pdf.setFont('Helvetica-Bold', 10)
    pdf.drawString(margin_left, line_y, 'Registered Courses')
    line_y -= (5 * mm)

    pdf.setFillColor(colors.HexColor('#e8e8e8'))
    pdf.rect(margin_left, line_y - (5 * mm), page_width - (2 * margin_left), 5 * mm, stroke=1, fill=1)
    pdf.setFillColor(colors.HexColor('#7a0016'))
    pdf.setFont('Helvetica-Bold', 9)
    pdf.drawString(margin_left + (2 * mm), line_y - (3.5 * mm), 'Course Code')
    pdf.drawString(margin_left + (32 * mm), line_y - (3.5 * mm), 'Course Title')
    pdf.drawRightString(page_width - margin_left - (2 * mm), line_y - (3.5 * mm), 'Credits')
    line_y -= (7 * mm)

    pdf.setFont('Helvetica', 9)
    for idx, course in enumerate(courses):
        if line_y < (24 * mm):
            pdf.showPage()
            pdf.setFillColor(colors.white)
            pdf.rect(0, 0, page_width, page_height, stroke=0, fill=1)
            line_y = page_height - (22 * mm)
            pdf.setFillColor(colors.HexColor('#7a0016'))
            pdf.setFont('Helvetica-Bold', 10)
            pdf.drawString(margin_left, line_y, 'Registered Courses (continued)')
            line_y -= (6 * mm)
            pdf.setFillColor(colors.black)
            pdf.setFont('Helvetica', 9)

        if idx % 2 == 0:
            pdf.setFillColor(colors.HexColor('#f9f9f9'))
            pdf.rect(margin_left, line_y - (5 * mm), page_width - (2 * margin_left), 5 * mm, stroke=0, fill=1)

        title = course.course_name or ''
        if len(title) > 50:
            title = title[:47] + '...'

        pdf.setFillColor(colors.black)
        pdf.drawString(margin_left + (2 * mm), line_y - (3.5 * mm), course.course_code)
        pdf.drawString(margin_left + (32 * mm), line_y - (3.5 * mm), title)
        pdf.drawRightString(page_width - margin_left - (2 * mm), line_y - (3.5 * mm), str(course.credit_hours))
        line_y -= (6 * mm)

    pdf.setFont('Helvetica-Oblique', 8)
    pdf.setFillColor(colors.HexColor('#999999'))
    pdf.drawString(margin_left, 10 * mm, 'This is an official course registration slip generated by USTED Students Portal.')
    pdf.drawString(margin_left, 7 * mm, 'Please retain this document for your records.')

    pdf.save()
    buffer.seek(0)
    return buffer


@student_bp.route('/my-courses/registration-download')
@login_required
def my_courses_registration_download():
    """Download the latest registration confirmation slip as PDF."""
    student = get_current_student()
    if not student:
        session.clear()
        flash('Student record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    receipt = session.get('registration_receipt') or {}
    if receipt.get('student_id') != student.student_id or not receipt.get('course_codes'):
        flash('No completed registration record is available for download yet.', 'warning')
        return redirect(url_for('student.my_courses'))

    course_codes = receipt.get('course_codes', [])
    courses = (
        Course.query.filter(Course.course_code.in_(course_codes))
        .order_by(Course.course_code.asc())
        .all()
    )

    buffer = _build_registration_pdf(
        student,
        receipt.get('academic_year', ''),
        receipt.get('semester', ''),
        courses,
    )
    if not buffer:
        flash('PDF export requires reportlab. Install dependencies and try again.', 'danger')
        return redirect(url_for('student.my_courses'))

    filename = f"registration_{student.student_id}_{receipt.get('academic_year', '').replace('/', '-')}_{receipt.get('semester', '')}.pdf"
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename,
    )


@student_bp.route('/my-courses/registration-download/<academic_year>/<semester>')
@login_required
def my_courses_registration_download_by_period(academic_year, semester):
    """Download a historical registration slip for a specific period as PDF."""
    student = get_current_student()
    if not student:
        session.clear()
        flash('Student record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    period_enrollments = (
        Enrollment.query.filter_by(
            student_id=student.student_id,
            academic_year=academic_year,
            semester=semester,
        )
        .join(Course, Enrollment.course_code == Course.course_code)
        .order_by(Course.course_code.asc())
        .all()
    )

    if not period_enrollments:
        flash('No registration record found for the selected period.', 'warning')
        return redirect(url_for('student.my_courses'))

    courses = [enrollment.course for enrollment in period_enrollments]
    buffer = _build_registration_pdf(student, academic_year, semester, courses)
    if not buffer:
        flash('PDF export requires reportlab. Install dependencies and try again.', 'danger')
        return redirect(url_for('student.my_courses'))

    filename = f"registration_{student.student_id}_{academic_year.replace('/', '-')}_{semester}.pdf"
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename,
    )


@student_bp.route('/results')
@login_required
def results():
    """Display student academic records and results."""
    student = get_current_student()
    if not student:
        session.clear()
        flash('Student record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    records = (
        Enrollment.query.filter_by(student_id=student.student_id)
        .join(Course, Enrollment.course_code == Course.course_code)
        .outerjoin(Grade, Grade.enrollment_id == Enrollment.enrollment_id)
        .order_by(Enrollment.academic_year.desc(), Enrollment.semester.desc(), Course.course_code.asc())
        .all()
    )

    semester_lookup = build_semester_number_lookup(
        [(record.academic_year, record.semester) for record in records]
    )

    published_records_all = [
        record
        for record in records
        if record.grade and record.grade.approval_status == 'Published'
    ]

    period_options = sorted(
        set((record.academic_year, record.semester) for record in published_records_all),
        key=lambda period: academic_period_rank(
            type('PeriodObj', (), {'academic_year': period[0], 'semester': period[1]})
        ),
        reverse=True,
    )

    selected_scope_raw = (request.args.get('result_scope') or 'all').strip()
    selected_scope = 'all' if selected_scope_raw.lower() in {'', 'all'} else selected_scope_raw
    selected_period = None
    if selected_scope != 'all' and '|' in selected_scope:
        year, sem = selected_scope.split('|', 1)
        selected_period = (year.strip(), sem.strip())

    results_payload = compute_results_analytics(
        records,
        score_to_point,
        score_to_letter,
        scaled_exam_score,
        selected_period=selected_period,
    )

    grouped_records = group_records_by_period(results_payload['scoped_published_records'], semester_lookup)

    for row in results_payload['period_rows_desc']:
        row['semester_number'] = semester_lookup.get((row['academic_year'], row['semester']))

    # Enrich grouped_records with semester metrics for template display.
    metrics_by_period = {
        (row['academic_year'], row['semester']): row
        for row in results_payload['period_rows_desc']
    }
    for group in grouped_records:
        key = (group['academic_year'], group['semester'])
        if key in metrics_by_period:
            metrics = metrics_by_period[key]
            group['metrics'] = {
                'scr': metrics['credits'],
                'sgp': metrics['points'],
                'sgpa': metrics['sgpa'],
                'completed_courses': metrics['completed_courses'],
                'incomplete_courses': metrics['incomplete_courses'],
            }
        else:
            group['metrics'] = {}

    # Prepare semester-vs-cumulative-CGPA trend data (chronological).
    trend_data = {
        'points': [
            {
                'x': 0,
                'y': 0.0,
                'label': 'Baseline (Before Semester 1)',
            }
        ],
    }
    running_credits = 0
    running_points = 0.0
    ordered_rows = sorted(
        results_payload['period_rows_desc'],
        key=lambda r: academic_period_rank(
            type('PeriodObj', (), {'academic_year': r['academic_year'], 'semester': r['semester']})
        ),
    )
    for semester_index, row in enumerate(ordered_rows, start=1):
        running_credits += row['credits']
        running_points += row['points']
        cgpa_to_date = round((running_points / running_credits), 2) if running_credits else 0.0
        trend_data['points'].append(
            {
                'x': semester_index,
                'y': cgpa_to_date,
                'label': f"Semester {semester_index} ({row['academic_year']} {row['semester']})",
            }
        )

    if selected_period and selected_period not in period_options:
        selected_scope = 'all'
        selected_period = None

    if selected_scope == 'all':
        download_url = url_for('student.results_transcript_pdf', result_scope='all')
    elif selected_period:
        download_url = url_for(
            'student.results_transcript_pdf',
            result_scope=f"{selected_period[0]}|{selected_period[1]}",
        )
    else:
        download_url = None

    return render_template(
        'student/results.html',
        student=student,
        grouped_records=grouped_records,
        result_snapshots=results_payload['result_snapshots'],
        analytics=results_payload['analytics'],
        abbreviation_summary=results_payload['abbreviation_summary'],
        period_rows=results_payload['period_rows_desc'],
        period_options=period_options,
        semester_lookup=semester_lookup,
        selected_scope=selected_scope,
        download_url=download_url,
        trend_data=trend_data,
        cgpa_classification=classify_cgpa(results_payload['analytics']['cgpa']),
    )


@student_bp.route('/results/transcript.pdf')
@login_required
def results_transcript_pdf():
    """Generate and download transcript PDF."""
    student = get_current_student()
    if not student:
        session.clear()
        flash('Student record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    records = (
        Enrollment.query.filter_by(student_id=student.student_id)
        .join(Course, Enrollment.course_code == Course.course_code)
        .outerjoin(Grade, Grade.enrollment_id == Enrollment.enrollment_id)
        .order_by(Enrollment.academic_year.desc(), Enrollment.semester.desc(), Course.course_code.asc())
        .all()
    )

    selected_scope_raw = (request.args.get('result_scope') or 'all').strip()
    selected_scope = 'all' if selected_scope_raw.lower() in {'', 'all'} else selected_scope_raw
    selected_period = None
    if selected_scope != 'all' and '|' in selected_scope:
        year, sem = selected_scope.split('|', 1)
        selected_period = (year.strip(), sem.strip())

    results_payload = compute_results_analytics(
        records,
        score_to_point,
        score_to_letter,
        scaled_exam_score,
        selected_period=selected_period,
    )
    records = results_payload['scoped_published_records']
    abbreviation_summary = results_payload['abbreviation_summary']
    result_snapshots = results_payload['result_snapshots']

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
    except ImportError:
        flash('PDF export requires reportlab. Install dependencies and try again.', 'danger')
        return redirect(url_for('student.results'))

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    page_width, page_height = A4

    margin_left = 18 * mm
    margin_right = 18 * mm
    line_y = page_height - (60 * mm)
    row_height = 7 * mm
    logo_path = get_default_logo_path(current_app.root_path)
    generated_at = datetime.now().strftime('Generated %Y-%m-%d %H:%M')

    def draw_header(y_pos, first_page=False):
        if first_page:
            draw_logo_and_titles(
                pdf,
                page_height,
                margin_left,
                colors,
                mm,
                logo_path,
                [
                    ('USTED Official Transcript', 'Helvetica-Bold', 11, 18),
                ],
            )

            details_left = [
                ('Student', f'{student.first_name} {student.last_name}'),
                ('ID', student.student_id),
                ('Period', abbreviation_summary['period_label']),
            ]
            details_right = [
                ('Generated', generated_at),
                ('CGPA', f"{abbreviation_summary['cgpa']:.2f}"),
                ('CCR', str(abbreviation_summary['ccr'])),
            ]

            draw_two_column_metadata(
                pdf,
                page_height,
                margin_left,
                details_left,
                details_right,
                colors,
                mm,
            )
        else:
            pdf.setFillColor(colors.HexColor('#7a0016'))
            pdf.setFont('Helvetica-Bold', 11)
            pdf.drawString(margin_left, page_height - (14 * mm), 'USTED Official Transcript')

        pdf.setFillColor(colors.HexColor('#4a000d'))
        pdf.setFont('Helvetica-Bold', 10)
        pdf.drawString(margin_left, y_pos, 'Academic Year')
        pdf.drawString(margin_left + (32 * mm), y_pos, 'Sem')
        pdf.drawString(margin_left + (46 * mm), y_pos, 'Course')
        pdf.drawString(margin_left + (68 * mm), y_pos, 'Title')
        pdf.drawString(margin_left + (128 * mm), y_pos, 'Cr')
        pdf.drawString(margin_left + (138 * mm), y_pos, 'Total')
        pdf.drawString(margin_left + (154 * mm), y_pos, 'Grade')
        pdf.line(margin_left, y_pos - 2, page_width - margin_right, y_pos - 2)

    draw_header(line_y, first_page=True)
    line_y -= row_height

    if not records:
        pdf.setFont('Helvetica', 10)
        pdf.setFillColor(colors.black)
        pdf.drawString(margin_left, line_y, 'No result records available yet.')
    else:
        pdf.setFont('Helvetica', 9)
        for enrollment in records:
            if line_y < (20 * mm):
                pdf.showPage()
                line_y = page_height - (24 * mm)
                draw_header(line_y, first_page=False)
                line_y -= row_height
                pdf.setFont('Helvetica', 9)

            title = enrollment.course.course_name or ''
            if len(title) > 34:
                title = title[:31] + '...'

            snapshot = result_snapshots.get(enrollment.enrollment_id, {})
            total_score = snapshot.get('total_score')
            total = f"{float(total_score):.2f}" if total_score is not None else 'N/A'
            grade_letter = snapshot.get('grade_letter', 'N/A')

            pdf.setFillColor(colors.black)
            pdf.drawString(margin_left, line_y, enrollment.academic_year)
            pdf.drawString(margin_left + (32 * mm), line_y, enrollment.semester[:3])
            pdf.drawString(margin_left + (46 * mm), line_y, enrollment.course.course_code)
            pdf.drawString(margin_left + (68 * mm), line_y, title)
            pdf.drawRightString(margin_left + (134 * mm), line_y, str(enrollment.course.credit_hours))
            pdf.drawRightString(margin_left + (151 * mm), line_y, total)
            pdf.drawRightString(margin_left + (170 * mm), line_y, grade_letter)
            line_y -= row_height

    if line_y < (52 * mm):
        pdf.showPage()
        line_y = page_height - (30 * mm)

    pdf.setFillColor(colors.HexColor('#4a000d'))
    pdf.setFont('Helvetica-Bold', 10)
    pdf.drawString(margin_left, line_y, f"Abbreviations Summary ({abbreviation_summary['period_label']})")
    line_y -= (6 * mm)
    pdf.line(margin_left, line_y + 2, page_width - margin_right, line_y + 2)

    pdf.setFillColor(colors.black)
    pdf.setFont('Helvetica', 9)
    pdf.drawString(margin_left, line_y - (2 * mm), f"SCR: {abbreviation_summary['scr']}")
    pdf.drawString(margin_left, line_y - (7 * mm), f"SGP: {abbreviation_summary['sgp']:.2f}")
    pdf.drawString(margin_left, line_y - (12 * mm), f"SGPA: {abbreviation_summary['sgpa']:.2f}")

    right_col_x = margin_left + (78 * mm)
    pdf.drawString(right_col_x, line_y - (2 * mm), f"CCR: {abbreviation_summary['ccr']}")
    pdf.drawString(right_col_x, line_y - (7 * mm), f"CGV: {abbreviation_summary['cgv']:.2f}")
    pdf.drawString(right_col_x, line_y - (12 * mm), f"CGPA: {abbreviation_summary['cgpa']:.2f}")

    pdf.setFont('Helvetica-Oblique', 8)
    pdf.setFillColor(colors.HexColor('#4a000d'))
    pdf.drawString(margin_left, 12 * mm, 'Generated by USTED Students Portal')

    pdf.save()
    buffer.seek(0)

    if selected_period:
        filename = f"USTED_Results_Semester_{selected_period[0].replace('/', '-')}_{selected_period[1]}_{student.student_id}.pdf"
    else:
        filename = f"USTED_Results_All_{student.student_id}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')


@student_bp.route('/resource-hub')
@login_required
def resource_hub():
    """Show curated global resources and lecturer-provided course resources."""
    student = get_current_student()
    if not student:
        session.clear()
        flash('Student record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    department_name = (student.department.department_name if student.department else '').strip().lower()

    it_categories = {
        'Cybersecurity': [
            {
                'name': 'TryHackMe Learning Paths',
                'url': 'https://tryhackme.com/',
                'note': 'Hands-on security labs from beginner to advanced.',
            },
            {
                'name': 'OWASP Top 10',
                'url': 'https://owasp.org/www-project-top-ten/',
                'note': 'Most critical web application security risks.',
            },
            {
                'name': 'Hack The Box Academy',
                'url': 'https://academy.hackthebox.com/',
                'note': 'Practical red-team and blue-team modules.',
            },
            {
                'name': 'PortSwigger Web Security Academy',
                'url': 'https://portswigger.net/web-security',
                'note': 'Free labs for web penetration testing techniques.',
            },
        ],
        'Cloud Engineering': [
            {
                'name': 'AWS Skill Builder',
                'url': 'https://explore.skillbuilder.aws/',
                'note': 'Cloud fundamentals, architecture, and hands-on labs.',
            },
            {
                'name': 'Microsoft Learn - Azure',
                'url': 'https://learn.microsoft.com/training/azure/',
                'note': 'Role-based Azure learning and certification prep.',
            },
            {
                'name': 'Google Cloud Skills Boost',
                'url': 'https://www.cloudskillsboost.google/',
                'note': 'Guided labs for GCP services and operations.',
            },
            {
                'name': 'Kubernetes Basics',
                'url': 'https://kubernetes.io/docs/tutorials/kubernetes-basics/',
                'note': 'Container orchestration essentials for cloud workloads.',
            },
        ],
        'DevOps and SRE': [
            {
                'name': 'Docker Docs',
                'url': 'https://docs.docker.com/get-started/',
                'note': 'Containerization workflow and best practices.',
            },
            {
                'name': 'GitHub Actions Docs',
                'url': 'https://docs.github.com/actions',
                'note': 'Build CI/CD pipelines directly in GitHub.',
            },
            {
                'name': 'Atlassian DevOps Tutorials',
                'url': 'https://www.atlassian.com/devops',
                'note': 'Modern DevOps lifecycle and delivery practices.',
            },
            {
                'name': 'Prometheus Monitoring Guides',
                'url': 'https://prometheus.io/docs/introduction/overview/',
                'note': 'Metrics, alerting, and observability foundations.',
            },
        ],
        'Data Science and Analytics': [
            {
                'name': 'Kaggle Learn',
                'url': 'https://www.kaggle.com/learn',
                'note': 'Practical notebooks for analytics and modeling.',
            },
            {
                'name': 'IBM Data Science Learning Path',
                'url': 'https://www.ibm.com/training/data-science',
                'note': 'Statistics, Python, and data workflow coverage.',
            },
            {
                'name': 'Google Data Analytics Certificate',
                'url': 'https://www.coursera.org/professional-certificates/google-data-analytics',
                'note': 'Spreadsheet, SQL, and BI analytics practice.',
            },
            {
                'name': 'DataCamp Free Courses',
                'url': 'https://www.datacamp.com/courses',
                'note': 'Interactive data analysis lessons and exercises.',
            },
        ],
        'Artificial Intelligence and ML': [
            {
                'name': 'Google ML Crash Course',
                'url': 'https://developers.google.com/machine-learning/crash-course',
                'note': 'Fast practical introduction to machine learning.',
            },
            {
                'name': 'DeepLearning.AI Short Courses',
                'url': 'https://www.deeplearning.ai/short-courses/',
                'note': 'Applied AI topics including LLM engineering.',
            },
            {
                'name': 'fast.ai Practical Deep Learning',
                'url': 'https://course.fast.ai/',
                'note': 'Hands-on deep learning with production focus.',
            },
            {
                'name': 'Hugging Face Course',
                'url': 'https://huggingface.co/learn',
                'note': 'NLP, transformers, and open-source AI workflows.',
            },
        ],
        'Backend Engineering': [
            {
                'name': 'FastAPI Tutorial',
                'url': 'https://fastapi.tiangolo.com/tutorial/',
                'note': 'Modern Python API development with type hints.',
            },
            {
                'name': 'Django Official Tutorial',
                'url': 'https://docs.djangoproject.com/en/stable/intro/tutorial01/',
                'note': 'Full-stack web development with robust backend support.',
            },
            {
                'name': 'Node.js Learn',
                'url': 'https://nodejs.org/en/learn',
                'note': 'Server-side JavaScript and runtime fundamentals.',
            },
            {
                'name': 'REST API Design Guide',
                'url': 'https://learn.microsoft.com/azure/architecture/best-practices/api-design',
                'note': 'Best practices for scalable API architecture.',
            },
        ],
        'Frontend Engineering': [
            {
                'name': 'MDN Frontend Learning Path',
                'url': 'https://developer.mozilla.org/en-US/docs/Learn/Front-end_web_developer',
                'note': 'Structured HTML, CSS, and JavaScript roadmap.',
            },
            {
                'name': 'React Documentation',
                'url': 'https://react.dev/learn',
                'note': 'Component patterns and modern React architecture.',
            },
            {
                'name': 'Vue.js Guide',
                'url': 'https://vuejs.org/guide/introduction.html',
                'note': 'Progressive framework tutorials and patterns.',
            },
            {
                'name': 'Frontend Mentor',
                'url': 'https://www.frontendmentor.io/challenges',
                'note': 'Real-world UI challenges for portfolio building.',
            },
        ],
        'Mobile App Development': [
            {
                'name': 'Android Developers Training',
                'url': 'https://developer.android.com/courses',
                'note': 'Kotlin-based Android app development pathways.',
            },
            {
                'name': 'Apple SwiftUI Tutorials',
                'url': 'https://developer.apple.com/tutorials/swiftui',
                'note': 'Build iOS apps with modern SwiftUI practices.',
            },
            {
                'name': 'Flutter Codelabs',
                'url': 'https://docs.flutter.dev/get-started/codelab',
                'note': 'Cross-platform app development from a single codebase.',
            },
            {
                'name': 'React Native Documentation',
                'url': 'https://reactnative.dev/docs/environment-setup',
                'note': 'JavaScript-native mobile apps for Android and iOS.',
            },
        ],
        'UI/UX Product Design': [
            {
                'name': 'Figma Learn',
                'url': 'https://help.figma.com/hc/en-us/categories/360002051613-Learn-design',
                'note': 'Interface design, prototyping, and collaboration workflows.',
            },
            {
                'name': 'Nielsen Norman Group Articles',
                'url': 'https://www.nngroup.com/articles/',
                'note': 'Industry-standard UX research and usability guidance.',
            },
            {
                'name': 'Material Design',
                'url': 'https://m3.material.io/',
                'note': 'Comprehensive design system for digital products.',
            },
            {
                'name': 'Laws of UX',
                'url': 'https://lawsofux.com/',
                'note': 'Practical UX principles for interface decisions.',
            },
        ],
        'Networking and Systems': [
            {
                'name': 'Cisco Skills for All - Networking',
                'url': 'https://skillsforall.com/catalog?category=networking',
                'note': 'Network fundamentals and routing/switching skills.',
            },
            {
                'name': 'CompTIA Network+ Objectives',
                'url': 'https://www.comptia.org/certifications/network',
                'note': 'Structured roadmap for networking competencies.',
            },
            {
                'name': 'Linux Journey',
                'url': 'https://linuxjourney.com/',
                'note': 'Linux systems administration learning path.',
            },
            {
                'name': 'Red Hat Enable Sysadmin',
                'url': 'https://www.redhat.com/sysadmin',
                'note': 'Practical system engineering and operations articles.',
            },
        ],
        'Data Engineering': [
            {
                'name': 'Data Engineering Zoomcamp',
                'url': 'https://github.com/DataTalksClub/data-engineering-zoomcamp',
                'note': 'Hands-on modern data engineering curriculum and projects.',
            },
            {
                'name': 'Apache Airflow Documentation',
                'url': 'https://airflow.apache.org/docs/',
                'note': 'Workflow orchestration for data pipelines at scale.',
            },
            {
                'name': 'dbt Learn',
                'url': 'https://docs.getdbt.com/docs/introduction',
                'note': 'Transform analytics workflows using modular SQL models.',
            },
            {
                'name': 'Kafka Quickstart',
                'url': 'https://kafka.apache.org/quickstart',
                'note': 'Streaming data pipelines and event-driven architecture basics.',
            },
        ],
        'QA and Test Automation': [
            {
                'name': 'Selenium Documentation',
                'url': 'https://www.selenium.dev/documentation/',
                'note': 'Browser automation for UI testing workflows.',
            },
            {
                'name': 'Playwright Docs',
                'url': 'https://playwright.dev/docs/intro',
                'note': 'Fast and reliable end-to-end testing across browsers.',
            },
            {
                'name': 'Postman API Testing Learning Center',
                'url': 'https://learning.postman.com/',
                'note': 'API testing, automation, and collaboration practices.',
            },
            {
                'name': 'Ministry of Testing',
                'url': 'https://www.ministryoftesting.com/',
                'note': 'Community-driven QA skills, guides, and career content.',
            },
        ],
        'Blockchain and Web3': [
            {
                'name': 'Ethereum Developer Docs',
                'url': 'https://ethereum.org/developers/docs/',
                'note': 'Smart contracts, wallets, and dApp architecture fundamentals.',
            },
            {
                'name': 'Solidity Documentation',
                'url': 'https://docs.soliditylang.org/',
                'note': 'Core language reference for EVM smart contracts.',
            },
            {
                'name': 'Chainlink Learn',
                'url': 'https://chain.link/education',
                'note': 'Oracle networks and hybrid smart contract design.',
            },
            {
                'name': 'Alchemy Web3 University',
                'url': 'https://www.alchemy.com/university',
                'note': 'Structured web3 development tutorials and projects.',
            },
        ],
        'Game Development': [
            {
                'name': 'Unity Learn',
                'url': 'https://learn.unity.com/',
                'note': '2D/3D game creation with production-ready workflows.',
            },
            {
                'name': 'Unreal Engine Tutorials',
                'url': 'https://dev.epicgames.com/community/unreal-engine/learning',
                'note': 'Blueprints, rendering, and C++ game systems.',
            },
            {
                'name': 'Godot Docs',
                'url': 'https://docs.godotengine.org/en/stable/getting_started/introduction/index.html',
                'note': 'Open-source game engine for rapid prototyping.',
            },
            {
                'name': 'Game Programming Patterns',
                'url': 'https://gameprogrammingpatterns.com/',
                'note': 'Engineering patterns commonly used in game systems.',
            },
        ],
        'IT Project Management': [
            {
                'name': 'PMI Project Management Basics',
                'url': 'https://www.pmi.org/learning/library',
                'note': 'Project planning, execution, and stakeholder communication.',
            },
            {
                'name': 'Atlassian Agile Coach',
                'url': 'https://www.atlassian.com/agile',
                'note': 'Agile delivery methods and team workflow playbooks.',
            },
            {
                'name': 'Scrum Guides',
                'url': 'https://scrumguides.org/',
                'note': 'Official Scrum framework for iterative delivery.',
            },
            {
                'name': 'Google Project Management Certificate',
                'url': 'https://www.coursera.org/professional-certificates/google-project-management',
                'note': 'Foundations of project operations and leadership skills.',
            },
        ],
        'AR/VR and Spatial Computing': [
            {
                'name': 'Unity XR Interaction Toolkit',
                'url': 'https://docs.unity3d.com/Packages/com.unity.xr.interaction.toolkit@latest',
                'note': 'Build immersive XR interactions in Unity.',
            },
            {
                'name': 'WebXR Device API',
                'url': 'https://developer.mozilla.org/en-US/docs/Web/API/WebXR_Device_API',
                'note': 'Browser-native augmented and virtual reality experiences.',
            },
            {
                'name': 'Meta Quest Developer Docs',
                'url': 'https://developer.oculus.com/documentation/',
                'note': 'VR development guidance for Quest devices.',
            },
            {
                'name': 'Apple visionOS Pathway',
                'url': 'https://developer.apple.com/visionos/',
                'note': 'Spatial computing app development for Apple Vision Pro.',
            },
        ],
    }

    education_categories = {
        'Teaching Practice': [
            {
                'name': 'TES Connect',
                'url': 'https://www.tes.com/teaching-resources',
                'note': 'Ready-to-use lesson plans and classroom activities.',
            },
            {
                'name': 'TeachThought',
                'url': 'https://www.teachthought.com/',
                'note': 'Modern classroom strategy and pedagogy resources.',
            },
        ],
        'Educational Technology': [
            {
                'name': 'edX Education Courses',
                'url': 'https://www.edx.org/learn/education',
                'note': 'Instructional design and learning science content.',
            },
            {
                'name': 'Coursera Teaching and Learning',
                'url': 'https://www.coursera.org/browse/social-sciences/education',
                'note': 'Professional certificates and specialization tracks.',
            },
        ],
    }

    category_icons = {
        'Cybersecurity': 'bi-shield-lock-fill',
        'Cloud Engineering': 'bi-cloud-fill',
        'DevOps and SRE': 'bi-gear-wide-connected',
        'Data Science and Analytics': 'bi-bar-chart-fill',
        'Artificial Intelligence and ML': 'bi-cpu-fill',
        'Backend Engineering': 'bi-hdd-network-fill',
        'Frontend Engineering': 'bi-window-stack',
        'Mobile App Development': 'bi-phone-fill',
        'UI/UX Product Design': 'bi-palette-fill',
        'Networking and Systems': 'bi-diagram-3-fill',
        'Data Engineering': 'bi-diagram-2-fill',
        'QA and Test Automation': 'bi-bug-fill',
        'Blockchain and Web3': 'bi-currency-bitcoin',
        'Game Development': 'bi-controller',
        'IT Project Management': 'bi-kanban-fill',
        'AR/VR and Spatial Computing': 'bi-badge-vr-fill',
        'Teaching Practice': 'bi-easel2-fill',
        'Educational Technology': 'bi-mortarboard-fill',
    }

    is_it_department = any(keyword in department_name for keyword in ['information technology', 'computer', 'ict', 'software'])
    is_education_department = any(keyword in department_name for keyword in ['education', 'teacher', 'pedagogy'])

    curated_categories = it_categories
    if is_it_department:
        curated_categories = it_categories
    elif is_education_department:
        curated_categories = education_categories

    common_it_boosters = [
        {
            'name': 'roadmap.sh Career Roadmaps',
            'url': 'https://roadmap.sh/',
            'note': 'Visual guides for role-based skills and progression.',
        },
        {
            'name': 'GitHub Skills',
            'url': 'https://skills.github.com/',
            'note': 'Hands-on labs for Git, collaboration, and developer workflows.',
        },
        {
            'name': 'Stack Overflow',
            'url': 'https://stackoverflow.com/',
            'note': 'Community Q&A for debugging and practical implementation issues.',
        },
        {
            'name': 'MIT OpenCourseWare - Electrical Engineering and Computer Science',
            'url': 'https://ocw.mit.edu/courses/electrical-engineering-and-computer-science/',
            'note': 'University-grade foundations across core computing topics.',
        },
        {
            'name': 'Coursera IT Catalog',
            'url': 'https://www.coursera.org/browse/information-technology',
            'note': 'Professional certificate pathways across top IT domains.',
        },
        {
            'name': 'edX Computer Science Programs',
            'url': 'https://www.edx.org/learn/computer-science',
            'note': 'Academic and industry-aligned CS and IT coursework.',
        },
        {
            'name': 'freeCodeCamp',
            'url': 'https://www.freecodecamp.org/',
            'note': 'Project-based practice for web, APIs, and scripting skills.',
        },
        {
            'name': 'GeeksforGeeks',
            'url': 'https://www.geeksforgeeks.org/',
            'note': 'Reference articles for algorithms, systems, and interview prep.',
        },
    ]

    def ensure_minimum_resources(categories, minimum=10):
        """Ensure each category has at least `minimum` direct links."""
        normalized = {}
        for category, links in categories.items():
            prepared_links = list(links)
            seen_urls = {item.get('url') for item in prepared_links}

            for booster in common_it_boosters:
                if len(prepared_links) >= minimum:
                    break
                if booster['url'] in seen_urls:
                    continue
                prepared_links.append(
                    {
                        'name': booster['name'],
                        'url': booster['url'],
                        'note': f"{booster['note']} Also useful for {category}.",
                    }
                )
                seen_urls.add(booster['url'])

            normalized[category] = prepared_links[:minimum]
        return normalized

    if is_it_department or not is_education_department:
        curated_categories = ensure_minimum_resources(curated_categories, minimum=10)

    try:
        course_resources = (
            Resource.query.outerjoin(Course, Resource.course_code == Course.course_code)
            .filter(
                Resource.department_id == student.department_id,
                Resource.resource_type == 'Course',
            )
            .order_by(Resource.upload_date.desc(), Course.course_code.asc())
            .all()
        )
    except Exception as exc:  # pragma: no cover - defensive fallback for inconsistent legacy rows
        current_app.logger.exception('Failed loading course resources for %s: %s', student.student_id, exc)
        flash('Some resources could not be loaded due to legacy data. Showing available items only.', 'warning')
        course_resources = []

    lecturer_course_count = len({res.course_code for res in course_resources if res.course_code})

    return render_template(
        'student/resource_hub.html',
        student=student,
        curated_categories=curated_categories,
        category_icons=category_icons,
        course_resources=course_resources,
        lecturer_course_count=lecturer_course_count,
    )


@student_bp.route('/gpa-simulator', methods=['GET', 'POST'])
@login_required
def gpa_simulator():
    """GPA simulator with single-course and target SGPA modes."""
    student = get_current_student()
    if not student:
        session.clear()
        flash('Student record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    enrollments = (
        Enrollment.query.filter_by(student_id=student.student_id)
        .join(Course, Enrollment.course_code == Course.course_code)
        .order_by(Enrollment.academic_year.desc(), Course.course_code.asc())
        .all()
    )

    if not enrollments:
        return render_template(
            'student/gpa_simulator.html',
            student=student,
            active_enrollments=[],
            active_period=None,
            past_cgpa=0.0,
            total_past_credits=0,
            mode='single',
            single_result=None,
            target_result=None,
        )

    active_enrollment = max(enrollments, key=academic_period_rank)
    active_period = (active_enrollment.academic_year, active_enrollment.semester)
    active_enrollments = [
        enrollment
        for enrollment in enrollments
        if (enrollment.academic_year, enrollment.semester) == active_period
    ]

    graded_enrollments = [enrollment for enrollment in enrollments if enrollment.grade]
    past_graded_enrollments = [
        enrollment
        for enrollment in graded_enrollments
        if (enrollment.academic_year, enrollment.semester) != active_period
    ]

    if student.level == '100' and active_period[1] == 'First':
        total_past_credits = 0
        total_past_grade_points = 0.0
        past_cgpa = 0.0
    else:
        total_past_credits = sum(enrollment.course.credit_hours for enrollment in past_graded_enrollments)
        total_past_grade_points = sum(
            score_to_point(float(enrollment.grade.total_score)) * enrollment.course.credit_hours
            for enrollment in past_graded_enrollments
        )
        past_cgpa = (total_past_grade_points / total_past_credits) if total_past_credits else 0.0

    if request.method == 'POST':
        mode = (request.form.get('mode') or 'single').strip().lower()
    else:
        mode = (request.args.get('mode') or 'single').strip().lower()
    if mode not in {'single', 'target'}:
        mode = 'single'
    single_result = None
    target_result = None

    baseline_grade_point = past_cgpa
    active_credit_hours = sum(enrollment.course.credit_hours for enrollment in active_enrollments)

    if request.method == 'POST' and mode == 'single':
        selected_enrollment_id = request.form.get('single_enrollment_id', '').strip()
        ca_raw = request.form.get('ca_score', '').strip()
        exam_raw = request.form.get('raw_exam_score', '').strip()

        selected_enrollment = next(
            (enrollment for enrollment in active_enrollments if str(enrollment.enrollment_id) == selected_enrollment_id),
            None,
        )

        if not selected_enrollment:
            flash('Please select a valid course for single-course projection.', 'danger')
        else:
            try:
                ca_score = float(ca_raw)
                raw_exam_score = float(exam_raw)
            except ValueError:
                flash('CA and Raw Exam must be numeric values.', 'danger')
            else:
                if not (0 <= ca_score <= 40):
                    flash('CA Score must be between 0 and 40.', 'danger')
                elif not (0 <= raw_exam_score <= 100):
                    flash('Raw Exam Score must be between 0 and 100.', 'danger')
                else:
                    scaled_exam = scaled_exam_score(raw_exam_score)
                    projected_total = ca_score + scaled_exam
                    projected_point = score_to_point(projected_total)
                    projected_letter = score_to_letter(projected_total)

                    baseline_semester_grade_points = 0.0
                    projected_semester_grade_points = 0.0

                    for enrollment in active_enrollments:
                        if enrollment.grade:
                            base_point = score_to_point(float(enrollment.grade.total_score))
                        else:
                            base_point = baseline_grade_point

                        if enrollment.enrollment_id == selected_enrollment.enrollment_id:
                            sim_point = projected_point
                        else:
                            sim_point = base_point

                        credit_hours = enrollment.course.credit_hours
                        baseline_semester_grade_points += base_point * credit_hours
                        projected_semester_grade_points += sim_point * credit_hours

                    baseline_sgpa = (
                        baseline_semester_grade_points / active_credit_hours if active_credit_hours else 0.0
                    )
                    projected_sgpa = (
                        projected_semester_grade_points / active_credit_hours if active_credit_hours else 0.0
                    )

                    baseline_cgpa = (
                        (total_past_grade_points + baseline_semester_grade_points)
                        / (total_past_credits + active_credit_hours)
                        if (total_past_credits + active_credit_hours)
                        else 0.0
                    )
                    projected_cgpa = (
                        (total_past_grade_points + projected_semester_grade_points)
                        / (total_past_credits + active_credit_hours)
                        if (total_past_credits + active_credit_hours)
                        else 0.0
                    )

                    single_result = {
                        'selected_enrollment_id': str(selected_enrollment.enrollment_id),
                        'course_code': selected_enrollment.course.course_code,
                        'ca_score': ca_score,
                        'raw_exam_score': raw_exam_score,
                        'scaled_exam_score': scaled_exam,
                        'projected_total': projected_total,
                        'projected_letter': projected_letter,
                        'projected_point': projected_point,
                        'baseline_sgpa': baseline_sgpa,
                        'projected_sgpa': projected_sgpa,
                        'baseline_cgpa': baseline_cgpa,
                        'projected_cgpa': projected_cgpa,
                        'cgpa_delta': projected_cgpa - baseline_cgpa,
                        'baseline_cgpa_classification': classify_cgpa(baseline_cgpa),
                        'projected_cgpa_classification': classify_cgpa(projected_cgpa),
                    }

    if request.method == 'POST' and mode == 'target':
        target_raw = request.form.get('target_sgpa', '').strip()
        try:
            target_sgpa = float(target_raw)
        except ValueError:
            flash('Target SGPA must be a numeric value.', 'danger')
        else:
            if not (0 <= target_sgpa <= 4.0):
                flash('Target SGPA must be between 0.00 and 4.00.', 'danger')
            else:
                required_rows = allocate_uneven_target_points(active_enrollments, target_sgpa)

                for row in required_rows:
                    min_total_score = point_to_min_total_score(row['required_point'])
                    row['minimum_total_score'] = min_total_score
                    row['minimum_letter'] = score_to_letter(min_total_score)
                    row['difficulty_label'] = difficulty_label(row['difficulty_weight'])

                target_result = {
                    'target_sgpa': target_sgpa,
                    'active_credit_hours': active_credit_hours,
                    'required_total_grade_points': target_sgpa * active_credit_hours,
                    'projected_cgpa': (
                        ((past_cgpa * total_past_credits) + (target_sgpa * active_credit_hours))
                        / (total_past_credits + active_credit_hours)
                        if (total_past_credits + active_credit_hours)
                        else 0.0
                    ),
                    'required_rows': required_rows,
                }
                target_result['projected_cgpa_classification'] = classify_cgpa(target_result['projected_cgpa'])

    return render_template(
        'student/gpa_simulator.html',
        student=student,
        active_enrollments=active_enrollments,
        active_period=active_period,
        past_cgpa=past_cgpa,
        total_past_credits=total_past_credits,
        past_cgpa_classification=classify_cgpa(past_cgpa),
        mode=mode,
        single_result=single_result,
        target_result=target_result,
    )


@student_bp.route('/financials')
@login_required
def financials():
    """Display student financial status summary."""
    student = get_current_student()
    if not student:
        session.clear()
        flash('Student record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    records = (
        FinancialStatus.query.filter_by(student_id=student.student_id)
        .order_by(FinancialStatus.academic_year.desc())
        .all()
    )

    total_billed = sum(float(record.amount_billed) for record in records)
    total_paid = sum(float(record.amount_paid) for record in records)
    total_arrears = total_billed - total_paid

    return render_template(
        'student/financials.html',
        student=student,
        records=records,
        total_billed=total_billed,
        total_paid=total_paid,
        total_arrears=total_arrears,
    )


@student_bp.route('/helpdesk', methods=['GET', 'POST'])
@login_required
def helpdesk():
    """Support ticket creation and listing."""
    student = get_current_student()
    if not student:
        session.clear()
        flash('Student record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    enrolled_course_codes = {
        enrollment.course_code
        for enrollment in Enrollment.query.filter_by(student_id=student.student_id).all()
    }

    if request.method == 'POST':
        ticket_type = request.form.get('ticket_type', '').strip()
        priority = request.form.get('priority', 'Medium').strip()
        description = request.form.get('description', '').strip()
        course_code = request.form.get('course_code', '').strip() or None

        if ticket_type not in {'Academic', 'Technical'} or not description:
            flash('Please provide a valid ticket type and description.', 'danger')
            return redirect(url_for('student.helpdesk'))
        if priority not in {'Low', 'Medium', 'High'}:
            flash('Invalid priority selected.', 'danger')
            return redirect(url_for('student.helpdesk'))
        if course_code and course_code not in enrolled_course_codes:
            flash('Selected course is not part of your current enrollments.', 'danger')
            return redirect(url_for('student.helpdesk'))

        ticket = SupportTicket(
            student_id=student.student_id,
            course_code=course_code,
            ticket_type=ticket_type,
            priority=priority,
            description=description,
        )
        db.session.add(ticket)
        db.session.commit()
        flash('Support ticket submitted successfully.', 'success')
        return redirect(url_for('student.helpdesk'))

    status_filter = request.args.get('status', 'All').strip()
    if status_filter not in {'All', 'Open', 'Pending', 'Resolved'}:
        status_filter = 'All'

    sort_filter = request.args.get('sort', 'newest').strip()
    if sort_filter not in {'newest', 'oldest', 'ticket_id'}:
        sort_filter = 'newest'

    query = SupportTicket.query.filter_by(student_id=student.student_id)
    if status_filter != 'All':
        query = query.filter(SupportTicket.status == status_filter)

    if sort_filter == 'oldest':
        tickets = query.order_by(
            SupportTicket.date_submitted.asc(),
            SupportTicket.ticket_id.asc(),
        ).all()
    elif sort_filter == 'ticket_id':
        tickets = query.order_by(
            SupportTicket.ticket_id.asc(),
        ).all()
    else:
        tickets = query.order_by(
            SupportTicket.date_submitted.desc(),
            SupportTicket.ticket_id.desc(),
        ).all()

    counts_q = SupportTicket.query.filter_by(student_id=student.student_id)
    status_counts = {
        'All': counts_q.count(),
        'Open': counts_q.filter(SupportTicket.status == 'Open').count(),
        'Pending': counts_q.filter(SupportTicket.status == 'Pending').count(),
        'Resolved': counts_q.filter(SupportTicket.status == 'Resolved').count(),
    }
    courses = (
        Course.query.join(Enrollment, Enrollment.course_code == Course.course_code)
        .filter(Enrollment.student_id == student.student_id)
        .group_by(Course.course_code)
        .order_by(Course.course_code.asc())
        .all()
    )

    return render_template(
        'student/helpdesk.html',
        student=student,
        tickets=tickets,
        courses=courses,
        status_filter=status_filter,
        sort_filter=sort_filter,
        status_counts=status_counts,
    )


@student_bp.route('/logout')
@login_required
def logout():
    """Logout the current student."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('public.login'))
