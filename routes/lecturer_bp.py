"""Lecturer routes blueprint for the USTED Students Portal."""

from functools import wraps

from flask import Blueprint, render_template, session, redirect, url_for, flash
from sqlalchemy import func

from models import Lecturer, CourseLecturer, Course, Enrollment


lecturer_bp = Blueprint(
    'lecturer',
    __name__,
    url_prefix='/lecturer',
)


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

    roster_counts = {
        course_code: count
        for course_code, count in (
            Enrollment.query
            .with_entities(Enrollment.course_code, func.count(Enrollment.enrollment_id))
            .filter(Enrollment.course_code.in_([row.course_code for row in assigned_rows]))
            .group_by(Enrollment.course_code)
            .all()
        )
    } if assigned_rows else {}

    total_students = sum(roster_counts.values()) if roster_counts else 0

    return render_template(
        'lecturer/dashboard.html',
        lecturer=lecturer,
        assigned_rows=assigned_rows,
        roster_counts=roster_counts,
        total_courses=len(assigned_rows),
        total_students=total_students,
    )


@lecturer_bp.route('/logout')
@lecturer_login_required
def logout():
    """Clear lecturer session and return to login."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('public.login'))
