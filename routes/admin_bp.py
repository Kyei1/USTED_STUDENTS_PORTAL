"""Admin routes blueprint for the USTED Students Portal."""

from functools import wraps

from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from sqlalchemy import case

from models import Admin, Announcement, Course, Enrollment, Grade, Lecturer, Student, SupportTicket, db


admin_bp = Blueprint(
    'admin',
    __name__,
    url_prefix='/admin',
)


def admin_login_required(view_func):
    """Decorator to require admin login for protected admin routes."""
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if session.get('user_role') != 'admin' or not session.get('admin_id'):
            flash('Please sign in as admin to continue.', 'warning')
            return redirect(url_for('public.login'))
        return view_func(*args, **kwargs)
    return wrapped_view


def get_current_admin():
    """Resolve admin from active session."""
    admin_id = session.get('admin_id')
    if not admin_id:
        return None
    return Admin.query.filter_by(admin_id=admin_id).first()


def _normalize_filter(value, allowed_values, default_value):
    """Normalize request filter values to safe, expected options."""
    normalized = (value or default_value).strip()
    if normalized not in allowed_values:
        return default_value
    return normalized


def _grade_queue_redirect(status_filter, academic_year_filter, course_code_filter):
    """Redirect helper to keep admin grade queue filters stable after actions."""
    return redirect(
        url_for(
            'admin.grade_approvals',
            status=status_filter,
            academic_year=academic_year_filter,
            course_code=course_code_filter,
        )
    )


@admin_bp.route('/dashboard')
@admin_login_required
def dashboard():
    """Admin dashboard with governance KPIs and quick workflow entry points."""
    admin = get_current_admin()
    if not admin:
        session.clear()
        flash('Admin record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    grade_status_counts = {
        'Draft': Grade.query.filter_by(approval_status='Draft').count(),
        'Pending_HOD': Grade.query.filter_by(approval_status='Pending_HOD').count(),
        'Pending_Board': Grade.query.filter_by(approval_status='Pending_Board').count(),
        'Published': Grade.query.filter_by(approval_status='Published').count(),
    }

    ticket_status_counts = {
        'Open': SupportTicket.query.filter_by(status='Open').count(),
        'Pending': SupportTicket.query.filter_by(status='Pending').count(),
        'Resolved': SupportTicket.query.filter_by(status='Resolved').count(),
    }

    recent_pending_grades = (
        Grade.query
        .join(Enrollment, Enrollment.enrollment_id == Grade.enrollment_id)
        .join(Student, Student.student_id == Enrollment.student_id)
        .join(Course, Course.course_code == Enrollment.course_code)
        .filter(Grade.approval_status.in_(['Pending_HOD', 'Pending_Board']))
        .order_by(Enrollment.academic_year.desc(), Course.course_code.asc(), Student.last_name.asc())
        .limit(8)
        .all()
    )

    recent_tickets = (
        SupportTicket.query
        .join(Student, Student.student_id == SupportTicket.student_id)
        .outerjoin(Course, Course.course_code == SupportTicket.course_code)
        .order_by(SupportTicket.date_submitted.desc(), SupportTicket.ticket_id.desc())
        .limit(8)
        .all()
    )

    latest_announcements = (
        Announcement.query
        .order_by(Announcement.date_posted.desc(), Announcement.announcement_id.desc())
        .limit(5)
        .all()
    )

    return render_template(
        'admin/dashboard.html',
        admin=admin,
        total_students=Student.query.count(),
        total_lecturers=Lecturer.query.count(),
        total_courses=Course.query.count(),
        grade_status_counts=grade_status_counts,
        ticket_status_counts=ticket_status_counts,
        unresolved_ticket_count=ticket_status_counts['Open'] + ticket_status_counts['Pending'],
        recent_pending_grades=recent_pending_grades,
        recent_tickets=recent_tickets,
        latest_announcements=latest_announcements,
    )


