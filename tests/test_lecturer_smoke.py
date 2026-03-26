"""Lecturer-side smoke tests for key lecturer pages.

Run with:
    python -m unittest tests.test_lecturer_smoke -v
"""

import unittest

from app import app, db
from models import Grade
from seed_db import seed_initial_data


class LecturerPortalSmokeTest(unittest.TestCase):
    """Smoke tests to ensure lecturer routes render and stay scoped."""

    @classmethod
    def setUpClass(cls):
        with app.app_context():
            db.drop_all()
            db.create_all()
        seed_initial_data(reset_schema=False)

    def setUp(self):
        self.client = app.test_client()

    def _login(self):
        response = self.client.post(
            "/login",
            data={
                "identifier": "LIT0001",
                "password": "lect1234",
                "account_type": "lecturer",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/lecturer/dashboard", response.headers.get("Location", ""))

    def test_protected_lecturer_pages(self):
        self._login()
        routes = [
            "/lecturer/dashboard",
            "/lecturer/profile",
            "/lecturer/account-settings",
            "/lecturer/my-courses",
            "/lecturer/grade-workspace",
            "/lecturer/submission-queue",
            "/lecturer/draft-grades",
            "/lecturer/academic-helpdesk",
        ]
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)

    def test_my_courses_renders_assigned_course_rows(self):
        self._login()
        response = self.client.get("/lecturer/my-courses")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("ITC356", body)
        self.assertIn("Grade Workspace", body)

    def test_my_courses_filters(self):
        self._login()
        response = self.client.get(
            "/lecturer/my-courses?academic_year=2025/2026&class_group=L300-A&semester=First"
        )
        self.assertEqual(response.status_code, 200)

    def test_grade_workspace_bulk_submit_selected(self):
        self._login()

        with app.app_context():
            draft_grade = Grade.query.filter_by(approval_status='Draft').first()
            self.assertIsNotNone(draft_grade)
            enrollment_id = draft_grade.enrollment_id

        response = self.client.post(
            "/lecturer/grade-workspace",
            data={
                "action": "submit_selected_hod",
                "selected_enrollment_ids": str(enrollment_id),
                "academic_year": "All",
                "semester": "All",
                "course_code": "All",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/lecturer/grade-workspace", response.headers.get("Location", ""))

        with app.app_context():
            refreshed_grade = Grade.query.filter_by(enrollment_id=enrollment_id).first()
            self.assertIsNotNone(refreshed_grade)
            self.assertEqual(refreshed_grade.approval_status, "Pending_HOD")


if __name__ == "__main__":
    unittest.main()
