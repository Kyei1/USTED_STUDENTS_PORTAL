"""Lecturer routes blueprint for the USTED Students Portal."""

from functools import wraps
from decimal import Decimal
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from flask import Blueprint, render_template, session, redirect, url_for, flash, request, Response, current_app, make_response
from sqlalchemy import and_, func, or_
import csv
import os
from io import StringIO
from uuid import uuid4

from models import Lecturer, CourseLecturer, Course, Enrollment, Student, Grade, SupportTicket, Announcement, Resource, db
from services.gpa_service import score_to_letter, scaled_exam_score
from services.lecturer_service import (
    build_lecturer_course_worklist,
    build_lecturer_draft_workspace,
    build_lecturer_resource_hub,
    submit_lecturer_drafts_to_hod,
)


lecturer_bp = Blueprint(
    'lecturer',
    __name__,
    url_prefix='/lecturer',
)

ALLOWED_RESOURCE_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt', 'csv', 'zip'
}


def lecturer_login_required(view_func):
    """Decorator to require lecturer login for protected lecturer routes."""
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if session.get('user_role') != 'lecturer' or not session.get('lecturer_id'):
            flash('Please sign in as lecturer to continue.', 'warning')
            return redirect(url_for('public.login'))
        return view_func(*args, **kwargs)
    return wrapped_view


def get_current_lecturer():
    """Resolve lecturer from active session."""
    lecturer_id = session.get('lecturer_id')
    if not lecturer_id:
        return None
    return Lecturer.query.filter_by(staff_id=lecturer_id).first()


def _lecturer_course_allocation(staff_id, course_code):
    """Resolve a lecturer's latest allocation row for a course."""
    return (
        CourseLecturer.query
        .join(Course, Course.course_code == CourseLecturer.course_code)
        .filter(
            CourseLecturer.staff_id == staff_id,
            CourseLecturer.course_code == course_code,
        )
        .order_by(CourseLecturer.academic_year.desc())
        .first()
    )


def _save_course_resource_file(file_storage, course_code):
    """Persist an uploaded resource file and return web path and original filename."""
    original_name = secure_filename((file_storage.filename or '').strip())
    if not original_name:
        raise ValueError('Select a file to upload.')

    extension = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else ''
    if extension not in ALLOWED_RESOURCE_EXTENSIONS:
        raise ValueError('Unsupported file type. Upload PDF, DOCX, PPTX, XLSX, TXT, CSV, or ZIP.')

    course_segment = secure_filename(course_code.lower()) or 'course'
    relative_dir = os.path.join('uploads', 'course_resources', course_segment)
    absolute_dir = os.path.join(current_app.static_folder, relative_dir)
    os.makedirs(absolute_dir, exist_ok=True)

    stored_name = f"{uuid4().hex}_{original_name}"
    absolute_file_path = os.path.join(absolute_dir, stored_name)
    file_storage.save(absolute_file_path)

    web_path = f"/static/{relative_dir.replace(os.sep, '/')}/{stored_name}"
    return web_path, original_name


def _delete_local_resource_file(file_path):
    """Delete a locally stored resource file if it belongs to static uploads."""
    if not file_path or not file_path.startswith('/static/uploads/course_resources/'):
        return

    relative_path = file_path.replace('/static/', '', 1)
    absolute_path = os.path.abspath(os.path.join(current_app.root_path, 'static', relative_path))
    static_root = os.path.abspath(current_app.static_folder)

    if not absolute_path.startswith(static_root):
        return

    if os.path.isfile(absolute_path):
        os.remove(absolute_path)


@lecturer_bp.route('/dashboard')
@lecturer_login_required
def dashboard():
    """Lecturer dashboard with assigned courses and roster counts."""
    lecturer = get_current_lecturer()
    if not lecturer:
        session.clear()
        flash('Lecturer record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    assigned_rows = (
        CourseLecturer.query
        .join(Course, Course.course_code == CourseLecturer.course_code)
        .filter(CourseLecturer.staff_id == lecturer.staff_id)
        .order_by(CourseLecturer.academic_year.desc(), Course.course_code.asc())
        .all()
    )

    assignment_scope = {(row.course_code, row.academic_year) for row in assigned_rows}
    scope_filter = None
    if assignment_scope:
        scope_filter = or_(
            *[
                and_(Enrollment.course_code == course_code, Enrollment.academic_year == academic_year)
                for course_code, academic_year in assignment_scope
            ]
        )

    if scope_filter is not None:
        roster_counts = {
            course_code: count
            for course_code, count in (
                Enrollment.query
                .with_entities(Enrollment.course_code, func.count(func.distinct(Enrollment.student_id)))
                .filter(scope_filter)
                .group_by(Enrollment.course_code)
                .all()
            )
        }
        total_students = (
            Enrollment.query
            .with_entities(func.count(func.distinct(Enrollment.student_id)))
            .filter(scope_filter)
            .scalar()
            or 0
        )
        grade_workspace_count = (
            Grade.query
            .join(Enrollment, Enrollment.enrollment_id == Grade.enrollment_id)
            .filter(scope_filter, Grade.approval_status == 'Draft')
            .count()
        )
    else:
        roster_counts = {}
        total_students = 0
        grade_workspace_count = 0

    lecturer_course_codes = [row.course_code for row in assigned_rows] if assigned_rows else []
    pending_academic_tickets = (
        SupportTicket.query
        .filter(
            SupportTicket.course_code.in_(lecturer_course_codes),
            SupportTicket.ticket_type == 'Academic',
            SupportTicket.status.in_(['Open', 'Pending'])
        )
        .count()
    ) if lecturer_course_codes else 0

    top_announcements = (
        Announcement.query
        .filter(Announcement.target_audience.in_(['All', 'Lecturers']))
        .order_by(Announcement.date_posted.desc())
        .limit(3)
        .all()
    )

    return render_template(
        'lecturer/dashboard.html',
        lecturer=lecturer,
        assigned_rows=assigned_rows,
        roster_counts=roster_counts,
        total_courses=len({row.course_code for row in assigned_rows}),
        total_students=total_students,
        grade_workspace_count=grade_workspace_count,
        pending_academic_tickets=pending_academic_tickets,
        top_announcements=top_announcements,
    )


