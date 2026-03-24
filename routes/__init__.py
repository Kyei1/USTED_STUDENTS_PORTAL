"""Routes module for Flask blueprints."""

from routes.public_bp import public_bp
from routes.student_bp import student_bp
from routes.lecturer_bp import lecturer_bp
from routes.admin_bp import admin_bp

__all__ = ['public_bp', 'student_bp', 'lecturer_bp', 'admin_bp']
