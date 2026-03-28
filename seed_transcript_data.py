"""Load reusable transcript data (including Semester 5 sample) for any student.

This script populates courses, enrollments, and grades with assumed CA/Exam scores
that are consistent with letter grades on the platform's 100-point scale.

When the active registration semester already exists for a student, the loader
skips that overlapping period so the transcript seed remains idempotent.
"""

import argparse

from app import app, db
from models import Course, Enrollment, Grade, Student


TRANSCRIPT_DATA = {
    "Semester 1": [
        ("ACC111", "Basic Accounting I", 3, "A"),
        ("ICT111", "Fundamentals of Information Technology", 3, "A"),
        ("MAT119", "Mathematics for Computing", 3, "A"),
        ("GPD111", "Communication and Study Skills", 3, "C"),
        ("ICT112", "Principles of Programming", 3, "A"),
        ("EDC111", "Philosophy of Education, School Curriculum, Social Change and National Development", 3, "B"),
        ("ICT113", "Computer Hardware and System Essentials", 3, "C+"),
    ],
    "Semester 2": [
        ("ICT123", "Computer Architecture", 3, "A"),
        ("ACC121", "Basic Accounting II", 3, "A"),
        ("ICT121", "Information Technology Tools", 3, "A"),
        ("ICT122", "Programming with C++", 3, "A"),
        ("MAT129", "Discrete Mathematics", 3, "B+"),
        ("EDC122", "Educational Technology", 3, "B+"),
        ("GPD122BB", "African Studies (Conflict and Conflict Management in Africa)", 3, "A"),
    ],
    "Semester 3": [
        ("GPD231CA", "Liberal Studies (Courtship and Marriage)", 3, "A"),
        ("EDC232", "Principles and Practice of Teacher Education", 3, "C+"),
        ("GPD233", "Introduction to Special Education", 3, "A"),
        ("ICT231", "Database Concepts and Design", 3, "A"),
        ("ICT233", "Web Technologies and Design", 3, "A"),
        ("ICT232", "Object-Oriented Programming with Java", 3, "A"),
        ("MAT239", "Probability and Statistics", 3, "B+"),
    ],
    "Semester 4": [
        ("EDC241", "Psychology of Human Development and Learning", 3, "B"),
        ("ICT244", "Systems Analysis and Design", 3, "A"),
        ("ICT243", "Web Programming", 3, "A"),
        ("ICT245", "Computer Networking", 3, "B+"),
        ("ICT242", "Data Structures and Algorithms", 3, "A"),
        ("ICT241", "Database Development and Implementation", 3, "A"),
        ("EDC242", "Trends in Education and School Management in Ghana", 3, "C"),
    ],
    "Semester 5": [
        ("ICT351", "Software Engineering", 3, "A"),
        ("ICT352", "Operating Systems", 3, "B+"),
        ("ICT353", "Data Communication and Networks", 3, "B"),
        ("ICT354", "Advanced Database Systems", 3, "A"),
        ("ICT355", "Human Computer Interaction", 3, "B+"),
        ("MAT349", "Numerical Methods", 3, "C+"),
        ("EDC351", "Assessment in Education", 3, "B"),
    ],
}

SEMESTER_MAPPING = {
    "Semester 1": ("2024/2025", "First"),
    "Semester 2": ("2024/2025", "Second"),
    "Semester 3": ("2025/2026", "First"),
    "Semester 4": ("2025/2026", "Second"),
    "Semester 5": ("2026/2027", "First"),
}

# Exact CA and raw exam scores provided for results-page alignment.
# Values are: (ca_score_out_of_40, raw_exam_out_of_100, total_score).
EXACT_SCORE_OVERRIDES = {
    "Semester 1": {
        "ACC111": (35.0, 80.0, 83.0),
        "ICT111": (37.0, 80.0, 85.0),
        "MAT119": (33.0, 80.0, 81.0),
        "GPD111": (26.0, 60.0, 62.0),
        "ICT112": (34.0, 90.0, 88.0),
        "EDC111": (30.0, 70.0, 72.0),
        "ICT113": (25.0, 70.0, 67.0),
    },
    "Semester 2": {
        "ICT123": (36.0, 80.0, 84.0),
        "ACC121": (34.0, 80.0, 82.0),
        "ICT121": (38.0, 80.0, 86.0),
        "ICT122": (35.0, 90.0, 89.0),
        "MAT129": (32.0, 75.0, 77.0),
        "EDC122": (31.0, 75.0, 76.0),
        "GPD122BB": (33.0, 80.0, 81.0),
    },
    "Semester 3": {
        "GPD231CA": (37.0, 80.0, 85.0),
        "EDC232": (26.0, 70.0, 68.0),
        "GPD233": (34.0, 80.0, 82.0),
        "ICT231": (39.0, 80.0, 87.0),
        "ICT233": (36.0, 80.0, 84.0),
        "ICT232": (34.0, 90.0, 88.0),
        "MAT239": (33.0, 75.0, 78.0),
    },
    "Semester 4": {
        "EDC241": (29.0, 70.0, 71.0),
        "ICT244": (35.0, 80.0, 83.0),
        "ICT243": (38.0, 80.0, 86.0),
        "ICT245": (32.0, 75.0, 77.0),
        "ICT242": (33.0, 80.0, 81.0),
        "ICT241": (37.0, 80.0, 85.0),
        "EDC242": (27.0, 60.0, 63.0),
    },
}