@admin_bp.route('/grade-approvals', methods=['GET', 'POST'])
@admin_login_required
def grade_approvals():
    """Review and transition grade records through admin approval stages."""
    admin = get_current_admin()
    if not admin:
        session.clear()
        flash('Admin record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    status_filter = _normalize_filter(
        request.args.get('status'),
        {'All', 'Draft', 'Pending_HOD', 'Pending_Board', 'Published'},
        'All',
    )
    academic_year_filter = (request.args.get('academic_year') or 'All').strip() or 'All'
    course_code_filter = (request.args.get('course_code') or 'All').strip() or 'All'

    if request.method == 'POST':
        status_filter = _normalize_filter(
            request.form.get('status_filter'),
            {'All', 'Draft', 'Pending_HOD', 'Pending_Board', 'Published'},
            'All',
        )
        academic_year_filter = (request.form.get('academic_year_filter') or 'All').strip() or 'All'
        course_code_filter = (request.form.get('course_code_filter') or 'All').strip() or 'All'

        action = (request.form.get('action') or '').strip()
        if action not in {'approve_hod', 'publish_board', 'return_hod', 'return_draft'}:
            flash('Unsupported approval action.', 'warning')
            return _grade_queue_redirect(status_filter, academic_year_filter, course_code_filter)

        raw_grade_ids = []
        single_grade_id = (request.form.get('grade_id') or '').strip()
        if single_grade_id:
            raw_grade_ids.append(single_grade_id)
        raw_grade_ids.extend(request.form.getlist('selected_grade_ids'))

        grade_ids = []
        for raw_grade_id in raw_grade_ids:
            try:
                grade_ids.append(int(raw_grade_id))
            except (TypeError, ValueError):
                continue
        grade_ids = sorted(set(grade_ids))

        if not grade_ids:
            flash('Select at least one grade record to continue.', 'warning')
            return _grade_queue_redirect(status_filter, academic_year_filter, course_code_filter)

        transition_map = {
            'approve_hod': {'Pending_HOD': 'Pending_Board'},
            'publish_board': {'Pending_Board': 'Published'},
            'return_hod': {'Pending_Board': 'Pending_HOD'},
            'return_draft': {'Pending_HOD': 'Draft', 'Pending_Board': 'Draft'},
        }

        candidate_grades = Grade.query.filter(Grade.grade_id.in_(grade_ids)).all()
        updated_count = 0
        skipped_count = 0

        for grade in candidate_grades:
            next_status = transition_map[action].get(grade.approval_status)
            if not next_status:
                skipped_count += 1
                continue

            grade.approval_status = next_status
            updated_count += 1

        if updated_count:
            db.session.commit()
            flash(f'{updated_count} grade record(s) updated successfully.', 'success')
        else:
            flash('No records matched the selected workflow action.', 'warning')

        if skipped_count:
            flash(f'{skipped_count} record(s) were skipped due to invalid stage transition.', 'info')

        return _grade_queue_redirect(status_filter, academic_year_filter, course_code_filter)

    grade_query = (
        Grade.query
        .join(Enrollment, Enrollment.enrollment_id == Grade.enrollment_id)
        .join(Student, Student.student_id == Enrollment.student_id)
        .join(Course, Course.course_code == Enrollment.course_code)
    )

    if status_filter != 'All':
        grade_query = grade_query.filter(Grade.approval_status == status_filter)
    if academic_year_filter != 'All':
        grade_query = grade_query.filter(Enrollment.academic_year == academic_year_filter)
    if course_code_filter != 'All':
        grade_query = grade_query.filter(Enrollment.course_code == course_code_filter)

    stage_order = case(
        (Grade.approval_status == 'Pending_HOD', 0),
        (Grade.approval_status == 'Pending_Board', 1),
        (Grade.approval_status == 'Draft', 2),
        (Grade.approval_status == 'Published', 3),
        else_=4,
    )

    queue_rows = (
        grade_query
        .order_by(
            stage_order.asc(),
            Enrollment.academic_year.desc(),
            Enrollment.semester.desc(),
            Course.course_code.asc(),
            Student.last_name.asc(),
            Student.first_name.asc(),
        )
        .all()
    )

    status_counts = {
        'Draft': Grade.query.filter_by(approval_status='Draft').count(),
        'Pending_HOD': Grade.query.filter_by(approval_status='Pending_HOD').count(),
        'Pending_Board': Grade.query.filter_by(approval_status='Pending_Board').count(),
        'Published': Grade.query.filter_by(approval_status='Published').count(),
    }

    academic_year_options = [
        year
        for (year,) in (
            Enrollment.query
            .with_entities(Enrollment.academic_year)
            .distinct()
            .order_by(Enrollment.academic_year.desc())
            .all()
        )
    ]
    course_code_options = [
        code
        for (code,) in (
            Course.query
            .with_entities(Course.course_code)
            .order_by(Course.course_code.asc())
            .all()
        )
    ]

    return render_template(
        'admin/grade_approvals.html',
        admin=admin,
        queue_rows=queue_rows,
        status_counts=status_counts,
        status_filter=status_filter,
        academic_year_filter=academic_year_filter,
        course_code_filter=course_code_filter,
        academic_year_options=academic_year_options,
        course_code_options=course_code_options,
    )


