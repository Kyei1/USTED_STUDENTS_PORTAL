# USTED Students Portal

Flask-based student information portal for USTED with branded UI, ORM-backed data model, and student workflows for registration, results, GPA simulation, financial visibility, and support.

## Current Build Status

### Student Module Readiness
- Authentication and session flow: complete
- Dashboard and announcements: complete
- Profile and account settings: complete (with demo-ready "coming soon" roadmap cards)
- My Courses and registration PDF export: complete
- Results and transcript PDF export: complete
- GPA Simulator (single + target modes): complete
- Financials: complete
- Helpdesk ticketing with priority/status filters: complete
- Resource Hub: complete (department-curated IT resources, tabs, sub-tabs, search/filter UI)

### Validation Snapshot (March 24, 2026)
- Student smoke tests: 9/9 passing (`tests/test_student_smoke.py`)
- No template/CSS diagnostics errors in recently updated student pages.

## Stack
- Backend: Python 3, Flask, SQLAlchemy ORM
- Database: SQLite (development/demo)
- Frontend: Jinja2 templates, Bootstrap 5, custom maroon/gold design system
- PDF: reportlab

## Key Routes
- Public: `/`, `/login`, `/forgot-password`, `/it-helpdesk`
- Student: `/dashboard`, `/profile`, `/account-settings`, `/my-courses`, `/results`, `/results/transcript.pdf`, `/gpa-simulator`, `/financials`, `/helpdesk`, `/resource-hub`

## Project Layout
- `routes/`: Flask blueprints (`public_bp`, `student_bp`)
- `services/`: academic, GPA, student, PDF service logic
- `templates/` + `templates/student/`: page templates (student aliases include root templates)
- `static/css/`, `static/js/`: page styles and UI behavior scripts
- `docs/`: architecture and algorithm documentation
- `tests/`: smoke test coverage for student workflows

## Next Major Focus
- Lecturer module (grade entry and course-centered student management)
- Admin module (workflow governance, approvals, and oversight)

See the updated roadmap in [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md) and MOSCOW planning docs under [docs/](docs/).