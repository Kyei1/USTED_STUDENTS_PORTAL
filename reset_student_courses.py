"""Reset a student's latest-semester course registrations for re-registration.

Usage:
    /workspaces/USTED_STUDENTS_PORTAL/venv/bin/python reset_student_courses.py
    /workspaces/USTED_STUDENTS_PORTAL/venv/bin/python reset_student_courses.py --student-id USD260012

This script removes only the latest semester's enrollments for the selected student,
including linked grade rows for those enrollments.
"""

import argparse

from app import app, db
from models import Enrollment, Grade, Student


def period_rank(enrollment):
    """Sort academic periods by year then semester (First < Second)."""
    semester_rank = 2 if str(enrollment.semester).lower().startswith("second") else 1
    try:
        start_year = int(str(enrollment.academic_year).split("/")[0])
    except (TypeError, ValueError, IndexError):
        start_year = 0
    return (start_year, semester_rank)


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

        latest = max(enrollments, key=period_rank)
        target_year = latest.academic_year
        target_semester = latest.semester

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

        db.session.commit()

        print(
            "RESET DONE: "
            f"student={student_id}, "
            f"period={target_year} {target_semester}, "
            f"deleted_enrollments={deleted_enrollments}, "
            f"deleted_grades={deleted_grades}"
        )


def main():
    parser = argparse.ArgumentParser(description="Reset latest-semester courses for a student")
    parser.add_argument("--student-id", default="USD260012", help="Student ID to reset")
    args = parser.parse_args()
    reset_latest_semester(args.student_id)


if __name__ == "__main__":
    main()
