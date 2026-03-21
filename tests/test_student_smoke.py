"""Student-side smoke tests for key portal pages.

Run with:
    python -m unittest tests.test_student_smoke -v
"""

import unittest

from app import app, db
from seed_db import seed_initial_data


class StudentPortalSmokeTest(unittest.TestCase):
    """Smoke tests to ensure student routes render without server errors."""

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
            data={"student_id": "USD260012", "password": "password123"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/dashboard", response.headers.get("Location", ""))

    def test_public_pages(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/login").status_code, 200)
        self.assertEqual(self.client.get("/forgot-password").status_code, 200)
        self.assertEqual(self.client.get("/it-helpdesk").status_code, 200)

    def test_landing_hides_dashboard_for_logged_out_user(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertNotIn('>Dashboard<', body)
        self.assertIn('>Explore Modules<', body)
        self.assertIn('id="ready-to-start"', body)

    def test_protected_student_pages(self):
        self._login()
        routes = [
            "/dashboard",
            "/profile",
            "/account-settings",
            "/my-courses",
            "/results",
            "/resource-hub",
            "/gpa-simulator",
            "/financials",
            "/helpdesk",
        ]
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)

    def test_helpdesk_status_filters(self):
        self._login()
        for status in ["All", "Open", "Pending", "Resolved"]:
            with self.subTest(status=status):
                response = self.client.get(f"/helpdesk?status={status}")
                self.assertEqual(response.status_code, 200)

    def test_helpdesk_ticket_create_with_priority(self):
        self._login()
        response = self.client.post(
            "/helpdesk",
            data={
                "ticket_type": "Technical",
                "priority": "High",
                "course_code": "",
                "description": "Smoke test ticket creation with priority.",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/helpdesk", response.headers.get("Location", ""))

    def test_resource_hub_type_filters(self):
        self._login()
        for resource_type in ["All", "Department", "Course"]:
            with self.subTest(resource_type=resource_type):
                response = self.client.get(f"/resource-hub?type={resource_type}")
                self.assertEqual(response.status_code, 200)

    def test_transcript_pdf_download(self):
        self._login()
        response = self.client.get("/results/transcript.pdf")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")

    def test_account_settings_profile_update(self):
        self._login()
        response = self.client.post(
            "/account-settings",
            data={
                "action": "profile",
                "first_name": "Jane",
                "middle_name": "M",
                "last_name": "Doe",
                "email_address": "jane@usted.edu.gh",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/account-settings", response.headers.get("Location", ""))

    def test_account_settings_password_update(self):
        self._login()
        response = self.client.post(
            "/account-settings",
            data={
                "action": "password",
                "current_password": "password123",
                "new_password": "password123",
                "confirm_password": "password123",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/account-settings", response.headers.get("Location", ""))


if __name__ == "__main__":
    unittest.main()
