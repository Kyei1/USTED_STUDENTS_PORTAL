"""Seed script for initial test data in the USTED Students Portal database."""

from werkzeug.security import generate_password_hash

from app import app, db
from models import (
	Course,
	Department,
	Enrollment,
	FinancialStatus,
	Grade,
	Student,
	SupportTicket,
)


def seed_initial_data():
	"""Populate initial Phase 1 data for dashboard, results, GPA, financials, and helpdesk."""
	with app.app_context():
		print("Starting database seed...")

		department = Department.query.filter_by(
			department_name="Information Technology Education"
		).first()

		if not department:
			department = Department(
				department_name="Information Technology Education",
				faculty_name="IT & Education",
			)
			db.session.add(department)
			db.session.flush()
			print("Added department: Information Technology Education")
		else:
			print("Department already exists: Information Technology Education")

		student = Student.query.filter_by(student_id="USD260012").first()
		if not student:
			student = Student(
				student_id="USD260012",
				department_id=department.department_id,
				reference_number="REF12345",
				first_name="Jane",
				middle_name=None,
				last_name="Doe",
				email_address="jane.doe@usted.edu",
				password_hash=generate_password_hash("password123"),
				level="300",
			)
			db.session.add(student)
			print("Added student: Jane Doe (USD260012)")
		else:
			print("Student already exists: USD260012")

		courses_to_create = [
			("ITE301", "Software Engineering", 3),
			("ITE302", "Database Administration", 3),
			("ITE303", "IT Project Management", 3),
		]

		for course_code, course_name, credit_hours in courses_to_create:
			existing_course = Course.query.filter_by(course_code=course_code).first()
			if not existing_course:
				course = Course(
					course_code=course_code,
					department_id=department.department_id,
					course_name=course_name,
					credit_hours=credit_hours,
					course_type="Core",
				)
				db.session.add(course)
				print(f"Added course: {course_code} - {course_name}")
			else:
				print(f"Course already exists: {course_code}")

		db.session.flush()

		enrollment_payload = [
			("ITE301", "2025/2026", "First"),
			("ITE302", "2025/2026", "First"),
			("ITE303", "2025/2026", "First"),
		]

		for course_code, academic_year, semester in enrollment_payload:
			existing_enrollment = Enrollment.query.filter_by(
				student_id=student.student_id,
				course_code=course_code,
				academic_year=academic_year,
				semester=semester,
			).first()

			if not existing_enrollment:
				enrollment = Enrollment(
					student_id=student.student_id,
					course_code=course_code,
					academic_year=academic_year,
					semester=semester,
				)
				db.session.add(enrollment)
				print(f"Added enrollment: {course_code} ({academic_year} {semester})")
			else:
				print(f"Enrollment already exists: {course_code} ({academic_year} {semester})")

		db.session.flush()

		grade_payload = {
			"ITE301": {"ca": 35.0, "exam": 52.0, "total": 87.0, "letter": "A", "status": "Published"},
			"ITE302": {"ca": 30.0, "exam": 44.0, "total": 74.0, "letter": "B+", "status": "Published"},
			"ITE303": {"ca": 28.0, "exam": 38.0, "total": 66.0, "letter": "B", "status": "Pending_HOD"},
		}

		enrollments = Enrollment.query.filter_by(
			student_id=student.student_id,
			academic_year="2025/2026",
			semester="First",
		).all()

		for enrollment in enrollments:
			grade_data = grade_payload.get(enrollment.course_code)
			if not grade_data:
				continue

			existing_grade = Grade.query.filter_by(enrollment_id=enrollment.enrollment_id).first()
			if not existing_grade:
				grade = Grade(
					enrollment_id=enrollment.enrollment_id,
					ca_score=grade_data["ca"],
					exam_score=grade_data["exam"],
					total_score=grade_data["total"],
					grade_letter=grade_data["letter"],
					approval_status=grade_data["status"],
				)
				db.session.add(grade)
				print(f"Added grade for enrollment ID {enrollment.enrollment_id}")
			else:
				print(f"Grade already exists for enrollment ID {enrollment.enrollment_id}")

		financial_payload = [
			("2024/2025", 3600.00, 3600.00, True),
			("2025/2026", 4200.00, 3100.00, False),
		]

		for academic_year, amount_billed, amount_paid, cleared in financial_payload:
			existing_financial = FinancialStatus.query.filter_by(
				student_id=student.student_id,
				academic_year=academic_year,
			).first()

			if not existing_financial:
				financial = FinancialStatus(
					student_id=student.student_id,
					academic_year=academic_year,
					amount_billed=amount_billed,
					amount_paid=amount_paid,
					cleared_for_registration=cleared,
				)
				db.session.add(financial)
				print(f"Added financial record: {academic_year}")
			else:
				print(f"Financial record already exists: {academic_year}")

		ticket_payload = [
			("Academic", "ITE303", "Please review the status of my ITE303 continuous assessment marks.", "Pending"),
			("Technical", None, "Unable to access my financial statement page on mobile browser.", "Open"),
		]

		for ticket_type, course_code, description, status in ticket_payload:
			existing_ticket = SupportTicket.query.filter_by(
				student_id=student.student_id,
				ticket_type=ticket_type,
				description=description,
			).first()

			if not existing_ticket:
				ticket = SupportTicket(
					student_id=student.student_id,
					course_code=course_code,
					ticket_type=ticket_type,
					description=description,
					status=status,
				)
				db.session.add(ticket)
				print(f"Added support ticket: {ticket_type}")
			else:
				print(f"Support ticket already exists: {ticket_type}")

		db.session.commit()
		print("Database seed completed successfully.")


if __name__ == "__main__":
	seed_initial_data()
