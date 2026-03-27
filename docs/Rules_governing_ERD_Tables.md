1. Business Relationship Rules (Cardinality)
These rules define how your entities interact with each other based on the connecting arrows and foreign keys (FKs) in your diagram.

Academic & Departmental Rules:

A Department owns many entities: One Department has/belongs to many Students, many Lecturers, many Courses, and many Resources.

The Many-to-Many Course Rule: A Course is "taught by" many Lecturers, and a Lecturer "handles" many Courses. This is explicitly resolved by the Course_Lecturer junction table.

The Enrollment Matrix: A Student can have many Enrollments, and a Course can have many Enrollments.

Grading & Financial Rules:

Strict 1-to-1 Grading: An Enrollment "can" have exactly one Grade record. Grades cannot exist without an active enrollment.

Strict 1-to-1 Financials: A Student is linked to exactly one Financial_Status record.

Operations & Support Rules:

Ticket Ownership: A Student "passes" (creates) many Support_Tickets.

Ticket Routing: A Support_Ticket "has" a link to a specific Course (nullable, likely for technical issues) and is "reviewed" by one Admin.

Announcements: An Admin "makes" many Announcements.

2. Data Constraint Rules (Integrity)
These rules prevent bad data from entering your portal.

Unique Identifiers: A Student's reference_number MUST be completely unique across the entire database.

Mandatory Fields (NOT NULL): You have strictly forbidden empty data for critical fields. A user cannot be created without a first_name, last_name, Email_address, and Password_Hash. A Course must have a course_name.

Auto-Incrementing PKs: System IDs (like grade_id, record_id, announcement_id, ticket_id, and adminID) automatically count up. However, user IDs (student_id, staff_id) and course_code are custom Strings (VARCHAR) that must be manually provided (e.g., "USD260012", "ITC361").

Nullable Foreign Keys: The course_code and Resolved_By_Admin fields in the Support_Ticket table are specifically marked as NULLABLE, meaning a student can submit a general technical issue that isn't tied to a specific class, and a ticket can exist before an admin picks it up.

3. State Restriction Rules (ENUMs & Defaults)
These are the strict multiple-choice rules you mapped out. The database will reject any text that does not perfectly match these states.

Student Levels: Must be exactly 100, 200, 300, or 400.

Lecturer Roles: Must be Lecturer or HOD. (Defaults to Lecturer).

Admin Roles: Must be SuperAdmin, Registrar, or IT_Support.

Course Types: Must be Core, Elective, or General.

Semesters: Must be First or Second.

Grade Approvals: Must be Draft, Pending_HOD, Pending_Board, or Published. (Crucially, it Defaults to 'Draft' to prevent students from seeing unapproved grades).

Resource Types: Must be tied to either a Department or a Course.

Announcement Targets: Must be All, Students, or Lecturers. (Defaults to All).

Ticket Types: Must be Academic or Technical.

Ticket Status: Must be Open, Pending, or Resolved. (Defaults to Open).