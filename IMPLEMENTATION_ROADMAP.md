# USTED Students Portal - Implementation Roadmap
**Status as of March 20, 2026**

---

## Executive Summary

The USTED Students Portal has successfully transitioned from initial infrastructure (Phase 1) through UI/feature development (Phase 2) to its current state. The application is **feature-complete for Phase 2** with comprehensive student dashboards, GPA simulation, financial tracking, and support ticketing. This roadmap outlines remaining tasks, outstanding features, and recommended next phases.

---

## Current Status Dashboard

### ✅ Phase 1: Foundation (COMPLETE)
- [x] SQLAlchemy ORM schema with 12 entities and relationships
- [x] Secure authentication with Werkzeug password hashing
- [x] Seed script for test data (Jane Doe, 3 IT courses)
- [x] Flask app initialization with SQLAlchemy
- [x] Session-based login/logout flow

### ✅ Phase 2: Student Experience (COMPLETE)
- [x] Landing page (index.html) - public-facing, maroon/gold/white branding
- [x] Login page (login.html) - Split-screen design inspired by Canvas
- [x] Dashboard (dashboard.html) - Sidebar navigation, welcome section, quick-action cards, enrolled courses table, toggleable results
- [x] GPA Simulator (gpa_simulator.html) - Dual-mode system (single-course and target SGPA projection)
- [x] Results/Transcript (results.html) - Academic standing display
- [x] Financial Statement (financials.html) - Billed/paid/arrears tracking
- [x] Helpdesk/Support Tickets (helpdesk.html) - Create and view tickets
- [x] Master theme (base.html) - Persistent sidebar (collapsible on mobile), top header, responsive layout
- [x] CSS variable centralization - Maroon/gold/white palette with reusable tokens

### ✅ Phase 2: Outstanding Items (CLOSED)
- [x] **Resource Hub** - Route implemented, template added, dashboard links connected
- [x] **PDF Transcript Export** - PDF generation connected through reportlab

### ❌ Phase 3: Lecturer/Admin Experience (NOT STARTED)
- [ ] Lecturer login and dashboard
- [ ] Lecturer: View enrolled students by course
- [ ] Lecturer: Input grades and manage assessments
- [ ] Admin: Account management (create/delete accounts)
- [ ] Admin: Department/course management
- [ ] Admin: Financial clearance workflow
- [ ] Admin: Support ticket resolution queue

### ❌ Phase 4: Enhancements (NOT STARTED)
- [ ] Email notifications (new tickets, grade uploads)
- [ ] SMS alerts for financial arrears
- [ ] Mobile app (optional; responsive web covers most use cases)
- [ ] Advanced reporting and analytics
- [ ] API layer for integrations

---

## Detailed Feature Inventory

### Backend Routes (`app.py`)
| Route | Verb | Status | Notes |
|-------|------|--------|-------|
| `/` | GET | ✅ Complete | Landing page |
| `/login` | GET, POST | ✅ Complete | ORM-based auth with hash validation |
| `/dashboard` | GET | ✅ Complete | Fetch enrolled courses and financial status |
| `/results` | GET | ✅ Complete | Display academic records (grades, transcripts) |
| `/results/transcript.pdf` | GET | ✅ Complete | Returns downloadable transcript PDF |
| `/gpa-simulator` | GET, POST | ✅ Complete | Dual-mode (single-course & target SGPA simulation) |
| `/financials` | GET | ✅ Complete | Billed/paid/arrears summary |
| `/helpdesk` | GET, POST | ✅ Complete | Create and list support tickets |
| `/logout` | GET | ✅ Complete | Clear session and redirect to login |
| `/resource-hub` | GET | ✅ Complete | Lists department/course resources for logged-in student |

### Frontend Templates (`/templates/`)
| File | Status | Purpose |
|------|--------|---------|
| index.html | ✅ Complete | Public landing page with hero, feature cards, footer |
| login.html | ✅ Complete | Split-screen auth UI with password toggle |
| base.html | ✅ Complete | Master shell with sidebar, header, CSS variables |
| dashboard.html | ✅ Complete | Student dashboard with quick actions, quick-access results |
| results.html | ✅ Complete | Detailed academic breakdown by semester/course |
| gpa_simulator.html | ✅ Complete | Dual-mode GPA projection interface |
| financials.html | ✅ Complete | Financial statement with arrears tracking |
| helpdesk.html | ✅ Complete | Support ticket creation and history |
| resource_hub.html | ✅ Complete | Resource listing and open/download actions |

