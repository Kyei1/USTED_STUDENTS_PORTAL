"""Database models for the USTED Students Portal.

This module defines the Flask-SQLAlchemy models that implement the
provided ER schema, including foreign keys, enums, and relationships.
"""

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class Department(db.Model):
	__tablename__ = "department"

	department_id = db.Column(db.Integer, primary_key=True)
	department_name = db.Column(db.String(150), nullable=False)
	faculty_name = db.Column(db.String(150), nullable=False)

	students = db.relationship("Student", back_populates="department", lazy=True)
	lecturers = db.relationship("Lecturer", back_populates="department", lazy=True)
	courses = db.relationship("Course", back_populates="department", lazy=True)
	resources = db.relationship("Resource", back_populates="department", lazy=True)


class Student(db.Model):
	__tablename__ = "student"

	student_id = db.Column(db.String(10), primary_key=True)
	department_id = db.Column(db.Integer, db.ForeignKey("department.department_id"), nullable=False)
	reference_number = db.Column(db.String(15), unique=True, nullable=False)
	first_name = db.Column(db.String(150), nullable=False)
	middle_name = db.Column(db.String(150), nullable=True)
	last_name = db.Column(db.String(150), nullable=False)
	email_address = db.Column("Email_address", db.String(150), nullable=False, unique=True)
	password_hash = db.Column("passwordHash", db.String(255), nullable=False)
	level = db.Column(db.Enum("100", "200", "300", "400", name="student_level"), nullable=False)

	department = db.relationship("Department", back_populates="students")
	enrollments = db.relationship("Enrollment", back_populates="student", lazy=True)
	financial_status_records = db.relationship("FinancialStatus", back_populates="student", lazy=True)
	support_tickets = db.relationship("SupportTicket", back_populates="student", lazy=True)


class Lecturer(db.Model):
	__tablename__ = "lecturer"

	staff_id = db.Column(db.String(15), primary_key=True)
	department_id = db.Column(db.Integer, db.ForeignKey("department.department_id"), nullable=False)
	title = db.Column("Title", db.String(50), nullable=False)
	first_name = db.Column("First_Name", db.String(150), nullable=False)
	middle_name = db.Column("Middle_name", db.String(150), nullable=True)
	last_name = db.Column("Last_Name", db.String(150), nullable=False)
	email_address = db.Column("Email_address", db.String(150), nullable=False, unique=True)
	password_hash = db.Column("Password_Hash", db.String(255), nullable=False)
	role = db.Column(db.Enum("Lecturer", "HOD", name="lecturer_role"), nullable=False, default="Lecturer")

	department = db.relationship("Department", back_populates="lecturers")
	course_allocations = db.relationship("CourseLecturer", back_populates="lecturer", lazy=True)


class Admin(db.Model):
	__tablename__ = "admin"

	admin_id = db.Column("adminID", db.Integer, primary_key=True)
	first_name = db.Column(db.String(150), nullable=False)
	middle_name = db.Column(db.String(150), nullable=True)
	last_name = db.Column(db.String(150), nullable=False)
	email_address = db.Column("Email_address", db.String(150), nullable=False, unique=True)
	password_hash = db.Column("Password_Hash", db.String(255), nullable=False)
	role = db.Column(db.Enum("SuperAdmin", "Registrar", "IT_Support", name="admin_role"), nullable=False)

	announcements = db.relationship("Announcement", back_populates="admin", lazy=True)
	resolved_tickets = db.relationship("SupportTicket", back_populates="resolved_by_admin", lazy=True)


class Course(db.Model):
	__tablename__ = "course"

	course_code = db.Column(db.String(10), primary_key=True)
	department_id = db.Column("Department_ID", db.Integer, db.ForeignKey("department.department_id"), nullable=False)
	course_name = db.Column(db.String(100), nullable=False)
	credit_hours = db.Column(db.Integer, nullable=False)
	course_type = db.Column("Course_Type", db.Enum("Core", "Elective", "General", name="course_type"), nullable=False)

	department = db.relationship("Department", back_populates="courses")
	lecturer_allocations = db.relationship("CourseLecturer", back_populates="course", lazy=True)
	enrollments = db.relationship("Enrollment", back_populates="course", lazy=True)
	resources = db.relationship("Resource", back_populates="course", lazy=True)
	support_tickets = db.relationship("SupportTicket", back_populates="course", lazy=True)


class CourseLecturer(db.Model):
	__tablename__ = "course_lecturer"

	allocation_id = db.Column(db.Integer, primary_key=True)
	course_code = db.Column(db.String(10), db.ForeignKey("course.course_code"), nullable=False)
	staff_id = db.Column(db.String(15), db.ForeignKey("lecturer.staff_id"), nullable=False)
	class_group = db.Column("Class_Group", db.String(20), nullable=False)
	academic_year = db.Column("Academic_Year", db.String(9), nullable=False)

	course = db.relationship("Course", back_populates="lecturer_allocations")
	lecturer = db.relationship("Lecturer", back_populates="course_allocations")


class Enrollment(db.Model):
	__tablename__ = "enrollment"

	enrollment_id = db.Column("Enrollment_ID", db.Integer, primary_key=True)
	student_id = db.Column(db.String(10), db.ForeignKey("student.student_id"), nullable=False)
	course_code = db.Column("Course_Code", db.String(10), db.ForeignKey("course.course_code"), nullable=False)
	academic_year = db.Column("Academic_Year", db.String(9), nullable=False)
	semester = db.Column(db.Enum("First", "Second", name="semester_type"), nullable=False)

	student = db.relationship("Student", back_populates="enrollments")
	course = db.relationship("Course", back_populates="enrollments")
	grade = db.relationship("Grade", back_populates="enrollment", uselist=False, lazy=True)