def assumed_scores_for_grade(grade_letter):
    """Generate assumed CA/Exam/Total that matches a target letter grade."""
    score_map = {
        'A': 84.0,
        'B+': 77.0,
        'B': 72.0,
        'C+': 67.0,
        'C': 62.0,
        'D+': 57.0,
        'D': 52.0,
        'E': 45.0,
    }
    total_target = score_map.get(grade_letter, 62.0)
    ca = round(min(40.0, total_target * 0.4), 2)

    # exam_score in DB is raw out of 100. Convert the needed exam contribution
    # (out of 60) back to raw scale so Total = CA + (Exam/100 * 60).
    needed_exam_component = max(0.0, total_target - ca)
    raw_exam = round(min(100.0, (needed_exam_component / 60.0) * 100.0), 2)

    total = round(ca + ((raw_exam / 100.0) * 60.0), 2)
    return ca, raw_exam, total


def _latest_active_period(enrollments):
    """Return the latest non-published academic period already present for the student."""
    if not enrollments:
        return None

    def period_key(enrollment):
        try:
            start_year = int(str(enrollment.academic_year).split('/')[0])
        except (TypeError, ValueError, IndexError):
            start_year = 0
        semester_rank = 2 if str(enrollment.semester).lower().startswith('second') else 1
        return (start_year, semester_rank)

    active_enrollments = [
        enrollment
        for enrollment in enrollments
        if not enrollment.grade or enrollment.grade.approval_status != 'Published'
    ]
    source = active_enrollments or enrollments
    latest = max(source, key=period_key)
    return (latest.academic_year, latest.semester)


def load_transcript(student_id, department_id=None, upsert_existing_grades=False):
    """Load transcript data into the database."""
    with app.app_context():
        # Get or verify student exists
        student = Student.query.filter_by(student_id=student_id).first()
        if not student:
            print(f"ERROR: Student {student_id} not found in database.")
            return False

        if department_id is None:
            department_id = student.department_id

        active_period = _latest_active_period(student.enrollments)

        loaded_count = 0
        error_count = 0

        # Process each semester
        for semester_label, courses_list in TRANSCRIPT_DATA.items():
            academic_year, semester_enum = SEMESTER_MAPPING.get(semester_label, (None, None))
            if not academic_year:
                print(f"WARNING: Skipping semester {semester_label} - no mapping found")
                continue

            if active_period and (academic_year, semester_enum) == active_period:
                print(f"\nSkipping {semester_label} ({academic_year} {semester_enum}) to avoid overlapping active registration period.")
                continue

            print(f"\nLoading {semester_label} ({academic_year} {semester_enum})...")

            for course_code, course_name, credit_hours, grade_letter in courses_list:
                try:
                    override_scores = EXACT_SCORE_OVERRIDES.get(semester_label, {}).get(course_code)
                    if override_scores:
                        ca_score, exam_score, total_score = override_scores
                    else:
                        ca_score, exam_score, total_score = assumed_scores_for_grade(grade_letter)

                    # Get or create course
                    course = Course.query.filter_by(course_code=course_code).first()
                    if not course:
                        # Determine course type based on code prefix
                        if any(code in course_code.upper() for code in ["GPD", "EDC"]):
                            course_type = "General"
                        elif any(code in course_code.upper() for code in ["ICT", "ACC", "MAT"]):
                            course_type = "Core"
                        else:
                            course_type = "Elective"

                        course = Course(
                            course_code=course_code,
                            course_name=course_name,
                            credit_hours=credit_hours,
                            department_id=department_id,
                            course_type=course_type,
                        )
                        db.session.add(course)
                        db.session.flush()
                        print(f"  Created course: {course_code}")

                    # Check if enrollment already exists
                    enrollment = Enrollment.query.filter_by(
                        student_id=student_id,
                        course_code=course_code,
                        academic_year=academic_year,
                        semester=semester_enum,
                    ).first()

                    if not enrollment:
                        # Create enrollment
                        enrollment = Enrollment(
                            student_id=student_id,
                            course_code=course_code,
                            academic_year=academic_year,
                            semester=semester_enum,
                        )
                        db.session.add(enrollment)
                        db.session.flush()
                        print(f"    Created enrollment for {course_code}")

                    if enrollment.grade and not upsert_existing_grades:
                        print(f"    SKIPPED grade for {course_code}: already exists")
                        continue

                    if enrollment.grade and upsert_existing_grades:
                        enrollment.grade.ca_score = ca_score
                        enrollment.grade.exam_score = exam_score
                        enrollment.grade.total_score = total_score
                        enrollment.grade.grade_letter = grade_letter
                        enrollment.grade.approval_status = "Published"
                        print(f"    Updated grade: {grade_letter} ({total_score})")
                    else:
                        grade = Grade(
                            enrollment_id=enrollment.enrollment_id,
                            ca_score=ca_score,
                            exam_score=exam_score,
                            total_score=total_score,
                            grade_letter=grade_letter,
                            approval_status="Published",
                        )
                        db.session.add(grade)
                        print(f"    Created grade: {grade_letter} ({total_score})")

                    loaded_count += 1

                except Exception as e:
                    error_count += 1
                    print(f"  ERROR processing {course_code}: {str(e)}")

        # Commit all changes
        try:
            db.session.commit()
            print(f"\n✓ Successfully loaded {loaded_count} grades")
            if error_count > 0:
                print(f"⚠ {error_count} errors encountered")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Failed to commit changes: {str(e)}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Load transcript data into the database")
    parser.add_argument("--student-id", default="USD260012", help="Student ID to load transcript for")
    parser.add_argument("--department-id", type=int, default=None, help="Department ID (auto-detected if not provided)")
    parser.add_argument(
        "--upsert-existing-grades",
        action="store_true",
        help="Update existing grades with assumed CA/Exam totals",
    )
    args = parser.parse_args()

    success = load_transcript(args.student_id, args.department_id, args.upsert_existing_grades)
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
