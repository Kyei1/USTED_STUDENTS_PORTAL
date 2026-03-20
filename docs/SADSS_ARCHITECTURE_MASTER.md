# OVERHAUL INC. MASTER ARCHITECTURE DOCUMENT
## Project: Enhanced USTED Students Portal (SADSS)
**Lead Developer / Architect:** LazyDev
**Target Institution:** University of Skills Training and Entrepreneurial Development (USTED)
**Target Department:** Information Technology Education (Level 300/400)

### 1. The Core Objective & Phased Rollout
This is a comprehensive, multi-role university portal designed to solve administrative and academic pain points.
* **Phase 1 (Current):** Student Experience (Transparent grading, GPA simulation, Helpdesk).
* **Phase 2:** Lecturer Experience (Secure CA/Exam score entry, course management).
* **Phase 3:** Admin Experience (System oversight, ticket resolution, financial tracking).

### 2. Technology Stack
* **Backend:** Python 3, Flask, Flask-Session.
* **Database:** SQLite (local development), Flask-SQLAlchemy (ORM).
* **Frontend Structure:** HTML5, Jinja2 Templating.
* **Frontend Framework:** STRICTLY Bootstrap 5 (using grid, cards, and flexbox utilities). No Tailwind.
* **Custom Styling:** A bespoke CSS layer enforcing the AAMUSTED brand identity.

### 3. Design System & Theme Identity (Strict Maroon, Gold & White)
All UI generation must strictly adhere to this color palette. Do not use default Bootstrap greens or primary blues.
* **Primary Branding (Maroon):** `#7A0016` (Used for top header borders, active sidebar links, and primary accents).
* **Secondary Accent (Gold):** `#DBA111` (Used for primary calls to action, important buttons, and highlights).
* **Typography & Icons (Deep Maroon Ink):** `#4A000D` (Used for body text, headings, and iconography).
* **Backgrounds:** `#f8f9fa` (Main content area), `#ffffff` (Cards and top header).
* **Layout Structure:** A persistent left Sidebar (collapsible on mobile) and a clean White Top Header. All pages extend `base.html`.
* **The Overhaul Signature:** The `base.html` footer must always contain a cheeky developer credit: *"Crafted with ☕ and late-night code by LazyDev @ Overhaul Inc."* (or similar variant) styled with the Maroon and Gold theme variables.

### 4. Hyper-Responsiveness Mandate
The portal must render flawlessly on all device sizes (from ultra-small mobile to 4K desktop) without horizontal scrolling or disorganized overlapping.
* **Fluid Layouts:** Strictly use `container-fluid` for main content areas to utilize available screen real estate.
* **Responsive Tables:** Every `<table>` must be wrapped in a `<div class="table-responsive">` so data (like Results and Financials) can scroll horizontally on mobile without breaking the page width.
* **Flexbox Wrapping:** Use `flex-wrap` on all button groups and stat cards so they stack vertically on smaller screens instead of shrinking to unreadable sizes.
* **No Fixed Widths:** Never hardcode widths (e.g., `width: 500px`). Use percentage-based Bootstrap classes (e.g., `w-100`, `w-md-50`).
* **Sidebar Behavior:** The maroon sidebar must automatically collapse behind a hamburger menu on screens smaller than 992px (`lg` breakpoint).

### 5. Database Architecture (The ERD)
The database schema (`models.py`) consists of 12 interconnected tables using SQLAlchemy ORM.
* **Users:** `Student` (PK: student_id), `Lecturer` (PK: staff_id), `Admin` (PK: adminID).
* **Academics:** `Department`, `Course`, `Enrollment` (links Student to Course), `Grade` (links Enrollment to CA/Exam scores), `Course_Lecturer`.
* **Operations:** `Financial_Status` (Tracks Billed vs. Paid), `Resource` (Downloadable files), `Announcement`, `Support_Ticket`.

### 6. Core Student Features (Phase 1)
* **Dashboard (`/dashboard`):** The landing zone. Displays program info, financial clearance, and quick links.
* **Results & Transcripts (`/results`):** A dedicated hub where students view exact breakdowns of their CA and Final Examination scores, and download official PDF transcripts.
* **GPA Simulator (`/gpa-simulator`):** Pulls `Enrollment` data so students can project their CGPA based on hypothetical scores.
* **Financial Statement (`/financials`):** A read-only tracking dashboard showing Total Billed, Total Cleared, and Arrears.
* **Helpdesk (`/helpdesk`):** Allows students to submit support tickets mapping to the `Support_Ticket` table.
* **Landing Page (`/`):** A public-facing marketing page highlighting the system's features.

### 7. Copilot Directives (Rules of Engagement)
1. **Never Hallucinate Inline Styles:** Always use Bootstrap 5 utility classes first. Only use inline styles if referencing the custom CSS variables (e.g., `var(--usted-maroon)`).
2. **Always Use ORM:** When writing backend queries, strictly use SQLAlchemy syntax (e.g., `Student.query.filter_by()`), never raw SQL.
3. **Respect the Base Layout:** All new HTML templates must start with `{% extends 'base.html' %}` and place content inside `{% block content %}`.