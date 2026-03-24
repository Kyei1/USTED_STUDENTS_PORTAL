# USTED Students Portal - Implementation Roadmap
**Status as of March 24, 2026**

## Executive Snapshot
- Student module is production-demo ready and smoke-tested.
- Resource Hub was upgraded with department-aware IT catalogs, tabbed UX, and interactive filtering.
- Profile and Account Settings include demo-oriented completion and roadmap experiences.
- Next implementation target: Lecturer module, then Admin workflows.

## Completion Matrix

### Phase 1 - Foundation
- Completed: ORM schema, session auth, app/bootstrap wiring, seed scripts.

### Phase 2 - Student Experience
- Completed:
  - Dashboard
  - Profile
  - Account Settings
  - My Courses (+ registration PDF)
  - Results (+ transcript PDF)
  - GPA Simulator (single + target mode)
  - Financials
  - Helpdesk
  - Resource Hub
- Verified:
  - Student smoke tests passing (9/9).

### Phase 3 - Lecturer Experience
- Not started (implementation target next).

### Phase 4 - Admin Experience
- Not started.

## Student Module Hardening (Post-demo polish)
- Add unit tests for GPA/resource filtering classification logic.
- Expand smoke tests for newly added Resource Hub filter states.
- Add stricter form validations for profile/account updates.
- Add lightweight audit log entries on sensitive account actions.

## Lecturer Module - Immediate Delivery Plan
1. Lecturer authentication and role-safe session isolation.
2. Lecturer dashboard with assigned courses and pending grading actions.
3. Course roster view (enrolled students by period).
4. Grade capture workflow (CA + exam + computed totals) with status transitions.
5. Resource publishing workflow for course materials.

## Admin Module - After Lecturer MVP
1. Approval workflow for grade publication states.
2. User and course lifecycle management.
3. Helpdesk oversight and escalation controls.
4. Financial clearance and year-level policy controls.

## Risk Notes
- SQLite is fine for demo but should be migrated for multi-user concurrency.
- Lecturer and admin modules need explicit authorization boundaries to prevent cross-role data leaks.
- Reporting/export features should be standardized for both lecturer and student portals.

## Supporting Documents
- [docs/SADSS_ARCHITECTURE_MASTER.md](docs/SADSS_ARCHITECTURE_MASTER.md)
- [docs/Rules_governing_ERD_Tables.md](docs/Rules_governing_ERD_Tables.md)
- [docs/COMING_SOON_BACKLOG.md](docs/COMING_SOON_BACKLOG.md)
- [docs/LECTURER_MODULE_MOSCOW.md](docs/LECTURER_MODULE_MOSCOW.md)
