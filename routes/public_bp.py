"""Public routes blueprint for the USTED Students Portal."""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from sqlalchemy import or_
from werkzeug.security import check_password_hash
from models import Student, Lecturer, Admin

public_bp = Blueprint(
    'public',
    __name__,
    url_prefix=None,  # Public routes at root level
)


@public_bp.route('/')
def index():
    """Public landing page."""
    return render_template('public/index.html')


@public_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Unified login page for student, lecturer, and admin roles."""
    if request.method == 'POST':
        # Backward compatibility: support legacy student_id field from existing tests/forms.
        identifier = request.form.get('identifier', '').strip() or request.form.get('student_id', '').strip()
        password = request.form.get('password', '')
        account_type = (request.form.get('account_type') or 'student').strip().lower()

        if account_type not in {'student', 'lecturer', 'admin'}:
            account_type = 'student'

        session.clear()

        if account_type == 'student':
            student = Student.query.filter(
                or_(
                    Student.student_id == identifier,
                    Student.email_address == identifier.lower(),
                )
            ).first()

            if student and check_password_hash(student.password_hash, password):
                session['user_role'] = 'student'
                session['student_id'] = student.student_id
                session['first_name'] = student.first_name
                flash(f'Login successful! Welcome, {student.first_name}.', 'success')
                return redirect(url_for('student.dashboard'))

            flash('Invalid student credentials. Please try again.', 'danger')
            return render_template('public/login.html')

        if account_type == 'lecturer':
            lecturer = Lecturer.query.filter(
                or_(
                    Lecturer.staff_id == identifier,
                    Lecturer.email_address == identifier.lower(),
                )
            ).first()

            if lecturer and check_password_hash(lecturer.password_hash, password):
                session['user_role'] = 'lecturer'
                session['lecturer_id'] = lecturer.staff_id
                session['first_name'] = lecturer.first_name
                flash(f'Login successful! Welcome, {lecturer.first_name}.', 'success')
                return redirect(url_for('lecturer.dashboard'))

            flash('Invalid lecturer credentials. Please try again.', 'danger')
            return render_template('public/login.html')

        # Admin login via email for consistency.
        admin = Admin.query.filter(Admin.email_address == identifier.lower()).first()
        if admin and check_password_hash(admin.password_hash, password):
            session['user_role'] = 'admin'
            session['admin_id'] = admin.admin_id
            session['first_name'] = admin.first_name
            flash(f'Login successful! Welcome, {admin.first_name}.', 'success')
            return redirect(url_for('admin.dashboard'))

        flash('Invalid admin credentials. Please try again.', 'danger')
        return render_template('public/login.html')

    return render_template('public/login.html')


@public_bp.route('/forgot-password')
def forgot_password():
    """Public password recovery guidance page."""
    return render_template('public/forgot_password.html')


@public_bp.route('/it-helpdesk')
def it_helpdesk():
    """Public IT helpdesk contact page for portal access issues."""
    return render_template('public/it_helpdesk.html')
