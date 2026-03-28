"""Student-side smoke tests for key portal pages.

Run with:
    python -m unittest tests.test_student_smoke -v
"""

import unittest
import re

from app import create_app
from models import db
from seed_db import seed_initial_data


class StudentPortalSmokeTest(unittest.TestCase):
    """Smoke tests to ensure student routes render without server errors."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app('sqlite:///student_smoke.db')
        with cls.app.app_context():
            db.drop_all()
            db.create_all()
        seed_initial_data(reset_schema=False, target_app=cls.app)

    def setUp(self):
        self.client = self.app.test_client()

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

    def test_dashboard_and_results_cgpa_match(self):
        self._login()

        dashboard_body = self.client.get("/dashboard").get_data(as_text=True)
        results_body = self.client.get("/results").get_data(as_text=True)

        dashboard_match = re.search(r"Current CGPA.*?>(\d+\.\d{2})<", dashboard_body, re.S)
        results_match = re.search(r"Cumulative GPA</p>\s*<p class=\"metric-value\">(\d+\.\d{2})<", results_body, re.S)

        self.assertIsNotNone(dashboard_match)
        self.assertIsNotNone(results_match)
        self.assertEqual(dashboard_match.group(1), results_match.group(1))

    def test_registration_pdf_downloads(self):
        self._login()

        current_response = self.client.get("/my-courses/registration-download")
        self.assertEqual(current_response.status_code, 200)
        self.assertEqual(current_response.mimetype, "application/pdf")
        self.assertIn("attachment", current_response.headers.get("Content-Disposition", ""))

        period_response = self.client.get("/my-courses/registration-download/2025/2026/First")
        self.assertEqual(period_response.status_code, 200)
        self.assertEqual(period_response.mimetype, "application/pdf")
        self.assertIn("attachment", period_response.headers.get("Content-Disposition", ""))

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
