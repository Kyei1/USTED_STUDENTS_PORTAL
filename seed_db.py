"""Comprehensive seed script for USTED Students Portal database.

This script populates the database with realistic institutional data including:
- Departments (IT Education, Mathematics Education)
- Core course catalog (14 courses across levels 100, 200, 300)
- Student baseline data (Jane Doe, Level 300)
- Active enrollments and draft grades for testing
"""

import random
from decimal import Decimal
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


def seed_initial_data(reset_schema=True):
	"""Populate initial comprehensive test data for all USTED modules.

	When reset_schema is True, tables are dropped and recreated before seeding.
	"""
	with app.app_context():
		print("\n" + "="*70)
		print("USTED STUDENTS PORTAL - DATABASE SEED")
		print("="*70)
		
		if reset_schema:
			print("\n[0/4] Resetting schema (drop_all + create_all)...")
			db.drop_all()
			db.create_all()
			print("  ✓ Schema reset complete")
		
		# ===== STEP 1: Create Departments =====
		print("\n[1/4] Creating Departments...")
		
		it_dept = Department.query.filter_by(
			department_name="Information Technology Education"
		).first()
		if not it_dept:
			it_dept = Department(
				department_name="Information Technology Education",
				faculty_name="IT & Education",
			)
			db.session.add(it_dept)
			db.session.flush()
			print("  ✓ Created: Information Technology Education")
		else:
			print("  ✓ Exists: Information Technology Education")
		
		math_dept = Department.query.filter_by(
			department_name="Mathematics Education"
		).first()
		if not math_dept:
			math_dept = Department(
				department_name="Mathematics Education",
				faculty_name="Mathematics & Sciences",
			)
			db.session.add(math_dept)
			db.session.flush()
			print("  ✓ Created: Mathematics Education")
		else:
			print("  ✓ Exists: Mathematics Education")
		
		db.session.commit()
		
		# ===== STEP 2: Create Core Course Catalog (Bound to IT Department) =====
		print("\n[2/4] Creating Course Catalog (14 courses for IT Department)...")
		
		# Define all 15 courses: structure (code, name, type, level_hint)
		courses_data = [
			# General/Education Core (3 courses)
			("EDC111", "Philosophy of Education", "General"),
			("EDC241", "Psychology of Human Development", "General"),
			("EDC362", "Educational Measurement, Evaluation, and Statistics", "General"),
			
			# Level 100 IT (3 courses)
			("ICT111", "Fundamentals of IT", "Core"),
			("CIT112", "Principles of Programming", "Core"),
			("CIT113", "Algebra", "Core"),
			
			# Level 200 IT (3 courses)
			("ITC231", "Database Concepts and Design", "Core"),
			("ICT232", "Web Technology and Design", "Core"),
			("ITC234", "Methods of Teaching IT", "Core"),
			
			# Level 300 IT (5 courses)
			("ITC357", "Software Engineering", "Core"),
			("ITC356", "Operating Systems", "Core"),
			("ITC354", "Data Communications and Networks", "Core"),
			("ITC352", "Research Methods in IT", "Core"),
			("ITC358", "Visual Programming using C#", "Core"),
		]
		
		created_courses = {}
		for course_code, course_name, course_type in courses_data:
			course = Course.query.filter_by(course_code=course_code).first()
			if not course:
				course = Course(
					course_code=course_code,
					department_id=it_dept.department_id,
					course_name=course_name,
					credit_hours=3,
					course_type=course_type,
				)
				db.session.add(course)
				created_courses[course_code] = course
				print(f"  ✓ Created: {course_code} - {course_name}")
			else:
				created_courses[course_code] = course
				print(f"  ✓ Exists:  {course_code} - {course_name}")
		
		db.session.commit()
		
		# ===== STEP 3: Create Baseline Student (Jane Doe, Level 300) =====
		print("\n[3/4] Creating Student Baseline...")
		
		student = Student.query.filter_by(student_id="USD260012").first()
		if not student:
			student = Student(
				student_id="USD260012",
				department_id=it_dept.department_id,
				reference_number="REF12345",
				first_name="Jane",
				middle_name="Mary",
				last_name="Doe",
				email_address="jane@usted.edu.gh",
				password_hash=generate_password_hash("password123"),
				level="300",
			)
			db.session.add(student)
			db.session.flush()
			print(f"  ✓ Created: {student.first_name} {student.last_name}")
			print(f"    - Student ID: {student.student_id}")
			print(f"    - Reference: {student.reference_number}")
			print(f"    - Level: {student.level}")
			print(f"    - Email: {student.email_address}")
			print(f"    - Past Credits: 84 (historical baseline)")
			print(f"    - Past Grade Points: 289.8 (historical baseline)")
		else:
			print(f"  ✓ Exists: {student.first_name} {student.last_name} ({student.student_id})")
		
		db.session.commit()
		
		# ===== STEP 4: Create Active Enrollments (7 courses, First Semester) =====
		print("\n[4/4] Creating Active Enrollments & Draft Grades...")
		
		# 7 specific courses for active enrollment (First Semester, 2025/2026)
		active_courses = [
			"ITC356",  # Operating Systems
			"ITC357",  # Software Engineering
			"ITC352",  # Research Methods in IT
			"ITC234",  # Methods of Teaching IT
			"ITC358",  # Visual Programming using C#
			"ITC354",  # Data Communications and Networks
			"EDC362",  # EDC equivalent for Guidance and Counselling
		]
		
		academic_year = "2025/2026"
		semester = "First"
		
		for course_code in active_courses:
			# Check if enrollment already exists
			existing_enrollment = Enrollment.query.filter_by(
				student_id=student.student_id,
				course_code=course_code,
				academic_year=academic_year,
				semester=semester,
			).first()
			
			if not existing_enrollment:
				# Create enrollment
				enrollment = Enrollment(
					student_id=student.student_id,
					course_code=course_code,
					academic_year=academic_year,
					semester=semester,
				)
				db.session.add(enrollment)
				db.session.flush()
				
				# Generate realistic draft grade
				ca_score = Decimal(str(round(random.uniform(25.00, 38.00), 2)))
				exam_score = Decimal("0.00")  # Exams not yet conducted
				total_score = ca_score + exam_score
				grade_letter = _calculate_grade_letter(float(total_score))
				
				grade = Grade(
					enrollment_id=enrollment.enrollment_id,
					ca_score=ca_score,
					exam_score=exam_score,
					total_score=total_score,
					grade_letter=grade_letter,
					approval_status="Draft",
				)
				db.session.add(grade)
				
				print(f"  ✓ Enrolled: {course_code}")
				print(f"    - Academic Year: {academic_year} ({semester})")
				print(f"    - CA Score: {ca_score} | Exam: {exam_score} | Total: {total_score}")
				print(f"    - Grade Letter: {grade_letter} | Status: Draft")
			else:
				print(f"  ✓ Exists:  {course_code} (already enrolled)")
		
		db.session.commit()
		
		# ===== Create Financial Status Record =====
		print("\n[Bonus] Creating Financial Status...")
		
		financial = FinancialStatus.query.filter_by(
			student_id=student.student_id,
			academic_year=academic_year,
		).first()
		
		if not financial:
			financial = FinancialStatus(
				student_id=student.student_id,
				academic_year=academic_year,
				amount_billed=Decimal("2500.00"),
				amount_paid=Decimal("1200.00"),
				cleared_for_registration=False,
			)
			db.session.add(financial)
			db.session.flush()
			print(f"  ✓ Created: Financial Status for {academic_year}")
			print(f"    - Amount Billed: GHS {financial.amount_billed}")
			print(f"    - Amount Paid: GHS {financial.amount_paid}")
			print(f"    - Outstanding: GHS {financial.amount_billed - financial.amount_paid}")
			print(f"    - Cleared for Registration: {financial.cleared_for_registration}")
		else:
			print(f"  ✓ Exists:  Financial Status for {academic_year}")

		print("\n[Bonus] Creating Support Tickets...")
		ticket_payload = [
			("Academic", "High", "ITC357", "Need urgent review of coursework rubric alignment.", "Open"),
			("Technical", "Medium", None, "Portal logs me out unexpectedly on slow network.", "Pending"),
			("Academic", "Low", "ITC352", "Clarify project submission format for research methods.", "Resolved"),
		]

		for ticket_type, priority, course_code, description, status in ticket_payload:
			existing_ticket = SupportTicket.query.filter_by(
				student_id=student.student_id,
				ticket_type=ticket_type,
				priority=priority,
				description=description,
			).first()

			if not existing_ticket:
				ticket = SupportTicket(
					student_id=student.student_id,
					course_code=course_code,
					ticket_type=ticket_type,
					priority=priority,
					description=description,
					status=status,
				)
				db.session.add(ticket)
				print(f"  ✓ Created: {ticket_type} ticket ({priority}, {status})")
			else:
				print(f"  ✓ Exists:  {ticket_type} ticket ({priority}, {status})")
		
		db.session.commit()
		
		print("\n" + "="*70)
		print("✅ DATABASE SEED COMPLETED SUCCESSFULLY")
		print("="*70)
		print("\nDatabase Summary:")
		print(f"  • Departments: 2 ({it_dept.department_name}, {math_dept.department_name})")
		print(f"  • Courses: 14 (all bound to IT Department, 3-credit hours each)")
		print(f"  • Students: 1 (Jane Doe, Level 300, USD260012)")
		print(f"  • Active Enrollments: 7 (First Semester, 2025/2026)")
		print(f"  • Draft Grades: 7 (CA scores only, exams pending)")
		print(f"  • Financial Records: 1 (Outstanding payment pending)")
		print(f"  • Support Tickets: 3 (Open, Pending, Resolved with priority levels)")
		print("\n📝 Next Steps:")
		print("  1. Run 'python app.py' to start the portal")
		print("  2. Login with student_id: USD260012, password: password123")
		print("  3. Navigate to:")
		print("     - Dashboard: View enrollments & GPA")
		print("     - My Courses: See registered courses")
		print("     - Results: View draft grades (CA only)")
		print("     - Financials: Check payment status")
		print("     - GPA Simulator: Project final scores")
		print("="*70 + "\n")


def _calculate_grade_letter(total_score):
	"""Convert total score to letter grade.
	
	Grading Scale (typical university standard):
	 A: 70-100
	 B: 60-69
	 C: 50-59
	 D: 40-49
	 F: 0-39
	"""
	if total_score >= 70:
		return "A"
	elif total_score >= 60:
		return "B"
	elif total_score >= 50:
		return "C"
	elif total_score >= 40:
		return "D"
	else:
		return "F"


if __name__ == "__main__":
	seed_initial_data()
