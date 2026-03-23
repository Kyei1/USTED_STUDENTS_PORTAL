"""Load Semester 5 courses with specific grades for consistent testing.

This script populates the database with Semester 5 enrollments and grades
matching the exact CA, Exam, and Total scores provided in specifications.
"""

import argparse
from app import app, db
from models import Course, Enrollment, Grade, Student

# Exact data mapping provided by user for Semester 5
SEMESTER5_DATA = {
    "2026/2027": {
        "First": [
            {
                "course_code": "ICT351",
                "course_name": "Software Engineering",
                "credits": 3,
                "ca_score": 35.0,
                "raw_exam": 80.0,
                "scaled_exam": 48.0,
                "total": 83.0,
                "grade": "A",
                "sgp": 12.0,
            },
            {
                "course_code": "ICT352",
                "course_name": "Operating Systems",
                "credits": 3,
                "ca_score": 36.0,
                "raw_exam": 80.0,
                "scaled_exam": 48.0,
                "total": 84.0,
                "grade": "A",
                "sgp": 12.0,
            },
            {
                "course_code": "ICT353",
                "course_name": "Data Communication and Networks",
                "credits": 3,
                "ca_score": 34.0,
                "raw_exam": 80.0,
                "scaled_exam": 48.0,
                "total": 82.0,
                "grade": "A",
                "sgp": 12.0,
            },
            {
                "course_code": "ICT354",
                "course_name": "Advanced Database Systems",
                "credits": 3,
                "ca_score": 38.0,
                "raw_exam": 80.0,
                "scaled_exam": 48.0,
                "total": 86.0,
                "grade": "A",
                "sgp": 12.0,
            },
            {
                "course_code": "ICT355",
                "course_name": "Human Computer Interaction",
                "credits": 3,
                "ca_score": 35.0,
                "raw_exam": 75.0,
                "scaled_exam": 45.0,
                "total": 80.0,
                "grade": "A",
                "sgp": 12.0,
            },
            {
                "course_code": "MAT349",
                "course_name": "Numerical Methods",
                "credits": 3,
                "ca_score": 33.0,
                "raw_exam": 70.0,
                "scaled_exam": 42.0,
                "total": 75.0,
                "grade": "B+",
                "sgp": 10.5,
            },
            {
                "course_code": "EDC351",
                "course_name": "Assessment in Education",
                "credits": 3,
                "ca_score": 30.0,
                "raw_exam": 70.0,
                "scaled_exam": 42.0,
                "total": 72.0,
                "grade": "B",
                "sgp": 9.0,
            },
        ]
    }
}


def load_semester5(student_id, upsert_existing=False):
    """Load Semester 5 courses with specific scores for a student."""
    with app.app_context():
        student = Student.query.filter_by(student_id=student_id).first()
        if not student:
            print(f"ERROR: Student {student_id} not found.")
            return False

        academic_year = "2026/2027"
        semester = "First"
        courses_data = SEMESTER5_DATA[academic_year][semester]

        for course_info in courses_data:
            course_code = course_info["course_code"]
            
            # Get or create course
            course = Course.query.filter_by(course_code=course_code).first()
            if not course:
                course = Course(
                    course_code=course_code,
                    course_name=course_info["course_name"],
                    credit_hours=course_info["credits"],
                    department_id=student.department_id,
                )
                db.session.add(course)
                db.session.flush()
                print(f"Created course: {course_code}")
            
            # Get or create enrollment
            enrollment = Enrollment.query.filter_by(
                student_id=student_id,
                course_code=course_code,
                academic_year=academic_year,
                semester=semester,
            ).first()
            
            if not enrollment:
                enrollment = Enrollment(
                    student_id=student_id,
                    course_code=course_code,
                    academic_year=academic_year,
                    semester=semester,
                )
                db.session.add(enrollment)
                db.session.flush()
                print(f"Created enrollment: {student_id} - {course_code}")
            
            # Get or create/update grade
            grade = Grade.query.filter_by(enrollment_id=enrollment.enrollment_id).first()
            
            if grade and not upsert_existing:
                print(f"Grade already exists for {course_code}, skipping (use --upsert to update)")
                continue
            
            if not grade:
                grade = Grade(enrollment_id=enrollment.enrollment_id)
                db.session.add(grade)
            
            # Set exact scores
            grade.ca_score = course_info["ca_score"]
            grade.exam_score = course_info["raw_exam"]
            grade.total_score = course_info["total"]
            grade.grade_letter = course_info["grade"]
            
            print(f"Updated grade: {course_code} = {course_info['grade']} (Total: {course_info['total']})")
        
        try:
            db.session.commit()
            print(f"\nSuccessfully loaded Semester 5 data for student {student_id}")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Failed to save data: {e}")
            return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Semester 5 courses with specific scores")
    parser.add_argument("--student-id", required=True, help="Student ID to populate")
    parser.add_argument("--upsert", action="store_true", help="Update existing grades if present")
    
    args = parser.parse_args()
    success = load_semester5(args.student_id, upsert_existing=args.upsert)
    exit(0 if success else 1)
