"""Admin-side smoke tests for governance workflows.

Run with:
    python -m unittest tests.test_admin_smoke -v
"""

import unittest

from app import create_app
from models import Announcement, Grade, SupportTicket, db
from seed_db import seed_initial_data


class AdminPortalSmokeTest(unittest.TestCase):
    """Smoke tests to ensure admin routes render and key actions work."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app('sqlite:///admin_smoke.db')
        with cls.app.app_context():
            db.drop_all()
            db.create_all()
        seed_initial_data(reset_schema=False, target_app=cls.app)

    def setUp(self):
        self.client = self.app.test_client()

    def _login(self):
        response = self.client.post(
            '/login',
            data={
                'identifier': 'registrar@usted.edu.gh',
                'password': 'admin1234',
                'account_type': 'admin',
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/dashboard', response.headers.get('Location', ''))

    def test_protected_admin_pages(self):
        self._login()
        routes = [
            '/admin/dashboard',
            '/admin/profile',
            '/admin/account-settings',
            '/admin/grade-approvals',
            '/admin/helpdesk',
            '/admin/announcements',
        ]
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)

    def test_grade_approval_transitions(self):
        self._login()

        with self.app.app_context():
            grade = Grade.query.first()
            self.assertIsNotNone(grade)
            grade.approval_status = 'Pending_HOD'
            db.session.commit()
            grade_id = grade.grade_id

        approve_hod = self.client.post(
            '/admin/grade-approvals',
            data={
                'grade_id': str(grade_id),
                'action': 'approve_hod',
                'status_filter': 'All',
                'academic_year_filter': 'All',
                'course_code_filter': 'All',
            },
            follow_redirects=False,
        )
        self.assertEqual(approve_hod.status_code, 302)
        self.assertIn('/admin/grade-approvals', approve_hod.headers.get('Location', ''))

        with self.app.app_context():
            refreshed = Grade.query.filter_by(grade_id=grade_id).first()
            self.assertIsNotNone(refreshed)
            self.assertEqual(refreshed.approval_status, 'Pending_Board')

        publish_board = self.client.post(
            '/admin/grade-approvals',
            data={
                'grade_id': str(grade_id),
                'action': 'publish_board',
                'status_filter': 'All',
                'academic_year_filter': 'All',
                'course_code_filter': 'All',
            },
            follow_redirects=False,
        )
        self.assertEqual(publish_board.status_code, 302)

        with self.app.app_context():
            refreshed = Grade.query.filter_by(grade_id=grade_id).first()
            self.assertIsNotNone(refreshed)
            self.assertEqual(refreshed.approval_status, 'Published')

    def test_helpdesk_resolution_sets_admin_owner(self):
        self._login()

        with self.app.app_context():
            ticket = SupportTicket.query.filter(SupportTicket.status != 'Resolved').first()
            self.assertIsNotNone(ticket)
            ticket_id = ticket.ticket_id

        response = self.client.post(
            '/admin/helpdesk',
            data={
                'ticket_id': str(ticket_id),
                'status': 'Resolved',
                'status_filter': 'All',
                'ticket_type_filter': 'All',
                'priority_filter': 'All',
                'sort_filter': 'newest',
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/helpdesk', response.headers.get('Location', ''))

        with self.app.app_context():
            refreshed = SupportTicket.query.filter_by(ticket_id=ticket_id).first()
            self.assertIsNotNone(refreshed)
            self.assertEqual(refreshed.status, 'Resolved')
            self.assertIsNotNone(refreshed.resolved_by_admin_id)

    def test_helpdesk_shows_only_technical_tickets(self):
        self._login()
        response = self.client.get('/admin/helpdesk')
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('Technical Helpdesk Oversight', body)
        self.assertNotIn('Need urgent review of coursework rubric alignment.', body)

    def test_announcement_creation(self):
        self._login()

        title = 'Admin smoke notice'
        response = self.client.post(
            '/admin/announcements',
            data={
                'title': title,
                'target_audience': 'All',
                'message': 'Smoke test for announcement creation.',
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/announcements', response.headers.get('Location', ''))

        with self.app.app_context():
            created = Announcement.query.filter_by(title=title).first()
            self.assertIsNotNone(created)


if __name__ == '__main__':
    unittest.main()
