"""Lecturer-side smoke tests for key lecturer pages.

Run with:
    python -m unittest tests.test_lecturer_smoke -v
"""

import unittest
from io import BytesIO

from app import create_app
from models import db
from models import Grade, Resource
from seed_db import seed_initial_data


class LecturerPortalSmokeTest(unittest.TestCase):
    """Smoke tests to ensure lecturer routes render and stay scoped."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app('sqlite:///lecturer_smoke.db')
        with cls.app.app_context():
            db.drop_all()
            db.create_all()
        seed_initial_data(reset_schema=False, target_app=cls.app)

    def setUp(self):
        self.client = self.app.test_client()

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
            "/lecturer/resource-management",
            "/lecturer/course/ITC356/resources",
            "/lecturer/course/ITC356/roster",
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

        with self.app.app_context():
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

        with self.app.app_context():
            refreshed_grade = Grade.query.filter_by(enrollment_id=enrollment_id).first()
            self.assertIsNotNone(refreshed_grade)
            self.assertEqual(refreshed_grade.approval_status, "Pending_HOD")

    def test_course_resource_crud(self):
        self._login()

        upload_response = self.client.post(
            "/lecturer/course/ITC356/resources/upload",
            data={
                "resource_label": "Week 1 Slides",
                "resource_file": (BytesIO(b"slides content"), "week1.pdf"),
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        self.assertEqual(upload_response.status_code, 302)
        self.assertIn("/lecturer/course/ITC356/resources", upload_response.headers.get("Location", ""))

        with self.app.app_context():
            created_resource = (
                Resource.query
                .filter_by(course_code="ITC356", resource_type="Course", file_name="Week 1 Slides")
                .order_by(Resource.resource_id.desc())
                .first()
            )
            self.assertIsNotNone(created_resource)
            resource_id = created_resource.resource_id

        update_response = self.client.post(
            f"/lecturer/course/ITC356/resources/{resource_id}/update",
            data={"resource_label": "Week 1 Lecture Slides"},
            follow_redirects=False,
        )
        self.assertEqual(update_response.status_code, 302)

        with self.app.app_context():
            updated_resource = Resource.query.filter_by(resource_id=resource_id).first()
            self.assertIsNotNone(updated_resource)
            self.assertEqual(updated_resource.file_name, "Week 1 Lecture Slides")

        delete_response = self.client.post(
            f"/lecturer/course/ITC356/resources/{resource_id}/delete",
            follow_redirects=False,
        )
        self.assertEqual(delete_response.status_code, 302)

        with self.app.app_context():
            deleted_resource = Resource.query.filter_by(resource_id=resource_id).first()
            self.assertIsNone(deleted_resource)


if __name__ == "__main__":
    unittest.main()
