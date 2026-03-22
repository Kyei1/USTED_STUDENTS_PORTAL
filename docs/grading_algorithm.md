# SADSS GRADING ALGORITHM SPECIFICATION
**Target Engine:** Python 3 (Flask) / SQLAlchemy
**Context:** Calculation of Academic Standing (SGPA/CGPA) for AAMUSTED students.

### 1. Database Variable Mapping
Assume the following data comes from the SQLAlchemy models:
* `course.credits` (Integer: e.g., 3)
* `grade.CA_score` (Float: Max 40.0, can be None)
* `grade.Exam_Score` (Float: Raw score input out of 100.0, can be None)
* `student.Total_Past_Credits_Attempted` (Float: Historical CCR baseline)
* `student.Total_Past_Grade_Points` (Float: Historical CGV baseline)

### 2. The Grade Scale Matrix (AAMUSTED Standard)
When converting a Total Score to a Grade Point (GP), use this strict conditional logic:
* `>= 80`: GP = 4.0, Grade = 'A', Remark = 'Pass'
* `>= 75 AND < 80`: GP = 3.5, Grade = 'B+', Remark = 'Pass'
* `>= 70 AND < 75`: GP = 3.0, Grade = 'B', Remark = 'Pass'
* `>= 65 AND < 70`: GP = 2.5, Grade = 'C+', Remark = 'Pass'
* `>= 60 AND < 65`: GP = 2.0, Grade = 'C', Remark = 'Pass'
* `>= 55 AND < 60`: GP = 1.5, Grade = 'D+', Remark = 'Pass'
* `>= 50 AND < 55`: GP = 1.0, Grade = 'D', Remark = 'Pass'
* `< 50`: GP = 0.0, Grade = 'E', Remark = 'Re-sit'

### 3. Execution Order (The Python Logic Steps)
When calculating results for a specific semester, loop through all active enrollments:

**STEP 1: The 'IC' (Incomplete) Intercept**
* `IF` `grade.Exam_Score` is `None` OR `grade.CA_score` is `None`:
  * `Grade` = 'IC'
  * `Remark` = 'Incomplete / Pending'
  * `SGP` = 0.0
  * **CRITICAL:** Do NOT add `course.credits` to the `SCR` (Semester Credits Registered). Skip to the next course.

**STEP 2: Course-Level Calculations (For Completed Grades)**
1. `Scaled_Exam` = `(grade.Exam_Score / 100) * 60`
2. `Total_Score` = `grade.CA_score + Scaled_Exam`
3. `Grade_Point` = [Map `Total_Score` using the Grade Scale Matrix above]
4. `SGP` (Semester Grade Point) = `course.credits * Grade_Point`
5. Add `course.credits` to `SCR`.
6. Add `SGP` to `Total_Semester_SGP`.

**STEP 3: Semester & Cumulative Aggregation**
1. `SGPA` = `Total_Semester_SGP / SCR` (Ensure `SCR > 0` to prevent division by zero).
2. `CCR` = `student.Total_Past_Credits_Attempted + SCR`
3. `CGV` = `student.Total_Past_Grade_Points + Total_Semester_SGP`
4. `CGPA` = `CGV / CCR` (Ensure `CCR > 0`).

### 4. Strict Edge Cases & Error Handling
* **Rounding:** All final output variables (`SGPA`, `CGPA`, `SGP`, `Total_Score`) must be rounded to exactly 2 decimal places before being passed to the Jinja template (e.g., `round(CGPA, 2)`).