"""Student dashboard and protected routes blueprint for the USTED Students Portal."""

from functools import wraps
from io import BytesIO
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file
from models import db, Student, Enrollment, Grade, FinancialStatus, SupportTicket, Course, Resource
from services import (
    get_current_student,
    score_to_point,
    score_to_letter,
    point_to_min_total_score,
    scaled_exam_score,
    difficulty_label,
    allocate_uneven_target_points,
    academic_period_rank,
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
    latest_financial = (
        FinancialStatus.query.filter_by(student_id=student.student_id)
        .order_by(FinancialStatus.academic_year.desc())
        .first()
    )

    return render_template(
        'student/dashboard.html',
        student=student,
        enrollments=enrollments,
        latest_financial=latest_financial,
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
        .order_by(Enrollment.academic_year.desc(), Course.course_code.asc())
        .all()
    )

    return render_template('student/results.html', student=student, records=records)


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
        .order_by(Enrollment.academic_year.desc(), Course.course_code.asc())
        .all()
    )

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
    line_y = page_height - (20 * mm)
    row_height = 7 * mm

    def draw_header(y_pos):
        pdf.setFillColor(colors.HexColor('#7a0016'))
        pdf.rect(0, page_height - (28 * mm), page_width, 28 * mm, stroke=0, fill=1)
        pdf.setFillColor(colors.white)
        pdf.setFont('Helvetica-Bold', 15)
        pdf.drawString(margin_left, page_height - (16 * mm), 'USTED Official Transcript')
        pdf.setFont('Helvetica', 10)
        pdf.drawString(margin_left, page_height - (22 * mm), f'Student: {student.first_name} {student.last_name} ({student.student_id})')
        pdf.drawRightString(page_width - margin_right, page_height - (22 * mm), datetime.now().strftime('Generated %Y-%m-%d %H:%M'))

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

    draw_header(line_y)
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
                line_y = page_height - (35 * mm)
                draw_header(line_y)
                line_y -= row_height
                pdf.setFont('Helvetica', 9)

            title = enrollment.course.course_name or ''
            if len(title) > 34:
                title = title[:31] + '...'

            total = f"{float(enrollment.grade.total_score):.1f}" if enrollment.grade else 'N/A'
            grade_letter = enrollment.grade.grade_letter if enrollment.grade else 'N/A'

            pdf.setFillColor(colors.black)
            pdf.drawString(margin_left, line_y, enrollment.academic_year)
            pdf.drawString(margin_left + (32 * mm), line_y, enrollment.semester[:3])
            pdf.drawString(margin_left + (46 * mm), line_y, enrollment.course.course_code)
            pdf.drawString(margin_left + (68 * mm), line_y, title)
            pdf.drawRightString(margin_left + (134 * mm), line_y, str(enrollment.course.credit_hours))
            pdf.drawRightString(margin_left + (151 * mm), line_y, total)
            pdf.drawRightString(margin_left + (170 * mm), line_y, grade_letter)
            line_y -= row_height

    pdf.setFont('Helvetica-Oblique', 8)
    pdf.setFillColor(colors.HexColor('#4a000d'))
    pdf.drawString(margin_left, 12 * mm, 'Generated by USTED Students Portal')

    pdf.save()
    buffer.seek(0)

    filename = f"USTED_Transcript_{student.student_id}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')


@student_bp.route('/resource-hub')
@login_required
def resource_hub():
    """List department and course resources available to the student."""
    student = get_current_student()
    if not student:
        session.clear()
        flash('Student record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    resources = (
        Resource.query.join(Course, Resource.course_code == Course.course_code)
        .filter(Resource.department_id == student.department_id)
        .order_by(Resource.upload_date.desc())
        .all()
    )

    return render_template('student/resource_hub.html', student=student, resources=resources)


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
        'student/gpa_simulator.html',
        student=student,
        active_enrollments=active_enrollments,
        active_period=active_period,
        past_cgpa=past_cgpa,
        total_past_credits=total_past_credits,
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
        description = request.form.get('description', '').strip()
        course_code = request.form.get('course_code', '').strip() or None

        if ticket_type not in {'Academic', 'Technical'} or not description:
            flash('Please provide a valid ticket type and description.', 'danger')
            return redirect(url_for('student.helpdesk'))
        if course_code and course_code not in enrolled_course_codes:
            flash('Selected course is not part of your current enrollments.', 'danger')
            return redirect(url_for('student.helpdesk'))

        ticket = SupportTicket(
            student_id=student.student_id,
            course_code=course_code,
            ticket_type=ticket_type,
            description=description,
        )
        db.session.add(ticket)
        db.session.commit()
        flash('Support ticket submitted successfully.', 'success')
        return redirect(url_for('student.helpdesk'))

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

    return render_template('student/helpdesk.html', student=student, tickets=tickets, courses=courses)


@student_bp.route('/logout')
@login_required
def logout():
    """Logout the current student."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('public.login'))