class Grade(db.Model):
	__tablename__ = "grade"

	grade_id = db.Column(db.Integer, primary_key=True)
	enrollment_id = db.Column(db.Integer, db.ForeignKey("enrollment.Enrollment_ID"), nullable=False, unique=True)
	ca_score = db.Column("CA_score", db.Numeric(5, 2), nullable=True)
	exam_score = db.Column("Exam_Score", db.Numeric(5, 2), nullable=True)
	total_score = db.Column("Total_Score", db.Numeric(5, 2), nullable=True)
	grade_letter = db.Column("Grade_Letter", db.String(2), nullable=True)
	approval_status = db.Column(
		"Approval_Status",
		db.Enum("Draft", "Pending_HOD", "Pending_Board", "Published", name="approval_status"),
		nullable=False,
		default="Draft",
	)

	enrollment = db.relationship("Enrollment", back_populates="grade")


class FinancialStatus(db.Model):
	__tablename__ = "financial_status"

	record_id = db.Column(db.Integer, primary_key=True)
	student_id = db.Column(db.String(10), db.ForeignKey("student.student_id"), nullable=False)
	academic_year = db.Column(db.String(9), nullable=False)
	amount_billed = db.Column(db.Numeric(10, 2), nullable=False)
	amount_paid = db.Column(db.Numeric(10, 2), nullable=False)
	cleared_for_registration = db.Column(db.Boolean, nullable=False, default=False)
	__table_args__ = (db.UniqueConstraint('student_id', 'academic_year', name='unique_student_per_year'),)

	student = db.relationship("Student", back_populates="financial_status_records")


class Resource(db.Model):
	__tablename__ = "resource"

	resource_id = db.Column(db.Integer, primary_key=True)
	course_code = db.Column(db.String(10), db.ForeignKey("course.course_code"), nullable=True)
	department_id = db.Column(db.Integer, db.ForeignKey("department.department_id"), nullable=False)
	file_name = db.Column("file_Name", db.String(255), nullable=False)
	resource_type = db.Column("Type", db.Enum("Department", "Course", name="resource_type"), nullable=False)
	file_path = db.Column("file_Path", db.String(255), nullable=False)
	upload_date = db.Column(db.TIMESTAMP, nullable=False, server_default=db.func.current_timestamp())

	course = db.relationship("Course", back_populates="resources")
	department = db.relationship("Department", back_populates="resources")


class Announcement(db.Model):
	__tablename__ = "announcement"

	announcement_id = db.Column(db.Integer, primary_key=True)
	admin_id = db.Column(db.Integer, db.ForeignKey("admin.adminID"), nullable=False)
	title = db.Column(db.String(150), nullable=False)
	message = db.Column(db.Text, nullable=False)
	target_audience = db.Column(
		"Target_Audience",
		db.Enum("All", "Students", "Lecturers", name="target_audience"),
		nullable=False,
		default="All",
	)
	date_posted = db.Column("Date_Posted", db.TIMESTAMP, nullable=False, server_default=db.func.current_timestamp())

	admin = db.relationship("Admin", back_populates="announcements")
	read_receipts = db.relationship("StudentAnnouncementRead", back_populates="announcement", lazy=True)


class StudentAnnouncementRead(db.Model):
	__tablename__ = "student_announcement_read"

	id = db.Column(db.Integer, primary_key=True)
	student_id = db.Column(db.String(10), db.ForeignKey("student.student_id"), nullable=False)
	announcement_id = db.Column(db.Integer, db.ForeignKey("announcement.announcement_id"), nullable=False)
	read_at = db.Column(db.TIMESTAMP, nullable=False, server_default=db.func.current_timestamp())
	__table_args__ = (
		db.UniqueConstraint('student_id', 'announcement_id', name='uq_student_announcement_read'),
	)

	student = db.relationship("Student", lazy=True)
	announcement = db.relationship("Announcement", back_populates="read_receipts")


class SupportTicket(db.Model):
	__tablename__ = "support_ticket"

	ticket_id = db.Column(db.Integer, primary_key=True)
	student_id = db.Column(db.String(10), db.ForeignKey("student.student_id"), nullable=False)
	course_code = db.Column(db.String(10), db.ForeignKey("course.course_code"), nullable=True)
	resolved_by_admin_id = db.Column("Resolved_By_Admin", db.Integer, db.ForeignKey("admin.adminID"), nullable=True)
	ticket_type = db.Column("Type", db.Enum("Academic", "Technical", name="ticket_type"), nullable=False)
	priority = db.Column(
		"Priority",
		db.Enum("Low", "Medium", "High", name="ticket_priority"),
		nullable=False,
		default="Medium",
	)
	description = db.Column("Description", db.Text, nullable=False)
	status = db.Column(
		"Status",
		db.Enum("Open", "Pending", "Resolved", name="ticket_status"),
		nullable=False,
		default="Open",
	)
	date_submitted = db.Column("Date_Submitted", db.TIMESTAMP, nullable=False, server_default=db.func.current_timestamp())

	student = db.relationship("Student", back_populates="support_tickets")
	course = db.relationship("Course", back_populates="support_tickets")
	resolved_by_admin = db.relationship("Admin", back_populates="resolved_tickets")
