"""Student service for data access and business logic."""

from flask import session
from models import Student


def get_current_student():
    """Retrieve the currently logged-in student from the session."""
    student_id = session.get('student_id')
    if not student_id:
        return None
    return Student.query.filter_by(student_id=student_id).first()
