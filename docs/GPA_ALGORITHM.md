# SADSS GPA SIMULATION ALGORITHM
**Reference:** SystemFlowchart.drawio

## 1. Core Mathematical Constants & Scaling Logic
* Maximum CA Score = 40.00
* Maximum Raw Exam Score = 100.00
* **Exam Scaling:** `Scaled_Exam_Score = (Raw_Exam_Score / 100) * 60`
* **Total Course Score:** `Total_Score = CA_Score + Scaled_Exam_Score`
* **Grade Scale (AAMUSTED Standard):**
  * 80 - 100 = A (4.0 Grade Point)
  * 75 - 79 = B+ (3.5 Grade Point)
  * 70 - 74 = B (3.0 Grade Point)
  * 65 - 69 = C+ (2.5 Grade Point)
  * 60 - 64 = C (2.0 Grade Point)
  * 55 - 59 = D+ (1.5 Grade Point)
  * 50 - 54 = D (1.0 Grade Point)
  * 0 - 49 = E/F (0.0 Grade Point - Fail)

## 2. The Initialization Logic
When a student accesses the GPA Simulator (`/gpa-simulator`), the backend MUST perform this exact check before allowing simulation:
1. **Check Student Level & Semester:**
   * `IF` Level == 100 `AND` Semester == 1:
     * `Past_CGPA` = 0.00 (No previous academic history).
     * `Total_Past_Credits` = 0.
   * `ELSE`:
     * Query the `Grade` and `Enrollment` tables.
     * Fetch `Total_Past_Credits_Attempted` and `Total_Past_Grade_Points`.
     * Calculate current `CGPA` = (`Total_Past_Grade_Points` / `Total_Past_Credits_Attempted`).

## 3. The Simulation Modes (Branching Logic)
The user interface allows two types of calculations. The backend must handle both gracefully.

**Path A: Single Course Projection**
* **Input:** A specific `Course_Code` (e.g., ITC361), a hypothetical `CA_Score` (out of 40), and a hypothetical `Raw_Exam_Score` (out of 100).
* **Execution:** Scale the Raw Exam Score to 60%. Add CA + Scaled Exam. Map to Grade Scale. Calculate new `SGPA` for the semester assuming all other current courses remain at their historical average. Output the isolated impact on the `CGPA`.

**Path B: Full Semester Target**
* **Input:** Desired Target `SGPA` (e.g., 3.60) for the current semester.
* **Execution:** Fetch all enrolled courses for the active semester. Distribute the required grade points across the active credit hours to output a table of "Required Grades per Course" to hit that target.