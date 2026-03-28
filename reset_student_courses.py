"""Reset a student's latest-semester course registrations for re-registration.

Usage:
    /workspaces/USTED_STUDENTS_PORTAL/venv/bin/python reset_student_courses.py
    /workspaces/USTED_STUDENTS_PORTAL/venv/bin/python reset_student_courses.py --student-id USD260012

This script removes the latest active registration semester for the selected student,
including linked grade rows, then recreates the standard 7-course active load.
"""

import argparse
import random
from decimal import Decimal

from app import app, db
from models import Course, Enrollment, Grade, Student


def period_rank(enrollment):
    """Sort academic periods by year then semester (First < Second)."""
    semester_rank = 2 if str(enrollment.semester).lower().startswith("second") else 1
    try:
        start_year = int(str(enrollment.academic_year).split("/")[0])
    except (TypeError, ValueError, IndexError):
        start_year = 0
    return (start_year, semester_rank)


def _latest_active_period(enrollments):
    """Prefer the latest period that still has any non-published grades."""
    active_periods = []
    for enrollment in enrollments:
        if not enrollment.grade or enrollment.grade.approval_status != "Published":
            active_periods.append((enrollment.academic_year, enrollment.semester))

    periods = active_periods or [(row.academic_year, row.semester) for row in enrollments]
    return max(periods, key=lambda period: (int(str(period[0]).split("/")[0]) if str(period[0]).split("/")[0].isdigit() else 0, 2 if period[1] == "Second" else 1))


def _active_registration_courses():
    """Return the standard 7-course active registration set."""
    return [
        ("ITC356", "Operating Systems"),
        ("ITC357", "Software Engineering"),
        ("ITC352", "Research Methods in IT"),
        ("ITC234", "Methods of Teaching IT"),
        ("ITC358", "Visual Programming using C#"),
        ("ITC354", "Data Communications and Networks"),
        ("EDC362", "Educational Measurement, Evaluation, and Statistics"),
    ]


def _calculate_grade_letter(total_score):
    if total_score >= 70:
        return "A"
    if total_score >= 60:
        return "B"
    if total_score >= 50:
        return "C"
    if total_score >= 40:
        return "D"
    return "F"


def reset_latest_semester(student_id):
    with app.app_context():
        student = Student.query.filter_by(student_id=student_id).first()
        if not student:
            print(f"NOOP: student {student_id} not found")
            return

        enrollments = Enrollment.query.filter_by(student_id=student_id).all()
        if not enrollments:
            print(f"NOOP: no enrollments found for {student_id}")
            return

        target_year, target_semester = _latest_active_period(enrollments)

        target_ids = [
            row.enrollment_id
            for row in enrollments
            if row.academic_year == target_year and row.semester == target_semester
        ]

        deleted_grades = 0
        if target_ids:
            deleted_grades = Grade.query.filter(Grade.enrollment_id.in_(target_ids)).delete(
                synchronize_session=False
            )

        deleted_enrollments = Enrollment.query.filter(Enrollment.enrollment_id.in_(target_ids)).delete(
            synchronize_session=False
        )

        db.session.flush()

        recreated = 0
        for course_code, course_name in _active_registration_courses():
            course = Course.query.filter_by(course_code=course_code).first()
            if not course:
                course = Course(
                    course_code=course_code,
                    department_id=student.department_id,
                    course_name=course_name,
                    credit_hours=3,
                    course_type="Core" if course_code.startswith(("ICT", "ITC", "CIT")) else "General",
                )
                db.session.add(course)
                db.session.flush()

            enrollment = Enrollment(
                student_id=student.student_id,
                course_code=course_code,
                academic_year=target_year,
                semester=target_semester,
            )
            db.session.add(enrollment)
            db.session.flush()

            ca_score = Decimal(str(round(random.uniform(25.00, 38.00), 2)))
            exam_score = Decimal("0.00")
            total_score = ca_score + exam_score
            grade = Grade(
                enrollment_id=enrollment.enrollment_id,
                ca_score=ca_score,
                exam_score=exam_score,
                total_score=total_score,
                grade_letter=_calculate_grade_letter(float(total_score)),
                approval_status="Draft",
            )
            db.session.add(grade)
            recreated += 1

        db.session.commit()

        print(
            "RESET DONE: "
            f"student={student_id}, "
            f"period={target_year} {target_semester}, "
            f"deleted_enrollments={deleted_enrollments}, "
            f"deleted_grades={deleted_grades}, "
            f"recreated_courses={recreated}"
        )


def main():
    parser = argparse.ArgumentParser(description="Reset latest-semester courses for a student")
    parser.add_argument("--student-id", default="USD260012", help="Student ID to reset")
    args = parser.parse_args()
    reset_latest_semester(args.student_id)


if __name__ == "__main__":
    main()
