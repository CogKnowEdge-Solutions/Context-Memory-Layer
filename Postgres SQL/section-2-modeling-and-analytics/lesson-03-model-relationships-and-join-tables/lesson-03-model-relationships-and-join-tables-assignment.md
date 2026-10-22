# Model Relationships and Join Tables — Assignment

## Exercises

### Exercise 1 — Many-to-many via junction
Explain why we need an `enrollments` table (a junction) to model students and courses. Why not put a list of course IDs in the `students` table?

### Exercise 2 — Referential integrity
The lesson uses `ON DELETE RESTRICT` on foreign keys. What does this do, and when might you choose `ON DELETE CASCADE` instead?

### Exercise 3 — Joins for a question
You want "all students and the courses they take, including students not taking anything". Which join should you use and why?

### Exercise 4 — Set difference
Write a query (conceptually) using `EXCEPT` to find students enrolled in CS101 but not in MATH101, using `enrollments` and course codes.

### Exercise 5 — SELF JOIN
Give a real-world example where a SELF JOIN is useful (other than prerequisites). Explain what it shows.

### Exercise 6 — Normalization intuition
Explain the difference between 1NF, 2NF, and 3NF in plain words, using the `students`/`courses`/`enrollments` model as context.

## Answer Key

### Exercise 1
**Answer:** A single student takes many courses and a single course has many students — many-to-many. You can't store multiple course IDs in one column without breaking 1NF (atomic values). A junction table (`enrollments`) gives one row per (student, course) and lets you store extra facts like `grade`.

**Why:** The junction preserves atomicity, allows querying in both directions, and makes constraints easy.

### Exercise 2
**Answer:** `ON DELETE RESTRICT` prevents deleting a parent row (e.g., a course) while child rows (enrollments) still reference it — protecting data. Use `ON DELETE CASCADE` when dependents are meaningless without the parent (e.g., order line items if the order is deleted).

**Why:** Choose RESTRICT to avoid accidental data loss; choose CASCADE only when deletion should automatically clean up children.

### Exercise 3
**Answer:** Use `LEFT JOIN` from `students` to `enrollments` (and to `courses`). `LEFT JOIN` keeps all students; for a student with no match, the enrollment and course columns come back as `NULL`, so students with no courses still appear.

**Why:** `INNER JOIN` would drop students with no enrollments entirely.

### Exercise 4
**Answer:**
```sql
SELECT e.student_id
FROM enrollments e
JOIN courses c ON c.course_id = e.course_id
WHERE c.code = 'CS101'
EXCEPT
SELECT e2.student_id
FROM enrollments e2
JOIN courses c2 ON c2.course_id = e2.course_id
WHERE c2.code = 'MATH101';
```
**Why:** First set is students in CS101, EXCEPT students in MATH101 gives those in CS101 but not MATH101.

### Exercise 5
**Answer:** Employee-manager: each employee has a manager who is also an employee. A SELF JOIN on `employees(employee_id, manager_id)` shows each employee with their manager's name.

**Why:** Hierarchical relationships (org charts, categories with parents) map naturally to SELF JOINs.

### Exercise 6
**Answer:** 1NF: atomic values (no comma lists). 2NF: no partial dependencies on a composite key. 3NF: no transitive dependencies (non-key facts depend only on the key). In our model, `students` stores name/email by student_id (3NF); enrollments links keys; no duplicated student details appear in enrollments.

**Why:** Normalization reduces update anomalies while keeping data consistent.
