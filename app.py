import os
from functools import wraps

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


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get('student_id'):
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return view_func(*args, **kwargs)

    return wrapped_view


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


def score_to_letter(score):
    if score >= 80:
        return 'A'
    if score >= 75:
        return 'B+'
    if score >= 70:
        return 'B'
    if score >= 65:
        return 'C+'
    if score >= 60:
        return 'C'
    if score >= 55:
        return 'D+'
    if score >= 50:
        return 'D'
    return 'E/F'


def point_to_min_total_score(grade_point):
    if grade_point >= 4.0:
        return 80
    if grade_point >= 3.5:
        return 75
    if grade_point >= 3.0:
        return 70
    if grade_point >= 2.5:
        return 65
    if grade_point >= 2.0:
        return 60
    if grade_point >= 1.5:
        return 55
    if grade_point >= 1.0:
        return 50
    return 0


def semester_rank(semester):
    return 2 if semester == 'Second' else 1


def academic_period_rank(enrollment):
    try:
        start_year = int(str(enrollment.academic_year).split('/')[0])
    except (ValueError, IndexError):
        start_year = 0
    return (start_year, semester_rank(enrollment.semester))


def scaled_exam_score(raw_exam_score):
    return (raw_exam_score / 100.0) * 60.0


def course_difficulty_weight(course):
    # Higher values indicate relatively harder courses.
    type_weight = {
        'Core': 1.25,
        'General': 1.0,
        'Elective': 0.9,
    }
    base = type_weight.get(course.course_type, 1.0)
    credit_adjustment = max(course.credit_hours - 2, 0) * 0.08
    return base + credit_adjustment


def difficulty_label(weight):
    if weight >= 1.3:
        return 'High'
    if weight >= 1.05:
        return 'Medium'
    return 'Low'


def allocate_uneven_target_points(active_enrollments, target_sgpa):
    total_credit_hours = sum(enrollment.course.credit_hours for enrollment in active_enrollments)
    if not total_credit_hours:
        return []

    rows = []
    for enrollment in active_enrollments:
        weight = course_difficulty_weight(enrollment.course)
        inverse_weight = 1.0 / weight if weight else 1.0
        rows.append(
            {
                'enrollment': enrollment,
                'credit_hours': enrollment.course.credit_hours,
                'difficulty_weight': weight,
                'inverse_weight': inverse_weight,
                'required_point': 0.0,
            }
        )

    weighted_inverse_avg = (
        sum(row['credit_hours'] * row['inverse_weight'] for row in rows) / total_credit_hours
    )

    for row in rows:
        scaled_target = target_sgpa * (row['inverse_weight'] / weighted_inverse_avg)
        row['required_point'] = min(4.0, max(0.0, scaled_target))

    required_total_points = target_sgpa * total_credit_hours
    current_total_points = sum(row['required_point'] * row['credit_hours'] for row in rows)
    delta_points = required_total_points - current_total_points

    if abs(delta_points) > 1e-9:
        # If points must be added, bias easier courses first; if reduced, bias harder courses first.
        rows.sort(
            key=lambda row: row['difficulty_weight'],
            reverse=delta_points < 0,
        )

        for row in rows:
            if abs(delta_points) <= 1e-9:
                break

            if delta_points > 0:
                capacity = 4.0 - row['required_point']
                if capacity <= 0:
                    continue
                available_points = capacity * row['credit_hours']
                consume = min(delta_points, available_points)
                row['required_point'] += consume / row['credit_hours']
                delta_points -= consume
            else:
                capacity = row['required_point']
                if capacity <= 0:
                    continue
                available_points = capacity * row['credit_hours']
                consume = min(abs(delta_points), available_points)
                row['required_point'] -= consume / row['credit_hours']
                delta_points += consume

    return rows


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
@login_required
def dashboard():
    student = get_current_student()
    if not student:
        session.clear()
        flash('Student record not found. Please log in again.', 'danger')
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
@login_required
def results():
    student = get_current_student()
    if not student:
        session.clear()
        flash('Student record not found. Please log in again.', 'danger')
        return redirect(url_for('login'))

    records = (
        Enrollment.query.filter_by(student_id=student.student_id)
        .join(Course, Enrollment.course_code == Course.course_code)
        .outerjoin(Grade, Grade.enrollment_id == Enrollment.enrollment_id)
        .order_by(Enrollment.academic_year.desc(), Course.course_code.asc())
        .all()
    )

    return render_template('results.html', student=student, records=records)


@app.route('/results/transcript.pdf')
@login_required
def results_transcript_pdf():
    student = get_current_student()
    if not student:
        session.clear()
        flash('Student record not found. Please log in again.', 'danger')
        return redirect(url_for('login'))

    flash('Transcript PDF export scaffold is active. Full PDF rendering will be connected next.', 'info')
    return redirect(url_for('results'))


@app.route('/gpa-simulator', methods=['GET', 'POST'])
@login_required
def gpa_simulator():
    student = get_current_student()
    if not student:
        session.clear()
        flash('Student record not found. Please log in again.', 'danger')
        return redirect(url_for('login'))

    enrollments = (
        Enrollment.query.filter_by(student_id=student.student_id)
        .join(Course, Enrollment.course_code == Course.course_code)
        .order_by(Enrollment.academic_year.desc(), Course.course_code.asc())
        .all()
    )

    if not enrollments:
        return render_template(
            'gpa_simulator.html',
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

    mode = request.form.get('mode', 'single') if request.method == 'POST' else 'single'
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
                    'required_rows': required_rows,
                }

    return render_template(
        'gpa_simulator.html',
        student=student,
        active_enrollments=active_enrollments,
        active_period=active_period,
        past_cgpa=past_cgpa,
        total_past_credits=total_past_credits,
        mode=mode,
        single_result=single_result,
        target_result=target_result,
    )


@app.route('/financials')
@login_required
def financials():
    student = get_current_student()
    if not student:
        session.clear()
        flash('Student record not found. Please log in again.', 'danger')
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
@login_required
def helpdesk():
    student = get_current_student()
    if not student:
        session.clear()
        flash('Student record not found. Please log in again.', 'danger')
        return redirect(url_for('login'))

    enrolled_course_codes = {
        enrollment.course_code
        for enrollment in Enrollment.query.filter_by(student_id=student.student_id).all()
    }

    if request.method == 'POST':
        ticket_type = request.form.get('ticket_type', '').strip()
        description = request.form.get('description', '').strip()
        course_code = request.form.get('course_code', '').strip() or None

        if ticket_type not in {'Academic', 'Technical'} or not description:
            flash('Please provide a valid ticket type and description.', 'danger')
            return redirect(url_for('helpdesk'))
        if course_code and course_code not in enrolled_course_codes:
            flash('Selected course is not part of your current enrollments.', 'danger')
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
        .group_by(Course.course_code)
        .order_by(Course.course_code.asc())
        .all()
    )

    return render_template('helpdesk.html', student=student, tickets=tickets, courses=courses)


@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