@admin_bp.route('/helpdesk', methods=['GET', 'POST'])
@admin_login_required
def helpdesk():
    """Oversee and resolve student support tickets across the institution."""
    admin = get_current_admin()
    if not admin:
        session.clear()
        flash('Admin record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    status_filter = _normalize_filter(
        request.args.get('status'),
        {'All', 'Open', 'Pending', 'Resolved'},
        'All',
    )
    ticket_type_filter = _normalize_filter(
        request.args.get('ticket_type'),
        {'All', 'Academic', 'Technical'},
        'All',
    )
    priority_filter = _normalize_filter(
        request.args.get('priority'),
        {'All', 'High', 'Medium', 'Low'},
        'All',
    )
    sort_filter = _normalize_filter(
        request.args.get('sort'),
        {'newest', 'oldest', 'priority'},
        'newest',
    )

    if request.method == 'POST':
        status_filter = _normalize_filter(
            request.form.get('status_filter'),
            {'All', 'Open', 'Pending', 'Resolved'},
            'All',
        )
        ticket_type_filter = _normalize_filter(
            request.form.get('ticket_type_filter'),
            {'All', 'Academic', 'Technical'},
            'All',
        )
        priority_filter = _normalize_filter(
            request.form.get('priority_filter'),
            {'All', 'High', 'Medium', 'Low'},
            'All',
        )
        sort_filter = _normalize_filter(
            request.form.get('sort_filter'),
            {'newest', 'oldest', 'priority'},
            'newest',
        )

        ticket_id_raw = (request.form.get('ticket_id') or '').strip()
        next_status = _normalize_filter(
            request.form.get('status') or '',
            {'Open', 'Pending', 'Resolved'},
            '',
        )

        if not next_status:
            flash('Invalid ticket status selected.', 'danger')
            return redirect(
                url_for(
                    'admin.helpdesk',
                    status=status_filter,
                    ticket_type=ticket_type_filter,
                    priority=priority_filter,
                    sort=sort_filter,
                )
            )

        try:
            ticket_id = int(ticket_id_raw)
        except (TypeError, ValueError):
            flash('Invalid ticket identifier.', 'danger')
            return redirect(
                url_for(
                    'admin.helpdesk',
                    status=status_filter,
                    ticket_type=ticket_type_filter,
                    priority=priority_filter,
                    sort=sort_filter,
                )
            )

        ticket = SupportTicket.query.filter_by(ticket_id=ticket_id).first()
        if not ticket:
            flash('Ticket not found.', 'danger')
            return redirect(
                url_for(
                    'admin.helpdesk',
                    status=status_filter,
                    ticket_type=ticket_type_filter,
                    priority=priority_filter,
                    sort=sort_filter,
                )
            )

        ticket.status = next_status
        if next_status == 'Resolved':
            ticket.resolved_by_admin_id = admin.admin_id
        else:
            ticket.resolved_by_admin_id = None

        db.session.commit()
        flash(f'Ticket #{ticket.ticket_id} updated to {next_status}.', 'success')

        return redirect(
            url_for(
                'admin.helpdesk',
                status=status_filter,
                ticket_type=ticket_type_filter,
                priority=priority_filter,
                sort=sort_filter,
            )
        )

    ticket_query = (
        SupportTicket.query
        .join(Student, Student.student_id == SupportTicket.student_id)
        .outerjoin(Course, Course.course_code == SupportTicket.course_code)
        .outerjoin(Admin, Admin.admin_id == SupportTicket.resolved_by_admin_id)
    )

    if status_filter != 'All':
        ticket_query = ticket_query.filter(SupportTicket.status == status_filter)
    if ticket_type_filter != 'All':
        ticket_query = ticket_query.filter(SupportTicket.ticket_type == ticket_type_filter)
    if priority_filter != 'All':
        ticket_query = ticket_query.filter(SupportTicket.priority == priority_filter)

    if sort_filter == 'oldest':
        ticket_query = ticket_query.order_by(SupportTicket.date_submitted.asc(), SupportTicket.ticket_id.asc())
    elif sort_filter == 'priority':
        priority_order = case(
            (SupportTicket.priority == 'High', 0),
            (SupportTicket.priority == 'Medium', 1),
            else_=2,
        )
        ticket_query = ticket_query.order_by(priority_order.asc(), SupportTicket.date_submitted.desc(), SupportTicket.ticket_id.desc())
    else:
        ticket_query = ticket_query.order_by(SupportTicket.date_submitted.desc(), SupportTicket.ticket_id.desc())

    tickets = ticket_query.all()

    counts_q = SupportTicket.query
    status_counts = {
        'All': counts_q.count(),
        'Open': counts_q.filter(SupportTicket.status == 'Open').count(),
        'Pending': counts_q.filter(SupportTicket.status == 'Pending').count(),
        'Resolved': counts_q.filter(SupportTicket.status == 'Resolved').count(),
    }

    return render_template(
        'admin/helpdesk.html',
        admin=admin,
        tickets=tickets,
        status_filter=status_filter,
        ticket_type_filter=ticket_type_filter,
        priority_filter=priority_filter,
        sort_filter=sort_filter,
        status_counts=status_counts,
    )


@admin_bp.route('/announcements', methods=['GET', 'POST'])
@admin_login_required
def announcements():
    """Create and review admin announcements for portal audiences."""
    admin = get_current_admin()
    if not admin:
        session.clear()
        flash('Admin record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        message = (request.form.get('message') or '').strip()
        target_audience = _normalize_filter(
            request.form.get('target_audience'),
            {'All', 'Students', 'Lecturers'},
            'All',
        )

        if not title or not message:
            flash('Title and message are required.', 'danger')
            return redirect(url_for('admin.announcements'))

        db.session.add(
            Announcement(
                admin_id=admin.admin_id,
                title=title,
                message=message,
                target_audience=target_audience,
            )
        )
        db.session.commit()
        flash('Announcement published successfully.', 'success')
        return redirect(url_for('admin.announcements'))

    announcements_rows = (
        Announcement.query
        .order_by(Announcement.date_posted.desc(), Announcement.announcement_id.desc())
        .all()
    )

    return render_template(
        'admin/announcements.html',
        admin=admin,
        announcements_rows=announcements_rows,
    )


@admin_bp.route('/logout')
@admin_login_required
def logout():
    """Clear admin session and return to login."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('public.login'))
