# Create Tables and Query Data — Assignment

## Exercises

### Exercise 1 — Rows and columns
The `students` table holds 25 students. In Structured Query Language (SQL), what is a *row* and what is a *column*? Give one example of each from the lesson's data.

### Exercise 2 — Read and sort
Write a query that returns the `name` and `grade` of every active student, with the highest grade first.

### Exercise 3 — The order SELECT runs in
Explain why you can use an alias you defined in `SELECT` inside `ORDER BY`, but not inside `WHERE`.

### Exercise 4 — The missing email
A student's `email` can be `NULL`. Why does `WHERE email = NULL` return no rows, and what should you write instead? Then write the query that lists the students who have no email, ordered by `student_id`.

### Exercise 5 — Labelling rows
Write a query that shows each student's `name` and `grade`, plus a column called `honor` that is `'yes'` when the grade is 90 or above and `'no'` otherwise. Sort the highest grade first.

### Exercise 6 — A friendly default
Write a query that returns every student's `name` and a `contact` column that shows the student's email when there is one, and the text `'no email on file'` when there is not. Order by `student_id`.

### Exercise 7 — Combining filters
Write one query that returns the `name` and `course` of students who are in Biology or Physics, are `active`, and scored between 60 and 80 inclusive. Sort by `course`, then by `name`.

### Exercise 8 — Why parameters
Why does the lesson pass values with `%s` placeholders instead of building the query text with an f-string? Give one short example of what could go wrong with an f-string.

## Answer Key

### Exercise 1
**Answer:** A *row* is one thing — here, one student, such as the row for `STU001` (Alice Johnson). A *column* is one fact about every row, such as `grade` (every student has a grade). 

**Why:** The relational model stores one entity per row and one attribute per column. Keeping those two ideas separate is what makes it possible to add a new student without disturbing the others.

### Exercise 2
**Answer:**
```python
show("""
    SELECT name, grade
    FROM students
    WHERE status = 'active'
    ORDER BY grade DESC, student_id
""")
```
**Why:** `WHERE` keeps only the active rows, and `ORDER BY grade DESC` sorts from the highest grade to the lowest. The second sort key (`student_id`) makes ties come out in the same order every time.

### Exercise 3
**Answer:** PostgreSQL runs the parts of a query in the order `FROM`, then `WHERE`, then `SELECT`, then `ORDER BY`. The alias is created during `SELECT`, so it exists by the time `ORDER BY` runs — but `WHERE` runs before `SELECT`, so the alias does not exist yet.

**Why:** This is the logical order of evaluation explained in Section 7. It also explains why `WHERE` must use the real column name (`grade`), not its alias (`score`).

### Exercise 4
**Answer:** `email = NULL` compares against the value "unknown", which is never true, so `WHERE` drops every row. Use `IS NULL` instead:
```python
show("SELECT student_id, name FROM students WHERE email IS NULL ORDER BY student_id")
```
**Why:** SQL uses three-valued logic (true, false, unknown), and `WHERE` keeps only the rows that are true. `IS NULL` is the test that asks the real question, "is this value missing?".

### Exercise 5
**Answer:**
```python
show("""
    SELECT name, grade,
           CASE WHEN grade >= 90 THEN 'yes' ELSE 'no' END AS honor
    FROM students
    ORDER BY grade DESC, student_id
""")
```
**Why:** `CASE` checks the condition for each row and returns the matching value, adding a new column to the result without changing the stored data.

### Exercise 6
**Answer:**
```python
show("SELECT name, COALESCE(email, 'no email on file') AS contact FROM students ORDER BY student_id")
```
**Why:** `COALESCE` returns the first value that is not `NULL`, so it shows the email when one exists and the fallback text when it does not.

### Exercise 7
**Answer:**
```python
show("""
    SELECT name, course
    FROM students
    WHERE course IN ('Biology', 'Physics')
      AND status = 'active'
      AND grade BETWEEN 60 AND 80
    ORDER BY course, name
""")
```
**Why:** `IN (...)` matches either course in one condition, and `BETWEEN 60 AND 80` includes both endpoints, so a grade of exactly 60 or 80 counts. Sorting by `course` then `name` groups the results by course.

### Exercise 8
**Answer:** Parameters keep the values separate from the SQL text, so a value can never be read as a command. With an f-string, a value such as `"x'; DROP TABLE students; --"` would be pasted straight into the query and could end the statement early and run the extra command.

**Why:** Splitting the query text from its values is how we avoid SQL injection — the trick of hiding commands inside data (covered in Step 5).
