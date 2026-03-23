#!/usr/bin/env python3
"""
Clear Semester 5 (2026/2027 First semester) records from the database.
Used to prepare for admin/lecturer upload workflow.
"""

import sys
from app import create_app
from models import db, Enrollment, Grade

app = create_app()

def clear_semester5(student_id=None):
    """Delete all Semester 5 records for a specific student or all students."""
    with app.app_context():
        try:
            # Query for all enrollments in Semester 5
            query = Enrollment.query.filter(
                Enrollment.academic_year == "2026/2027",
                Enrollment.semester == "First"
            )
            
            if student_id:
                query = query.filter(Enrollment.student_id == student_id)
            
            enrollments = query.all()
            
            if not enrollments:
                print(f"No Semester 5 records found{' for student ' + student_id if student_id else ''}.")
                return
            
            print(f"Found {len(enrollments)} Semester 5 enrollment(s){' for student ' + student_id if student_id else ''}.")
            
            # Delete associated grades first
            enrollment_ids = [e.enrollment_id for e in enrollments]
            grades_deleted = Grade.query.filter(Grade.enrollment_id.in_(enrollment_ids)).delete()
            print(f"Deleted {grades_deleted} grade record(s).")
            
            # Delete enrollments
            enrollments_deleted = len(enrollments)
            for enrollment in enrollments:
                db.session.delete(enrollment)
            
            db.session.commit()
            print(f"Deleted {enrollments_deleted} enrollment record(s).")
            print("✓ Semester 5 cleared successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error clearing Semester 5: {e}")
            sys.exit(1)

if __name__ == "__main__":
    student_id = None
    if len(sys.argv) > 1:
        student_id = sys.argv[1]
    
    clear_semester5(student_id)
