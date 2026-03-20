import os

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from models import db, Student, Enrollment, Grade, FinancialStatus, SupportTicket, Course

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-secret-key-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///usted_portal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
with app.app_context():
    db.create_all()


@app.route('/')
def index():
    return render_template('index.html')


def get_current_student():
    student_id = session.get('student_id')
    if not student_id:
        return None
    return Student.query.filter_by(student_id=student_id).first()


def score_to_point(score):
    if score >= 80:
        return 4.0
    if score >= 75:
        return 3.5
    if score >= 70:
        return 3.0
    if score >= 65:
        return 2.5
    if score >= 60:
        return 2.0
    if score >= 55:
        return 1.5
    if score >= 50:
        return 1.0
    return 0.0


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        password = request.form.get('password', '')

        student = Student.query.filter_by(student_id=student_id).first()

        if student and check_password_hash(student.password_hash, password):
            session['student_id'] = student.student_id
            session['first_name'] = student.first_name
            flash(f'Login successful! Welcome, {student.first_name}.', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid student ID or password. Please try again.', 'danger')
        return render_template('login.html')

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    student = get_current_student()
    if not student:
        flash('Please log in to access the dashboard.', 'warning')
        return redirect(url_for('login'))

    enrollments = (
        Enrollment.query.filter_by(student_id=student.student_id)
        .order_by(Enrollment.academic_year.desc())
        .limit(6)
        .all()
    )
    latest_financial = (
        FinancialStatus.query.filter_by(student_id=student.student_id)
        .order_by(FinancialStatus.academic_year.desc())
        .first()
    )

    return render_template(
        'dashboard.html',
        student=student,
        enrollments=enrollments,
        latest_financial=latest_financial,
    )


@app.route('/results')
def results():
    student = get_current_student()
    if not student:
        flash('Please log in to view your results.', 'warning')
        return redirect(url_for('login'))

    records = (
        Enrollment.query.filter_by(student_id=student.student_id)
        .join(Course, Enrollment.course_code == Course.course_code)
        .outerjoin(Grade, Grade.enrollment_id == Enrollment.enrollment_id)
        .order_by(Enrollment.academic_year.desc(), Course.course_code.asc())
        .all()
    )

    return render_template('results.html', student=student, records=records)


@app.route('/gpa-simulator', methods=['GET', 'POST'])
def gpa_simulator():
    student = get_current_student()
    if not student:
        flash('Please log in to use the GPA simulator.', 'warning')
        return redirect(url_for('login'))

    enrollments = (
        Enrollment.query.filter_by(student_id=student.student_id)
        .join(Course, Enrollment.course_code == Course.course_code)
        .order_by(Enrollment.academic_year.desc(), Course.course_code.asc())
        .all()
    )

    simulation_rows = []
    total_credit_hours = 0
    total_weighted_points = 0.0

    for enrollment in enrollments:
        existing_score = float(enrollment.grade.total_score) if enrollment.grade else None
        score_value = existing_score

        if request.method == 'POST':
            posted_score = request.form.get(f'score_{enrollment.enrollment_id}', '').strip()
            if posted_score:
                try:
                    parsed = float(posted_score)
                    score_value = max(0.0, min(100.0, parsed))
                except ValueError:
                    score_value = existing_score

        if score_value is not None:
            points = score_to_point(score_value)
            weighted = points * enrollment.course.credit_hours
            total_credit_hours += enrollment.course.credit_hours
            total_weighted_points += weighted
        else:
            points = None

        simulation_rows.append(
            {
                'enrollment': enrollment,
                'score': score_value,
                'points': points,
            }
        )

    projected_gpa = (total_weighted_points / total_credit_hours) if total_credit_hours else None

    return render_template(
        'gpa_simulator.html',
        student=student,
        simulation_rows=simulation_rows,
        projected_gpa=projected_gpa,
        total_credit_hours=total_credit_hours,
    )


@app.route('/financials')
def financials():
    student = get_current_student()
    if not student:
        flash('Please log in to view your financial statement.', 'warning')
        return redirect(url_for('login'))

    records = (
        FinancialStatus.query.filter_by(student_id=student.student_id)
        .order_by(FinancialStatus.academic_year.desc())
        .all()
    )

    total_billed = sum(float(record.amount_billed) for record in records)
    total_paid = sum(float(record.amount_paid) for record in records)
    total_arrears = total_billed - total_paid

    return render_template(
        'financials.html',
        student=student,
        records=records,
        total_billed=total_billed,
        total_paid=total_paid,
        total_arrears=total_arrears,
    )


@app.route('/helpdesk', methods=['GET', 'POST'])
def helpdesk():
    student = get_current_student()
    if not student:
        flash('Please log in to access helpdesk.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        ticket_type = request.form.get('ticket_type', '').strip()
        description = request.form.get('description', '').strip()
        course_code = request.form.get('course_code', '').strip() or None

        if ticket_type not in {'Academic', 'Technical'} or not description:
            flash('Please provide a valid ticket type and description.', 'danger')
            return redirect(url_for('helpdesk'))

        ticket = SupportTicket(
            student_id=student.student_id,
            course_code=course_code,
            ticket_type=ticket_type,
            description=description,
        )
        db.session.add(ticket)
        db.session.commit()
        flash('Support ticket submitted successfully.', 'success')
        return redirect(url_for('helpdesk'))

    tickets = (
        SupportTicket.query.filter_by(student_id=student.student_id)
        .order_by(SupportTicket.date_submitted.desc())
        .all()
    )
    courses = (
        Course.query.join(Enrollment, Enrollment.course_code == Course.course_code)
        .filter(Enrollment.student_id == student.student_id)
        .order_by(Course.course_code.asc())
        .all()
    )

    return render_template('helpdesk.html', student=student, tickets=tickets, courses=courses)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