### Database Models (`models.py`)
| Entity | Status | Key Fields |
|--------|--------|-----------|
| Student | ✅ Complete | student_id, name, level, email, password_hash |
| Lecturer | ✅ Complete | lecturer_id, name, email, department_code |
| Admin | ✅ Complete | admin_id, name, email |
| Department | ✅ Complete | department_code, name |
| Course | ✅ Complete | course_code, name, credit_hours, department_code |
| Enrollment | ✅ Complete | student_id, course_code, academic_year, semester |
| Grade | ✅ Complete | enrollment_id, ca_score, raw_exam_score, total_score |
| FinancialStatus | ✅ Complete | student_id, academic_year, amount_billed, amount_paid |
| SupportTicket | ✅ Complete | ticket_id, student_id, ticket_type, description, status |
| Announcement | ✅ Complete | announcement_id, title, body, posted_date |
| Resource | ✅ Complete | resource_id, file_name, file_type, description |
| Course_Lecturer | ✅ Complete | course_code, lecturer_id |

### Design System
- **Color Palette** (Maroon/Gold/White—no blue, no green):
  - Primary: `--usted-maroon` (#7a0016)
  - Secondary: `--usted-gold` (#dba111)
  - Text: `--usted-ink` (#4a000d)
  - Variants: soft/mid/strong for maroon and gold
  - Background: `--usted-bg` (#f8f9fa)

- **Framework**: Bootstrap 5.3.3 CDN + Jinja2 templating
- **Icons**: Bootstrap Icons 1.11.3
- **Layout Pattern**: Persistent sidebar (collapsible on mobile), white header, responsive main content

---

## Folder Structure (Current)
```
/workspaces/USTED_STUDENTS_PORTAL/
├── app.py                              [Main Flask app with all routes]
├── models.py                           [SQLAlchemy ORM schema]
├── database.py                         [DB initialization helper]
├── init_db.py                          [DB schema creation]
├── seed_db.py                          [Test data seeding]
├── requirements.txt                    [Dependencies]
├── students_portal.db                  [SQLite database]
├── docs/
│   ├── SADSS_ARCHITECTURE_MASTER.md    [Design guidelines]
│   └── GPA_ALGORITHM.md                [GPA calculation logic]
├── static/
│   ├── css/
│   │   ├── base.css                    [Shared theme and layout styles]
│   │   └── dashboard.css               [Dashboard-specific styles]
│   └── js/
│       ├── base.js                     [Top nav and profile dropdown behavior]
│       └── dashboard.js                [Dashboard interactions]
├── templates/
│   ├── base.html                       [Legacy base shell retained for compatibility]
│   ├── index.html                      [Legacy landing template retained for compatibility]
│   ├── login.html                      [Legacy login template retained for compatibility]
│   ├── dashboard.html                  [Legacy dashboard template retained for compatibility]
│   ├── results.html                    [Legacy results template retained for compatibility]
│   ├── gpa_simulator.html              [Legacy GPA template retained for compatibility]
│   ├── financials.html                 [Legacy financials template retained for compatibility]
│   ├── helpdesk.html                   [Legacy helpdesk template retained for compatibility]
│   ├── resource_hub.html               [Legacy resource hub template retained for compatibility]
│   ├── layouts/
│   │   └── base.html                   [Grouped layout entrypoint]
│   ├── public/
│   │   ├── index.html                  [Public-facing pages]
│   │   └── login.html                  [Authentication pages]
│   └── student/
│       ├── dashboard.html              [Student dashboard]
│       ├── results.html                [Student results]
│       ├── gpa_simulator.html          [Student GPA simulator]
│       ├── financials.html             [Student financial statement]
│       ├── helpdesk.html               [Student helpdesk]
│       └── resource_hub.html           [Student resource hub]
└── [Other: venv/, __pycache__/, .git/]
```

---

## Recommended Next Steps (Priority Order)

### 🔴 IMMEDIATE (Before PR Merge)

**1. Final Testing & QA** *(Est: 1-2 hours)*
- Test all 9 routes with dashboard login (Jane Doe / password123)
- Verify palette consistency across all pages (maroon/gold/white only)
- Test responsive design (mobile/tablet/desktop)
- Check for console errors (browser DevTools)
- Validate seed script runs without errors
- Commit changes to `copilot/create-project-structure` branch

---

### 🟡 SHORT-TERM (Phase 2.5 - Post-Merge Polish, 1-2 Sprints)

**2. Project Structure Refactor (File Grouping)** *(Est: 2-4 hours)*
- Move CSS/JS out of templates into `static/css` and `static/js`
- Keep templates organized by domain (`templates/student`, `templates/public`, `templates/layouts`)
- Split backend into `routes`, `services`, and `models` modules
- Add blueprints (`student_bp`, `public_bp`) to reduce `app.py` size
- Keep route names stable while refactoring to avoid template breakage

**3. Enhance GPA Simulator UI** *(Est: 2-3 hours)*
- Add visual grade distribution chart (Chart.js or similar)
- Add what-if comparison (show before/after side-by-side)
- Implement grade history visualization

**4. Improve Financial UI** *(Est: 1-2 hours)*
- Add payment plan visualization
- Include clearance status badge (Cleared/Arrears/At-Risk)
- Add payment history drill-down

**5. Helpdesk Enhancements** *(Est: 2-3 hours)*
- Add ticket status filtering (Open/In Progress/Resolved)
- Add priority assignment
- Basic email notification on ticket update

---

### 🟢 MEDIUM-TERM (Phase 3 - Lecturer/Admin, 2-3 Sprints)

**7. Lecturer Portal** *(Est: 8-10 hours)*
- Separate login (`/lecturer-login`) with lecturer auth
- Lecturer dashboard: List enrolled students by course
- Grade entry form: Input CA scores, exam scores, computed totals
- Attendance tracking interface

**8. Admin Portal** *(Est: 10-12 hours)*
- Separate login (`/admin-login`) with admin auth
- Dashboard: System overview (students, courses, financials)
- User management: Create/edit/delete students, lecturers
- Course management: Add/edit/deprecate courses
- Financial clearance workflow: Mark paid, approve arrears

---

### 🔵 FUTURE (Phase 4 - Enhancements, Optional)

**9. Notifications System** *(Est: 4-6 hours)*
- Email integration (Flask-Mail)
- SMS alerts (Twilio or similar)
- In-app notification center

**10. Reporting & Analytics** *(Est: 6-8 hours)*
- Department performance dashboards
- GPA distribution charts
- Financial summary reports
- Support ticket analytics

**11. API Layer** *(Est: 4-6 hours)*
- RESTful API for mobile app or external integrations
- Token-based auth (JWT)
- Versioned endpoints

---

## Testing Recommendations

### Manual QA Checklist
- [ ] Navigation: All sidebar links active and functional
- [ ] Auth: Login/logout cycle with credential validation
- [ ] Dashboard: Enrollments, financial status, notifications display correctly
- [ ] GPA Simulator: Both modes calculate correctly (single-course & target SGPA)
- [ ] Results: All grades and transcripts display with correct calculations
- [ ] Financials: Billed/paid/arrears totals reconcile
- [ ] Helpdesk: Tickets submit and display correctly
- [ ] Responsive: Layout adapts on mobile (<768px), tablet (768-991px), desktop (>992px)
- [ ] Palette: No blue/green accents visible; maroon/gold/white only
- [ ] Performance: Page load times <2 seconds

### Automated Testing (Future)
- Unit tests for GPA calculation functions (score_to_point, score_to_letter, etc.)
- Integration tests for routes (login, dashboard, results)
- Database transaction rollback for test isolation
- Example test file: `tests/test_gpa_simulator.py`

---

## Development Workflow

### Current Branch Strategy
- **Main Branch**: Production-ready releases
- **Active Branch**: `copilot/create-project-structure` (PR #2)
  - Feature complete for Phase 2
  - Resource Hub and transcript PDF export are implemented
  - Awaiting final QA and optional file-organization refactor

### Deployment Readiness Checklist
- [ ] All Phase 2 routes tested and passing
- [ ] Secret key configured in environment (not hardcoded)
- [ ] Database migrated to production-grade SQLite or PostgreSQL
- [ ] Error handling implemented for DB failures
- [ ] Logging configured for production
- [ ] CORS/CSRF protections enabled
- [ ] Rate limiting on auth endpoints

---

## Success Metrics

### Phase 2 Completion Criteria (CURRENT)
- ✅ 9/9 student routes implemented
- ✅ 9/9 student templates styled with brand palette
- ✅ ORM schema complete with relationships
- ✅ GPA calculation logic verified
- ✅ Seed script functional
- ✅ Resource hub route implemented
- ✅ PDF export functional

### Phase 3 Readiness (FUTURE)
- Authentication for lecturers and admins
- Grade upload and management workflows
- Course and department administration
- Final user acceptance testing

---

## Known Limitations & Future Considerations

1. **Database**: Currently using SQLite (fine for dev/demo, not production). Migrate to PostgreSQL for scaling.
2. **PDF Generation**: Implemented with `reportlab`; consider `weasyprint` later if HTML-styled transcripts are needed.
3. **Email**: No email integration yet. Add Flask-Mail for notifications.
4. **Lecturer/Admin**: Separate portals not yet built; will require significant UI work.
5. **Static Files**: No `/static/` folder needed since all CSS is inline (Bootstrap CDN). Consider adding if custom icon sets or large CSS files needed.
6. **Timezone Handling**: Currently no timezone support; all timestamps UTC. Add timezone-aware datetime handling for international use.

---

## Contact & Documentation

- **Architecture Guide**: See [docs/SADSS_ARCHITECTURE_MASTER.md](docs/SADSS_ARCHITECTURE_MASTER.md)
- **GPA Algorithm**: See [docs/GPA_ALGORITHM.md](docs/GPA_ALGORITHM.md)
- **Main Repo**: USTED_STUDENTS_PORTAL (GitHub: Kyei1)
- **Current PR**: #2 - Bootstrap Flask student portal with login, DB layer, and modern UI

---

**Last Updated**: March 20, 2026  
**Next Review**: After PR #2 merge