@lecturer_bp.route('/profile')
@lecturer_login_required
def profile():
    """Display lecturer profile details."""
    lecturer = get_current_lecturer()
    if not lecturer:
        session.clear()
        flash('Lecturer record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    assigned_count = CourseLecturer.query.filter_by(staff_id=lecturer.staff_id).count()
    return render_template(
        'lecturer/profile.html',
        lecturer=lecturer,
        assigned_count=assigned_count,
    )


@lecturer_bp.route('/account-settings', methods=['GET', 'POST'])
@lecturer_login_required
def account_settings():
    """Allow lecturer to update email and password."""
    lecturer = get_current_lecturer()
    if not lecturer:
        session.clear()
        flash('Lecturer record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    if request.method == 'POST':
        email = (request.form.get('email_address') or '').strip().lower()
        new_password = (request.form.get('new_password') or '').strip()
        confirm_password = (request.form.get('confirm_password') or '').strip()

        if not email:
            flash('Email address is required.', 'danger')
            return redirect(url_for('lecturer.account_settings'))

        existing = Lecturer.query.filter(
            Lecturer.email_address == email,
            Lecturer.staff_id != lecturer.staff_id,
        ).first()
        if existing:
            flash('That email address is already used by another account.', 'danger')
            return redirect(url_for('lecturer.account_settings'))

        lecturer.email_address = email

        if new_password or confirm_password:
            if len(new_password) < 6:
                flash('New password must be at least 6 characters long.', 'danger')
                return redirect(url_for('lecturer.account_settings'))
            if new_password != confirm_password:
                flash('Password confirmation does not match.', 'danger')
                return redirect(url_for('lecturer.account_settings'))
            lecturer.password_hash = generate_password_hash(new_password)

        db.session.commit()
        flash('Account settings updated successfully.', 'success')
        return redirect(url_for('lecturer.account_settings'))

    return render_template('lecturer/account_settings.html', lecturer=lecturer)


@lecturer_bp.route('/course/<course_code>/roster', methods=['GET', 'POST'])
@lecturer_bp.route('/grading/<course_code>', methods=['GET', 'POST'])
@lecturer_login_required
def course_roster(course_code):
    """Display course roster and allow lecturer grade entry for a period."""
    lecturer = get_current_lecturer()
    if not lecturer:
        session.clear()
        flash('Lecturer record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    allocation = (
        CourseLecturer.query
        .join(Course, Course.course_code == CourseLecturer.course_code)
        .filter(
            CourseLecturer.staff_id == lecturer.staff_id,
            CourseLecturer.course_code == course_code,
        )
        .order_by(CourseLecturer.academic_year.desc())
        .first()
    )

    if not allocation:
        flash('You are not assigned to this course.', 'danger')
        return redirect(url_for('lecturer.dashboard'))

    selected_year = (request.values.get('academic_year') or allocation.academic_year).strip()
    selected_semester = (request.values.get('semester') or 'First').strip().title()
    if selected_semester not in {'First', 'Second'}:
        selected_semester = 'First'

    if request.method == 'POST':
        upload_action = (request.form.get('upload_action') or '').strip()
        if upload_action == 'import_ca_csv':
            upload = request.files.get('ca_csv_file')
            if not upload or not upload.filename:
                flash('Select a CSV file to upload.', 'danger')
                return redirect(url_for('lecturer.course_roster', course_code=course_code, academic_year=selected_year, semester=selected_semester))

            try:
                payload = upload.read().decode('utf-8-sig')
            except UnicodeDecodeError:
                flash('CSV must be UTF-8 encoded.', 'danger')
                return redirect(url_for('lecturer.course_roster', course_code=course_code, academic_year=selected_year, semester=selected_semester))

            csv_reader = csv.DictReader(StringIO(payload))
            if not csv_reader.fieldnames:
                flash('CSV is empty. Include headers: student_id, ca_score.', 'danger')
                return redirect(url_for('lecturer.course_roster', course_code=course_code, academic_year=selected_year, semester=selected_semester))

            normalized_headers = {header.strip().lower(): header for header in csv_reader.fieldnames if header}
            student_col = normalized_headers.get('student_id') or normalized_headers.get('studentid')
            ca_col = normalized_headers.get('ca_score') or normalized_headers.get('ca')
            ic_col = normalized_headers.get('ic')

            if not student_col or not ca_col:
                flash('CSV headers must include student_id and ca_score.', 'danger')
                return redirect(url_for('lecturer.course_roster', course_code=course_code, academic_year=selected_year, semester=selected_semester))

            enrollment_map = {
                row.student_id: row
                for row in Enrollment.query.filter_by(
                    course_code=course_code,
                    academic_year=selected_year,
                    semester=selected_semester,
                ).all()
            }

            imported_count = 0
            ic_count = 0
            skipped_count = 0

            for raw_row in csv_reader:
                student_id = (raw_row.get(student_col) or '').strip()
                ca_raw = (raw_row.get(ca_col) or '').strip()
                ic_raw = (raw_row.get(ic_col) or '').strip().lower() if ic_col else ''
                mark_ic = ic_raw in {'1', 'true', 'yes', 'y', 'ic'}

                if not student_id:
                    skipped_count += 1
                    continue

                enrollment = enrollment_map.get(student_id)
                if not enrollment:
                    skipped_count += 1
                    continue

                grade = Grade.query.filter_by(enrollment_id=enrollment.enrollment_id).first()
                if not grade:
                    grade = Grade(enrollment_id=enrollment.enrollment_id)
                    db.session.add(grade)

                if grade.approval_status in {'Pending_Board', 'Published'}:
                    skipped_count += 1
                    continue

                if mark_ic:
                    grade.grade_letter = 'IC'
                    grade.ca_score = Decimal('0.00')
                    grade.exam_score = Decimal('0.00')
                    grade.total_score = Decimal('0.00')
                    grade.is_ca_published = False
                    grade.approval_status = 'Draft'
                    ic_count += 1
                    continue

                try:
                    ca_score = float(ca_raw)
                except (TypeError, ValueError):
                    skipped_count += 1
                    continue

                if ca_score < 0 or ca_score > 40:
                    skipped_count += 1
                    continue

                grade.ca_score = Decimal(f"{ca_score:.2f}")
                grade.exam_score = None
                grade.total_score = None
                grade.grade_letter = None
                grade.is_ca_published = False
                grade.approval_status = 'Draft'
                imported_count += 1

            db.session.commit()

            if imported_count:
                flash(f'{imported_count} CA score(s) imported and saved as Draft.', 'success')
            if ic_count:
                flash(f'{ic_count} row(s) marked as IC.', 'info')
            if skipped_count:
                flash(f'{skipped_count} row(s) were skipped (invalid student, locked status, or invalid score).', 'warning')

            return redirect(url_for('lecturer.course_roster', course_code=course_code, academic_year=selected_year, semester=selected_semester))

        bulk_action = (request.form.get('bulk_action') or '').strip()
        has_bulk_scores = any(key.startswith('ca_score_') for key in request.form.keys())
        has_single_enrollment = bool((request.form.get('enrollment_id') or '').strip())

        if bulk_action in ('save_all_drafts', 'submit_all_hod', 'publish_all_ca') or (has_bulk_scores and not has_single_enrollment):
            if not bulk_action and has_bulk_scores:
                bulk_action = 'save_all_drafts'

            saved_count = 0
            submitted_count = 0
            published_ca_count = 0
            error_count = 0

            for key in request.form.keys():
                if not key.startswith('ca_score_'):
                    continue

                enrollment_id_str = key.replace('ca_score_', '')
                try:
                    enrollment_id_int = int(enrollment_id_str)
                except (TypeError, ValueError):
                    error_count += 1
                    continue

                ca_raw = request.form.get(f'ca_score_{enrollment_id_str}', '').strip()
                exam_raw = request.form.get(f'raw_exam_score_{enrollment_id_str}', '').strip()
                is_ic = bool(request.form.get(f'ic_{enrollment_id_str}'))

                enrollment = Enrollment.query.filter_by(
                    enrollment_id=enrollment_id_int,
                    course_code=course_code,
                    academic_year=selected_year,
                    semester=selected_semester,
                ).first()

                if not enrollment:
                    error_count += 1
                    continue

                grade = Grade.query.filter_by(enrollment_id=enrollment.enrollment_id).first()
                if not grade:
                    grade = Grade(enrollment_id=enrollment.enrollment_id)
                    db.session.add(grade)

                if is_ic:
                    grade.grade_letter = 'IC'
                    grade.ca_score = Decimal("0.00")
                    grade.exam_score = Decimal("0.00")
                    grade.total_score = Decimal("0.00")
                    grade.is_ca_published = False
                    grade.approval_status = 'Pending_HOD' if bulk_action == 'submit_all_hod' else 'Draft'
                    if bulk_action == 'submit_all_hod':
                        submitted_count += 1
                    else:
                        saved_count += 1
                    continue

                if bulk_action == 'publish_all_ca':
                    if ca_raw:
                        try:
                            ca_score = float(ca_raw)
                        except (TypeError, ValueError):
                            error_count += 1
                            continue
                        if ca_score < 0 or ca_score > 40:
                            error_count += 1
                            continue
                        if not grade.is_ca_published:
                            grade.ca_score = Decimal(f"{ca_score:.2f}")
                    elif grade.ca_score is None:
                        continue

                    if not grade.is_ca_published:
                        grade.is_ca_published = True
                        published_ca_count += 1
                    continue

                if not ca_raw and not exam_raw:
                    continue

                if grade.is_ca_published:
                    if grade.ca_score is None:
                        error_count += 1
                        continue
                    ca_score = float(grade.ca_score)
                else:
                    if not ca_raw:
                        error_count += 1
                        continue
                    try:
                        ca_score = float(ca_raw)
                    except (TypeError, ValueError):
                        error_count += 1
                        continue
                    if ca_score < 0 or ca_score > 40:
                        error_count += 1
                        continue
                    grade.ca_score = Decimal(f"{ca_score:.2f}")

                if not exam_raw:
                    error_count += 1
                    continue

                try:
                    raw_exam_score = float(exam_raw)
                except (TypeError, ValueError):
                    error_count += 1
                    continue

                if raw_exam_score < 0 or raw_exam_score > 100:
                    error_count += 1
                    continue

                exam_component = scaled_exam_score(raw_exam_score)
                total_score = round(ca_score + exam_component, 2)

                grade.exam_score = Decimal(f"{exam_component:.2f}")
                grade.total_score = Decimal(f"{total_score:.2f}")
                grade.grade_letter = score_to_letter(total_score)
                grade.approval_status = 'Pending_HOD' if bulk_action == 'submit_all_hod' else 'Draft'

                if bulk_action == 'submit_all_hod':
                    submitted_count += 1
                else:
                    saved_count += 1

            db.session.commit()

            if error_count > 0:
                flash(f'Warning: {error_count} entry/entries skipped due to invalid data.', 'warning')
            if published_ca_count > 0:
                flash(f'{published_ca_count} student(s) had their CA scores published.', 'success')
            if saved_count > 0:
                flash(f'{saved_count} grade(s) saved as draft.', 'success')
            if submitted_count > 0:
                flash(f'{submitted_count} grade(s) submitted to HOD queue.', 'success')

            return redirect(url_for('lecturer.course_roster', course_code=course_code, academic_year=selected_year, semester=selected_semester))

        enrollment_id = (request.form.get('enrollment_id') or '').strip()
        ca_raw = (request.form.get('ca_score') or '').strip()
        exam_raw = (request.form.get('raw_exam_score') or '').strip()
        submit_action = (request.form.get('submit_action') or 'save_draft').strip()

        try:
            enrollment_id_int = int(enrollment_id)
        except (TypeError, ValueError):
            flash('Invalid enrollment record selected.', 'danger')
            return redirect(url_for('lecturer.course_roster', course_code=course_code, academic_year=selected_year, semester=selected_semester))

        enrollment = Enrollment.query.filter_by(
            enrollment_id=enrollment_id_int,
            course_code=course_code,
            academic_year=selected_year,
            semester=selected_semester,
        ).first()

        if not enrollment:
            flash('Enrollment record not found for selected period.', 'danger')
            return redirect(url_for('lecturer.course_roster', course_code=course_code, academic_year=selected_year, semester=selected_semester))

        grade = Grade.query.filter_by(enrollment_id=enrollment.enrollment_id).first()
        if not grade:
            grade = Grade(enrollment_id=enrollment.enrollment_id)
            db.session.add(grade)

        single_ic_flag = (request.form.get('single_ic') or '').strip().lower() in {'1', 'true', 'on', 'yes'}
        row_ic_flag = bool(request.form.get(f'ic_{enrollment_id_int}'))
        is_ic = single_ic_flag or row_ic_flag

        if is_ic:
            grade.grade_letter = 'IC'
            grade.ca_score = Decimal("0.00")
            grade.exam_score = Decimal("0.00")
            grade.total_score = Decimal("0.00")
            grade.is_ca_published = False
            grade.approval_status = 'Pending_HOD' if submit_action == 'submit_hod' else 'Draft'
        elif submit_action == 'publish_ca':
            if grade.is_ca_published:
                flash(f'CA score is already published for {enrollment.student.student_id}.', 'info')
                return redirect(url_for('lecturer.course_roster', course_code=course_code, academic_year=selected_year, semester=selected_semester))

            if not ca_raw:
                flash('Enter a CA score before publishing CA.', 'danger')
                return redirect(url_for('lecturer.course_roster', course_code=course_code, academic_year=selected_year, semester=selected_semester))

            try:
                ca_score = float(ca_raw)
            except (TypeError, ValueError):
                flash('CA score must be numeric.', 'danger')
                return redirect(url_for('lecturer.course_roster', course_code=course_code, academic_year=selected_year, semester=selected_semester))

            if ca_score < 0 or ca_score > 40:
                flash('CA score must be between 0 and 40.', 'danger')
                return redirect(url_for('lecturer.course_roster', course_code=course_code, academic_year=selected_year, semester=selected_semester))

            grade.ca_score = Decimal(f"{ca_score:.2f}")
            grade.is_ca_published = True
            grade.approval_status = grade.approval_status or 'Draft'
        else:
            if grade.is_ca_published:
                if grade.ca_score is None:
                    flash('Published CA score is missing and cannot be overridden.', 'danger')
                    return redirect(url_for('lecturer.course_roster', course_code=course_code, academic_year=selected_year, semester=selected_semester))
                ca_score = float(grade.ca_score)
            else:
                if not ca_raw:
                    flash('CA score is required.', 'danger')
                    return redirect(url_for('lecturer.course_roster', course_code=course_code, academic_year=selected_year, semester=selected_semester))
                try:
                    ca_score = float(ca_raw)
                except (TypeError, ValueError):
                    flash('CA score must be numeric.', 'danger')
                    return redirect(url_for('lecturer.course_roster', course_code=course_code, academic_year=selected_year, semester=selected_semester))

                if ca_score < 0 or ca_score > 40:
                    flash('CA score must be between 0 and 40.', 'danger')
                    return redirect(url_for('lecturer.course_roster', course_code=course_code, academic_year=selected_year, semester=selected_semester))

                grade.ca_score = Decimal(f"{ca_score:.2f}")

            if not exam_raw:
                flash('Raw exam score is required.', 'danger')
                return redirect(url_for('lecturer.course_roster', course_code=course_code, academic_year=selected_year, semester=selected_semester))

            try:
                raw_exam_score = float(exam_raw)
            except (TypeError, ValueError):
                flash('Raw exam score must be numeric.', 'danger')
                return redirect(url_for('lecturer.course_roster', course_code=course_code, academic_year=selected_year, semester=selected_semester))

            if raw_exam_score < 0 or raw_exam_score > 100:
                flash('Raw exam score must be between 0 and 100.', 'danger')
                return redirect(url_for('lecturer.course_roster', course_code=course_code, academic_year=selected_year, semester=selected_semester))

            exam_component = scaled_exam_score(raw_exam_score)
            total_score = round(ca_score + exam_component, 2)

            grade.exam_score = Decimal(f"{exam_component:.2f}")
            grade.total_score = Decimal(f"{total_score:.2f}")
            grade.grade_letter = score_to_letter(total_score)
            grade.approval_status = 'Pending_HOD' if submit_action == 'submit_hod' else 'Draft'

        db.session.commit()

        if submit_action == 'publish_ca':
            flash(f'CA score published for {enrollment.student.student_id}.', 'success')
        elif submit_action == 'submit_hod':
            flash(f'Grade submitted to HOD queue for {enrollment.student.student_id}.', 'success')
        else:
            flash(f'Grade draft saved for {enrollment.student.student_id}.', 'success')

        return redirect(url_for('lecturer.course_roster', course_code=course_code, academic_year=selected_year, semester=selected_semester))
    
    roster = (
        Enrollment.query
        .join(Student, Student.student_id == Enrollment.student_id)
        .outerjoin(Grade, Grade.enrollment_id == Enrollment.enrollment_id)
        .filter(
            Enrollment.course_code == course_code,
            Enrollment.academic_year == selected_year,
            Enrollment.semester == selected_semester,
        )
        .order_by(Student.last_name.asc(), Student.first_name.asc())
        .all()
    )

    def classify_enrollment_status(enrollment):
        grade = enrollment.grade
        if not grade or (
            grade.ca_score is None
            and grade.exam_score is None
            and not grade.grade_letter
            and not getattr(grade, 'is_ca_published', False)
        ):
            return {
                'key': 'No grade entered',
                'label': 'No grade entered',
                'badge_class': 'theme-badge-neutral',
                'tone_class': 'summary-tone-neutral',
            }

        if grade.grade_letter == 'IC':
            return {
                'key': 'IC marked',
                'label': 'IC marked',
                'badge_class': 'theme-badge-neutral',
                'tone_class': 'summary-tone-neutral',
            }

        if grade.approval_status == 'Published':
            return {
                'key': 'Published',
                'label': 'Published',
                'badge_class': 'theme-badge-maroon',
                'tone_class': 'summary-tone-maroon',
            }

        if grade.approval_status == 'Pending_Board':
            return {
                'key': 'Pending Board approval',
                'label': 'Pending Board approval',
                'badge_class': 'theme-badge-neutral',
                'tone_class': 'summary-tone-neutral',
            }

        if grade.approval_status == 'Pending_HOD':
            return {
                'key': 'Submitted to HOD',
                'label': 'Submitted to HOD',
                'badge_class': 'theme-badge-gold',
                'tone_class': 'summary-tone-gold',
            }

        if getattr(grade, 'is_ca_published', False):
            return {
                'key': 'CA Published',
                'label': 'CA Published',
                'badge_class': 'theme-badge-gold',
                'tone_class': 'summary-tone-gold',
            }

        return {
            'key': 'Grade entered',
            'label': 'Grade entered',
            'badge_class': 'theme-badge-soft',
            'tone_class': 'summary-tone-soft',
        }

    roster_rows = []
    summary_counts = {
        'No grade entered': 0,
        'Grade entered': 0,
        'CA Published': 0,
        'Submitted to HOD': 0,
        'Pending Board approval': 0,
        'Published': 0,
        'IC marked': 0,
    }

    for enrollment in roster:
        row_status = classify_enrollment_status(enrollment)
        summary_counts[row_status['key']] += 1

        grade = enrollment.grade
        ca_prefill = ''
        raw_exam_prefill = ''
        if grade and grade.ca_score is not None:
            ca_prefill = f"{float(grade.ca_score):.2f}"
        if grade and grade.exam_score is not None:
            raw_exam_prefill = f"{round((float(grade.exam_score) / 60.0) * 100.0, 2):.2f}"

        roster_rows.append(
            {
                'enrollment': enrollment,
                'ca_prefill': ca_prefill,
                'raw_exam_prefill': raw_exam_prefill,
                'row_status': row_status,
            }
        )

    if summary_counts.get('Pending Board approval', 0):
        workspace_status = {
            'label': 'Pending Board approval',
            'badge_class': 'theme-badge-neutral',
        }
    elif summary_counts.get('Submitted to HOD', 0):
        workspace_status = {
            'label': 'Submitted to HOD',
            'badge_class': 'theme-badge-gold',
        }
    elif summary_counts.get('CA Published', 0):
        workspace_status = {
            'label': 'CA Published',
            'badge_class': 'theme-badge-gold',
        }
    elif summary_counts.get('Grade entered', 0):
        workspace_status = {
            'label': 'Grade entered',
            'badge_class': 'theme-badge-soft',
        }
    elif summary_counts.get('IC marked', 0):
        workspace_status = {
            'label': 'IC marked',
            'badge_class': 'theme-badge-neutral',
        }
    elif summary_counts.get('Published', 0):
        workspace_status = {
            'label': 'Published',
            'badge_class': 'theme-badge-maroon',
        }
    else:
        workspace_status = {
            'label': 'No grades entered',
            'badge_class': 'theme-badge-neutral',
        }

    summary_cards = [
        {
            'label': 'No grade entered',
            'count': summary_counts['No grade entered'],
            'tone_class': 'summary-tone-neutral',
        },
        {
            'label': 'Grade entered',
            'count': summary_counts['Grade entered'],
            'tone_class': 'summary-tone-soft',
        },
        {
            'label': 'CA Published',
            'count': summary_counts['CA Published'],
            'tone_class': 'summary-tone-gold',
        },
        {
            'label': 'Submitted to HOD',
            'count': summary_counts['Submitted to HOD'],
            'tone_class': 'summary-tone-gold',
        },
        {
            'label': 'Pending Board approval',
            'count': summary_counts['Pending Board approval'],
            'tone_class': 'summary-tone-neutral',
        },
        {
            'label': 'Published',
            'count': summary_counts['Published'],
            'tone_class': 'summary-tone-maroon',
        },
        {
            'label': 'IC marked',
            'count': summary_counts['IC marked'],
            'tone_class': 'summary-tone-neutral',
        },
    ]

    period_options = sorted(
        {
            (row.academic_year, row.semester)
            for row in Enrollment.query.with_entities(Enrollment.academic_year, Enrollment.semester)
            .filter_by(course_code=course_code)
            .all()
        },
        key=lambda item: (item[0], 0 if item[1] == 'First' else 1),
        reverse=True,
    )
    period_years = sorted({year for year, _semester in period_options}, reverse=True)

    return render_template(
        'lecturer/course_roster.html',
        lecturer=lecturer,
        allocation=allocation,
        roster_rows=roster_rows,
        summary_cards=summary_cards,
        selected_year=selected_year,
        selected_semester=selected_semester,
        period_options=period_options,
        period_years=period_years,
        workspace_status=workspace_status,
    )


@lecturer_bp.route('/submission-queue')
@lecturer_login_required
def submission_queue():
    """Read-only course progress tracker for lecturer grade submissions."""
    lecturer = get_current_lecturer()
    if not lecturer:
        session.clear()
        flash('Lecturer record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    assigned_rows = (
        CourseLecturer.query
        .join(Course, Course.course_code == CourseLecturer.course_code)
        .filter(CourseLecturer.staff_id == lecturer.staff_id)
        .order_by(CourseLecturer.academic_year.desc(), Course.course_code.asc())
        .all()
    )

    assignment_scope = {(row.course_code, row.academic_year) for row in assigned_rows}
    scope_filter = None
    if assignment_scope:
        scope_filter = or_(
            *[
                and_(Enrollment.course_code == course_code, Enrollment.academic_year == academic_year)
                for course_code, academic_year in assignment_scope
            ]
        )

    trackers_map = {}
    for row in assigned_rows:
        if row.course_code not in trackers_map:
            trackers_map[row.course_code] = {
                'course_code': row.course_code,
                'course_name': row.course.course_name,
                'class_groups': set(),
                'academic_years': set(),
                'total_students': 0,
                'no_grade_count': 0,
                'draft_count': 0,
                'ca_published_count': 0,
                'pending_hod_count': 0,
                'pending_board_count': 0,
                'published_count': 0,
                'ic_count': 0,
            }
        trackers_map[row.course_code]['class_groups'].add(row.class_group)
        trackers_map[row.course_code]['academic_years'].add(row.academic_year)

    if scope_filter is not None:
        scoped_enrollments = (
            Enrollment.query
            .join(Course, Course.course_code == Enrollment.course_code)
            .join(Student, Student.student_id == Enrollment.student_id)
            .outerjoin(Grade, Grade.enrollment_id == Enrollment.enrollment_id)
            .filter(scope_filter)
            .order_by(Enrollment.course_code.asc(), Student.last_name.asc(), Student.first_name.asc())
            .all()
        )
    else:
        scoped_enrollments = []

    for enrollment in scoped_enrollments:
        tracker = trackers_map.get(enrollment.course_code)
        if not tracker:
            continue

        tracker['total_students'] += 1
        grade = enrollment.grade

        if not grade or (
            grade.ca_score is None
            and grade.exam_score is None
            and not grade.grade_letter
            and not bool(getattr(grade, 'is_ca_published', False))
        ):
            tracker['no_grade_count'] += 1
            continue

        if grade.grade_letter == 'IC':
            tracker['ic_count'] += 1
            continue

        if grade.approval_status == 'Published':
            tracker['published_count'] += 1
        elif grade.approval_status == 'Pending_Board':
            tracker['pending_board_count'] += 1
        elif grade.approval_status == 'Pending_HOD':
            tracker['pending_hod_count'] += 1
        elif bool(getattr(grade, 'is_ca_published', False)):
            tracker['ca_published_count'] += 1
        else:
            tracker['draft_count'] += 1

    course_trackers = []
    for tracker in trackers_map.values():
        total_students = tracker['total_students']
        processed_count = max(total_students - tracker['no_grade_count'], 0)
        progress_percent = int(round((processed_count / total_students) * 100)) if total_students else 0

        def segment_width(value):
            if not total_students:
                return 0
            return round((value / total_students) * 100, 1)

        tracker['class_groups'] = sorted(tracker['class_groups'])
        tracker['academic_years'] = sorted(tracker['academic_years'], reverse=True)
        tracker['processed_count'] = processed_count
        tracker['progress_percent'] = progress_percent
        tracker['segment_no_grade'] = segment_width(tracker['no_grade_count'])
        tracker['segment_draft'] = segment_width(tracker['draft_count'])
        tracker['segment_ca_published'] = segment_width(tracker['ca_published_count'])
        tracker['segment_pending_hod'] = segment_width(tracker['pending_hod_count'])
        tracker['segment_pending_board'] = segment_width(tracker['pending_board_count'])
        tracker['segment_published'] = segment_width(tracker['published_count'])
        tracker['segment_ic'] = segment_width(tracker['ic_count'])

        stage_counts = [
            ('Grade Entered', tracker['draft_count']),
            ('CA Published', tracker['ca_published_count']),
            ('Submitted to HOD', tracker['pending_hod_count']),
            ('Pending Board', tracker['pending_board_count']),
            ('Published', tracker['published_count']),
        ]

        highest_stage_index = -1
        for index, (_label, count) in enumerate(stage_counts):
            if count > 0:
                highest_stage_index = index

        if highest_stage_index == -1 and total_students > 0:
            highest_stage_index = 0

        checklist_steps = []
        for index, (label, count) in enumerate(stage_counts):
            reached_count = sum(stage_count for _stage_label, stage_count in stage_counts[index:])
            if highest_stage_index == -1:
                state = 'pending'
            elif index == highest_stage_index and count > 0:
                state = 'active'
            elif index < highest_stage_index and reached_count > 0:
                state = 'done'
            elif count > 0:
                state = 'done'
            else:
                state = 'pending'

            checklist_steps.append(
                {
                    'label': label,
                    'count': count,
                    'state': state,
                }
            )

        tracker['checklist_steps'] = checklist_steps
        course_trackers.append(tracker)

    course_trackers.sort(key=lambda item: item['course_code'])

    total_pending_hod = sum(item['pending_hod_count'] for item in course_trackers)
    total_pending_board = sum(item['pending_board_count'] for item in course_trackers)
    total_tracked_students = sum(item['total_students'] for item in course_trackers)

    response = make_response(
        render_template(
            'lecturer/submission_queue.html',
            lecturer=lecturer,
            course_trackers=course_trackers,
            total_pending_hod=total_pending_hod,
            total_pending_board=total_pending_board,
            total_tracked_students=total_tracked_students,
        )
    )
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@lecturer_bp.route('/course/<course_code>/grades-export')
@lecturer_login_required
def grades_export(course_code):
    """Export grades for a course as CSV."""
    lecturer = get_current_lecturer()
    if not lecturer:
        session.clear()
        flash('Lecturer record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    allocation = (
        CourseLecturer.query
        .filter(
            CourseLecturer.staff_id == lecturer.staff_id,
            CourseLecturer.course_code == course_code,
        )
        .first()
    )

    if not allocation:
        flash('You are not assigned to this course.', 'danger')
        return redirect(url_for('lecturer.dashboard'))

    grades_data = (
        Enrollment.query
        .join(Student, Student.student_id == Enrollment.student_id)
        .outerjoin(Grade, Grade.enrollment_id == Enrollment.enrollment_id)
        .filter(Enrollment.course_code == course_code)
        .order_by(Student.last_name.asc(), Student.first_name.asc())
        .all()
    )

    csv_buffer = StringIO()
    csv_writer = csv.writer(csv_buffer)
    csv_writer.writerow(['Student ID', 'First Name', 'Last Name', 'CA (0-40)', 'Exam Component (0-60)', 'Total (0-100)', 'Grade', 'Status', 'Academic Year', 'Semester'])

    for enrollment in grades_data:
        grade = enrollment.grade
        row = [
            enrollment.student.student_id,
            enrollment.student.first_name,
            enrollment.student.last_name,
            float(grade.ca_score) if grade and grade.ca_score else '',
            float(grade.exam_score) if grade and grade.exam_score else '',
            float(grade.total_score) if grade and grade.total_score else '',
            grade.grade_letter if grade and grade.grade_letter else '',
            grade.approval_status if grade else 'Not Graded',
            enrollment.academic_year,
            enrollment.semester,
        ]
        csv_writer.writerow(row)

    return Response(
        csv_buffer.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={course_code}_grades.csv'}
    )


@lecturer_bp.route('/logout')
@lecturer_login_required
def logout():
    """Clear lecturer session and return to login."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('public.login'))

@lecturer_bp.route('/my-courses')
@lecturer_login_required
def my_courses():
    """Display lecturer-scoped course worklist and grading workload counts."""
    lecturer = get_current_lecturer()
    if not lecturer:
        session.clear()
        flash('Lecturer record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    course_payload = build_lecturer_course_worklist(
        lecturer.staff_id,
        academic_year=request.args.get('academic_year', 'All'),
        class_group=request.args.get('class_group', 'All'),
        semester=request.args.get('semester', 'All'),
    )

    return render_template(
        'lecturer/my_courses.html',
        lecturer=lecturer,
        **course_payload,
    )

@lecturer_bp.route('/draft-grades', methods=['GET', 'POST'])
@lecturer_bp.route('/grade-workspace', methods=['GET', 'POST'])
@lecturer_login_required
def grade_workspace():
    """Cross-course workspace for Draft grade validation and bulk submission."""
    lecturer = get_current_lecturer()
    if not lecturer:
        session.clear()
        flash('Lecturer record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    if request.method == 'POST':
        selected_year = request.form.get('academic_year', 'All')
        selected_semester = request.form.get('semester', 'All')
        selected_course_code = request.form.get('course_code', 'All')
        action = (request.form.get('action') or '').strip()

        draft_payload = build_lecturer_draft_workspace(
            lecturer.staff_id,
            academic_year=selected_year,
            semester=selected_semester,
            course_code=selected_course_code,
        )

        if action == 'submit_all_hod':
            target_ids = [row['enrollment'].enrollment_id for row in draft_payload['draft_rows'] if row['is_valid']]
        elif action == 'submit_selected_hod':
            target_ids = request.form.getlist('selected_enrollment_ids')
        else:
            target_ids = []

        if not target_ids:
            flash('No Draft records selected for submission.', 'warning')
        else:
            result = submit_lecturer_drafts_to_hod(lecturer.staff_id, target_ids)
            if result['submitted']:
                flash(f"{result['submitted']} Draft record(s) submitted to HOD queue.", 'success')
            if result['invalid']:
                flash(f"{result['invalid']} record(s) were skipped due to incomplete or invalid grading data.", 'warning')
            if result['unauthorized'] or result['missing']:
                flash('Some selected records were outside your scope or no longer available.', 'danger')

        return redirect(
            url_for(
                'lecturer.grade_workspace',
                academic_year=selected_year,
                semester=selected_semester,
                course_code=selected_course_code,
            )
        )

    draft_payload = build_lecturer_draft_workspace(
        lecturer.staff_id,
        academic_year=request.args.get('academic_year', 'All'),
        semester=request.args.get('semester', 'All'),
        course_code=request.args.get('course_code', 'All'),
    )

    return render_template(
        'lecturer/draft_grades.html',
        lecturer=lecturer,
        **draft_payload,
    )


@lecturer_bp.route('/course/<course_code>/resources', methods=['GET'])
@lecturer_login_required
def course_resources(course_code):
    """View course resources for a lecturer-owned course."""
    lecturer = get_current_lecturer()
    if not lecturer:
        session.clear()
        flash('Lecturer record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    allocation = _lecturer_course_allocation(lecturer.staff_id, course_code)
    if not allocation:
        flash('You are not assigned to this course.', 'danger')
        return redirect(url_for('lecturer.my_courses'))

    resources = (
        db.session.query(Resource)
        .filter(
            Resource.course_code == course_code,
            Resource.resource_type == 'Course',
        )
        .order_by(Resource.upload_date.desc())
        .all()
    )

    return render_template(
        'lecturer/course_resources.html',
        lecturer=lecturer,
        allocation=allocation,
        resources=resources,
    )


@lecturer_bp.route('/course/<course_code>/resources/upload', methods=['POST'])
@lecturer_login_required
def upload_course_resource(course_code):
    """Upload a course resource for a lecturer-owned course."""
    lecturer = get_current_lecturer()
    if not lecturer:
        session.clear()
        flash('Lecturer record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    allocation = _lecturer_course_allocation(lecturer.staff_id, course_code)
    if not allocation:
        flash('You are not assigned to this course.', 'danger')
        return redirect(url_for('lecturer.my_courses'))

    upload = request.files.get('resource_file')
    resource_label = (request.form.get('resource_label') or '').strip()

    if not upload or not upload.filename:
        flash('Select a file before uploading.', 'warning')
        return redirect(url_for('lecturer.course_resources', course_code=course_code))

    try:
        file_path, original_name = _save_course_resource_file(upload, course_code)
    except ValueError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('lecturer.course_resources', course_code=course_code))

    resource = Resource(
        course_code=course_code,
        department_id=allocation.course.department_id,
        file_name=resource_label or original_name,
        resource_type='Course',
        file_path=file_path,
    )
    db.session.add(resource)
    db.session.commit()
    flash('Course resource uploaded successfully.', 'success')
    return redirect(url_for('lecturer.course_resources', course_code=course_code))


@lecturer_bp.route('/course/<course_code>/resources/<int:resource_id>/update', methods=['POST'])
@lecturer_login_required
def update_course_resource(course_code, resource_id):
    """Update a resource label and optionally replace the uploaded file."""
    lecturer = get_current_lecturer()
    if not lecturer:
        session.clear()
        flash('Lecturer record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    allocation = _lecturer_course_allocation(lecturer.staff_id, course_code)
    if not allocation:
        flash('You are not assigned to this course.', 'danger')
        return redirect(url_for('lecturer.my_courses'))

    resource = (
        Resource.query
        .filter_by(resource_id=resource_id, course_code=course_code, resource_type='Course')
        .first()
    )
    if not resource:
        flash('Resource record not found for this course.', 'danger')
        return redirect(url_for('lecturer.course_resources', course_code=course_code))

    resource_label = (request.form.get('resource_label') or '').strip()
    replacement = request.files.get('resource_file')

    if not resource_label and (not replacement or not replacement.filename):
        flash('No changes detected for this resource.', 'warning')
        return redirect(url_for('lecturer.course_resources', course_code=course_code))

    if resource_label:
        resource.file_name = resource_label

    if replacement and replacement.filename:
        try:
            file_path, _ = _save_course_resource_file(replacement, course_code)
        except ValueError as exc:
            flash(str(exc), 'danger')
            return redirect(url_for('lecturer.course_resources', course_code=course_code))

        old_path = resource.file_path
        resource.file_path = file_path
        _delete_local_resource_file(old_path)

    db.session.commit()
    flash('Course resource updated successfully.', 'success')
    return redirect(url_for('lecturer.course_resources', course_code=course_code))


@lecturer_bp.route('/course/<course_code>/resources/<int:resource_id>/delete', methods=['POST'])
@lecturer_login_required
def delete_course_resource(course_code, resource_id):
    """Delete a course resource from lecturer scope."""
    lecturer = get_current_lecturer()
    if not lecturer:
        session.clear()
        flash('Lecturer record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    allocation = _lecturer_course_allocation(lecturer.staff_id, course_code)
    if not allocation:
        flash('You are not assigned to this course.', 'danger')
        return redirect(url_for('lecturer.my_courses'))

    resource = (
        Resource.query
        .filter_by(resource_id=resource_id, course_code=course_code, resource_type='Course')
        .first()
    )
    if not resource:
        flash('Resource record not found for this course.', 'danger')
        return redirect(url_for('lecturer.course_resources', course_code=course_code))

    old_path = resource.file_path
    db.session.delete(resource)
    db.session.commit()
    _delete_local_resource_file(old_path)

    flash('Course resource deleted successfully.', 'success')
    return redirect(url_for('lecturer.course_resources', course_code=course_code))


@lecturer_bp.route('/resource-management')
@lecturer_login_required
def resource_management():
    """Display a lecturer resource hub for assigned courses."""
    lecturer = get_current_lecturer()
    if not lecturer:
        session.clear()
        flash('Lecturer record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    resource_payload = build_lecturer_resource_hub(lecturer.staff_id)

    return render_template(
        'lecturer/resource_management.html',
        lecturer=lecturer,
        **resource_payload,
    )

@lecturer_bp.route('/academic-helpdesk', methods=['GET', 'POST'])
@lecturer_login_required
def academic_helpdesk():
    """Lecturer view for Academic helpdesk tickets tied to their assigned courses."""
    lecturer = get_current_lecturer()
    if not lecturer:
        session.clear()
        return redirect(url_for('public.login'))

    assigned_course_codes = [
        row.course_code for row in 
        CourseLecturer.query.filter_by(staff_id=lecturer.staff_id).all()
    ]

    # Handle status updates
    if request.method == 'POST':
        ticket_id = request.form.get('ticket_id')
        new_status = request.form.get('status')
        if ticket_id and new_status in ['Open', 'Pending', 'Resolved']:
            ticket = SupportTicket.query.filter_by(ticket_id=ticket_id).first()
            # Double check it belongs to this lecturer
            if ticket and ticket.course_code in assigned_course_codes and ticket.ticket_type == 'Academic':
                ticket.status = new_status
                db.session.commit()
                flash(f'Ticket #{ticket_id} updated to {new_status}.', 'success')
            else:
                flash('Unauthorized or invalid ticket.', 'danger')
        return redirect(url_for('lecturer.academic_helpdesk'))

    # Query academic tickets for this lecturer's courses
    tickets = (
        SupportTicket.query
        .filter(
            SupportTicket.course_code.in_(assigned_course_codes),
            SupportTicket.ticket_type == 'Academic'
        )
        .order_by(
            # Sort open/pending to top
            db.case({
                'Open': 1,
                'Pending': 2,
                'Resolved': 3
            }, value=SupportTicket.status, else_=4),
            SupportTicket.date_submitted.desc()
        )
        .all()
    ) if assigned_course_codes else []

    return render_template('lecturer/academic_helpdesk.html', tickets=tickets)

