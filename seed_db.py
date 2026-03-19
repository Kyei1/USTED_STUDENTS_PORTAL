"""Seed script for initial test data in the USTED Students Portal database."""

from werkzeug.security import generate_password_hash

from app import app, db
from models import Course, Department, Student


def seed_initial_data():
	"""Populate initial department, student, and courses."""
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

		db.session.commit()
		print("Database seed completed successfully.")


if __name__ == "__main__":
	seed_initial_data()
