# Lecturer Module Plan (MOSCOW)
**Prepared: March 24, 2026**

This plan is derived from the architecture baseline in [SADSS_ARCHITECTURE_MASTER.md](SADSS_ARCHITECTURE_MASTER.md) and ERD rules in [Rules_governing_ERD_Tables.md](Rules_governing_ERD_Tables.md).

## Must Have
- Lecturer authentication and authorization boundary:
  - Separate lecturer login flow.
  - Session role checks on all lecturer endpoints.
- Lecturer dashboard:
  - Assigned courses (from `CourseLecturer`).
  - Pending grading tasks by course and period.
- Course roster view:
  - Student list by selected course + academic period.
  - Enrollment-linked visibility only.
- Grade entry and update workflow:
  - Input CA and exam scores.
  - Auto-calc totals/letters via existing grading service rules.
  - Save to `Grade` with controlled status transitions (`Draft` -> `Pending_HOD`).
- Course resource management:
  - Upload/create course resources to `Resource` with `resource_type='Course'`.
  - Resource listing/edit/remove for lecturer-owned context.
- Student-facing consistency:
  - Newly published course resources immediately visible in student Resource Hub.

## Should Have
- Bulk grade upload/import:
  - CSV template download and upload with validation report.
- Inline validation guardrails:
  - Score ranges, missing fields, and duplicate grade prevention.
- Assessment progress insights:
  - Count graded vs pending students per course.
- Lecturer announcements:
  - Course-scoped notices pushed to enrolled students.
- Feedback notes:
  - Optional qualitative feedback attached to each grade row.
- Approval handoff dashboard:
  - Quick view of all entries awaiting HOD/Admin processing.

## Could Have
- Reopen-request flow for already submitted grade sheets.
- Attendance quick-marking tied to course roster.
- Rubric templates reusable across courses.
- Grade distribution visual analytics for lecturer self-review.
- Office-hour slots and student booking widget.

## Won't Have (for initial lecturer release)
- Full chat/messaging platform.
- Native mobile app for lecturers.
- AI auto-grading or auto-comment generation.
- Complex workflow engine across multiple faculties.

## Seamless Lecturer-Student Experience Additions
- Shared course timeline:
  - Lecturer posts (resources/announcements) appear in student dashboard feed.
- Unified ticket context:
  - Tickets linked to course show lecturer context and status updates to student.
- Transparent grade lifecycle:
  - Students see state (`Draft`, `Pending`, `Published`) without exposing restricted data.
- Resource discoverability:
  - Lecturer-tagged resources appear in student filters by course and topic.
- Action traceability:
  - Key lecturer actions (publish grades/resources) reflected as student notifications.
