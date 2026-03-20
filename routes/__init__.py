"""Routes module for Flask blueprints."""

from routes.public_bp import public_bp
from routes.student_bp import student_bp

__all__ = ['public_bp', 'student_bp']
