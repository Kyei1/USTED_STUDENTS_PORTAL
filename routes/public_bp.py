"""Public routes blueprint for the USTED Students Portal."""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from models import Student

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
    """Student login page with ORM-based authentication."""
    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        password = request.form.get('password', '')

        student = Student.query.filter_by(student_id=student_id).first()

        if student and check_password_hash(student.password_hash, password):
            session['student_id'] = student.student_id
            session['first_name'] = student.first_name
            flash(f'Login successful! Welcome, {student.first_name}.', 'success')
            return redirect(url_for('student.dashboard'))
        flash('Invalid student ID or password. Please try again.', 'danger')
        return render_template('public/login.html')

    return render_template('public/login.html')
