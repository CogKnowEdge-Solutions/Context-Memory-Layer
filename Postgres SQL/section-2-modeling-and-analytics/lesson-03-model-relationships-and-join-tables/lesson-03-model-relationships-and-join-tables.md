# Model Relationships and Join Tables
## 1. What are Relationships and Joins?

Relational databases organize data into tables that relate to one another. A *relationship* links rows in different tables (for example, which students are enrolled in which courses). A *join* brings those related rows together in a single result.

- **Tables and keys:** Each table has a primary key (one row, one identity). Foreign keys point from one table to another to keep links valid.
- **Types of relationships:** One-to-many (a course has many enrollments), many-to-many (students and courses via a junction table), and self-references (a course may have a prerequisite course).
- **Joins:** Combine matching rows from related tables. Set operations combine entire result sets.
- **Normalization:** Organize data to reduce duplication (1NF to 3NF). Denormalization trades a little duplication for simpler or faster queries when it makes sense.

**Everyday example:** Think of a university: students and courses are separate lists. An "enrollments" card links a student to a course — that's a many-to-many relationship, and a join shows "who is taking what".

```mermaid
graph LR
  S[Students] -->|enrollments (many-to-many)| C[Courses]
  E[Enrollments] --> S
  E --> C
  style S fill:#e1f5ff,stroke:#0288d1,color:#01579b
  style C fill:#ffe0b2,stroke:#ef6c00,color:#7f3f00
  style E fill:#fff9c4,stroke:#f9a825,color:#7f6000
```

## 2. Problem Statement / Use Case Overview

You need to model how students, courses, and enrollments relate, enforce valid links with foreign keys, and answer questions like "Who is taking which course and what grade?" using joins and set operations. You also learn the basics of normalization, denormalization, and common anti-patterns.

In this lesson you build a small normalized model, add relationships, and practice INNER/LEFT/RIGHT/FULL/CROSS and SELF joins, plus UNION/INTERSECT/EXCEPT.

## 3. Input

Sample data for a tiny university:

- **students** (student_id, name, email) — 3 students
- **courses** (course_id, code, title, credits) — 3 courses
- **enrollments** (enrollment_id, student_id, course_id, grade) — links students to courses

All defined inside the notebook so the lesson stays self-contained.

## 4. Processing

```mermaid
flowchart LR
  A[Create normalized tables with FKs] --> B[Load sample data]
  B --> C[Practice joins: INNER/LEFT/RIGHT/FULL/CROSS/SELF]
  C --> D[Practice set ops: UNION/INTERSECT/EXCEPT]
  D --> E[Combined report]
  style A fill:#e1f5ff,stroke:#0288d1,color:#01579b
  style B fill:#fff9c4,stroke:#f9a825,color:#7f6000
  style C fill:#ffe0b2,stroke:#ef6c00,color:#7f3f00
  style D fill:#c8e6c9,stroke:#2e7d32,color:#1b5e20
  style E fill:#f3e5f5,stroke:#6a1b9a,color:#4a148c
```

## 5. Output

The combined report shows each student and the courses they take (including students with no enrollments):

```\n\n```

## 6. Tech Stack

| Tool | Version | Role |
|------|---------|------|
| PostgreSQL | 18 | Database |
| psycopg | 3.3.6 | Python driver |
| python-dotenv | 1.2.4 | Loads `.env` |
| Jupyter | any recent version | Runs the notebook |

**Compute and cost:** Runs on a laptop CPU with minimal memory. No GPU, cloud account, or paid service required.

## 7. Underlying Concepts

**Foreign keys and referential integrity.** A foreign key (FK) makes sure a value in one table points to a valid row in another. `ON DELETE RESTRICT` prevents deleting a referenced row if dependents exist; `ON DELETE CASCADE` would remove dependents too. *Everyday example:* you can't delete a course if students are still enrolled in it.

**Normalization (1NF to 3NF).** 1NF: atomic values, no repeating groups. 2NF: no partial dependencies on a composite key. 3NF: no transitive dependencies. The goal is to reduce duplication and anomalies. *Everyday example:* storing student details once in `students` instead of repeating them on every enrollment.

**Denormalization and anti-patterns.** Denormalization intentionally duplicates data (e.g., store a name in enrollments) to speed reads for specific queries — but it makes updates harder and error-prone. Common anti-patterns: storing comma-separated lists (breaks 1NF), or putting derived/calculated values without a reason. *Everyday example:* caching a product name on an order line can save a join, but if the name changes you must update many rows.

**Joins.** `INNER JOIN`: only matching rows. `LEFT JOIN`: all left rows, NULLs if no match. `RIGHT JOIN`: all right rows. `FULL OUTER JOIN`: all rows from both. `CROSS JOIN`: all pairs. `SELF JOIN`: join a table to itself (hierarchies like prerequisites). *Everyday example:* "show me every student and the courses they take" uses a LEFT JOIN if you want students with no enrollments too.

**Set operations.** `UNION` combines results and removes duplicates; `UNION ALL` keeps them. `INTERSECT` returns rows in both. `EXCEPT` (or `MINUS`) returns rows in the first but not the second. *Everyday example:* students taking CS101 UNION students taking MATH101 gives everyone taking either; INTERSECT gives those taking both.

**Entity-Relationship (ER) intuition.** Entities (students, courses) become tables; relationships become FKs or junction tables. *Everyday example:* drawing boxes and lines on a whiteboard maps cleanly to tables and foreign keys.

## 8. Prerequisites

- Basic SQL from lesson 1 and 2 (SELECT, WHERE, INSERT, constraints).
- A running PostgreSQL server (version 18) and the `.env` file at the course root.
- Familiarity with Python/notebook basics.

## 9. Environment / Dependencies Setup

All connection settings live in the global `.env` at the course root. Every notebook loads it with `load_dotenv("../../.env")`, so start Jupyter from inside this lesson folder.

Install packages:
```
pip install "psycopg[binary]==3.3.6" "python-dotenv==1.2.4"
```

## 10. Step-wise Development Instructions

### Step 1 — Model tables with foreign keys

```python
# Step 1: Model tables with foreign keys
conn.execute("DROP TABLE IF EXISTS enrollments")
conn.execute("DROP TABLE IF EXISTS courses")
conn.execute("DROP TABLE IF EXISTS students")

conn.execute("""CREATE TABLE students (
    student_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE
)""")
conn.execute("""CREATE TABLE courses (
    course_id TEXT PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    credits INTEGER NOT NULL CHECK (credits > 0)
)""")
conn.execute("""CREATE TABLE enrollments (
    enrollment_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_id TEXT NOT NULL REFERENCES students(student_id) ON DELETE RESTRICT,
    course_id TEXT NOT NULL REFERENCES courses(course_id) ON DELETE RESTRICT,
    grade INTEGER CHECK (grade BETWEEN 0 AND 100),
    UNIQUE (student_id, course_id)
)""")
conn.commit()
print("tables created")
```

Creates normalized tables with primary keys, foreign keys (`ON DELETE RESTRICT`), `UNIQUE`, and `CHECK`. The junction `enrollments` represents a many-to-many between students and courses. Foreign keys are not automatically indexed in PostgreSQL — add indexes if needed for performance.

### Step 1b — Foreign keys in action (failures)

```python
# Step 1b: FK demo - failing insert and blocked delete
try:
    conn.execute("INSERT INTO enrollments (student_id, course_id) VALUES ('NOPE','C001')")
    conn.commit()
except Exception as e:
    conn.rollback()
    print("FK insert failed as expected")

try:
    conn.execute("INSERT INTO students VALUES ('STU001','Alice Johnson','alice@univ.example')")
    conn.execute("INSERT INTO courses VALUES ('C001','CS101','Intro to CS',3)")
    conn.execute("INSERT INTO enrollments (student_id,course_id,grade) VALUES ('STU001','C001',95)")
    conn.commit()
    conn.execute("DELETE FROM courses WHERE course_id='C001'")
    conn.commit()
    print("delete happened")
except Exception as e:
    conn.rollback()
    print("FK delete blocked as expected (ON DELETE RESTRICT)")
```

Library card analogy: you cannot enroll a student who does not exist (failing insert). You cannot delete a course that has enrollments (blocked delete) when using `ON DELETE RESTRICT`.

### Step 2 — Load sample data

```python
# Step 2: insert sample data (include student with no enrollment, course with no students)
conn.execute("INSERT INTO students VALUES ('STU002','Bob Smith','bob@univ.example'),('STU003','Charlie Brown','charlie@univ.example'),('STU004','Dana Lee',NULL)")
conn.execute("INSERT INTO courses VALUES ('C002','MATH101','Calculus I',4),('C003','ENG101','Writing',3)")
conn.execute("INSERT INTO enrollments (student_id,course_id,grade) VALUES ('STU002','C002',88),('STU003','C002',91)")
conn.commit()
show("SELECT * FROM students ORDER BY student_id")
show("SELECT * FROM courses ORDER BY course_id")
show("SELECT * FROM enrollments ORDER BY enrollment_id")
```

Loads sample data. STU004 has no enrollments; ENG101 (C003) has no students — so outer joins will differ. The junction table links students and courses.

**Output:**

```
Connecting to postgres@localhost:5432/university (sslmode=prefer)
```

### Step 3 — INNER JOIN

```python
# Step 3: INNER JOIN — only matches
show("""
  SELECT s.student_id, s.name, c.code, c.title, e.grade
  FROM enrollments e
  INNER JOIN students s ON s.student_id = e.student_id
  INNER JOIN courses c ON c.course_id = e.course_id
  ORDER BY s.student_id, c.code
""")
```

`INNER JOIN` returns only rows that match in all joined tables. Row count shown below reflects matches only.

**Output:**

```
db ready
```

### Step 4 — LEFT JOIN (unmatched preserved)

```python
# Step 4: LEFT JOIN — all students
show("""
  SELECT s.student_id, s.name, c.code, e.grade
  FROM students s
  LEFT JOIN enrollments e ON e.student_id = s.student_id
  LEFT JOIN courses c ON c.course_id = e.course_id
  ORDER BY s.student_id
""")
```

`LEFT JOIN` keeps all rows from the left table (`students`); unmatched right-side values become `NULL`. STU004 appears with NULLs.

**Output:**

```
connected
```

### Step 5 — RIGHT and FULL OUTER JOIN

```python
# Step 5: RIGHT JOIN and FULL OUTER JOIN
show("""
  SELECT s.name, c.code
  FROM enrollments e
  RIGHT JOIN students s ON s.student_id = e.student_id
  ORDER BY s.student_id
""")
show("""
  SELECT s.name, c.code
  FROM courses c
  LEFT JOIN enrollments e ON e.course_id = c.course_id
  LEFT JOIN students s ON s.student_id = e.student_id
  ORDER BY c.code, s.name
""")
```

`RIGHT JOIN` keeps all right-side rows; `FULL OUTER JOIN` keeps rows from both sides. Here we also show courses with no students.

**Output:**

```
current_database
----------------
university      
(1 rows)
```

### Step 6 — CROSS JOIN

```python
# Step 6: CROSS JOIN
show("""
  SELECT s.name, c.code
  FROM students s CROSS JOIN courses c
  ORDER BY s.name, c.code
""")
```

`CROSS JOIN` produces the Cartesian product (all pairs).

**Output:**

```
tables created
```

### Step 7 — SELF JOIN

```python
# Step 7: SELF JOIN
show("""
  SELECT c.code AS course, p.code AS prereq
  FROM courses c
  LEFT JOIN courses p ON p.course_id = c.prerequisite
  ORDER BY c.code
""")
```

A `SELF JOIN` joins a table to itself to represent hierarchical relationships like prerequisites.

**Output:**

```
student_id |      name     |        email        
-----------+---------------+---------------------
STU001     | Alice Johnson | alice@univ.example  
STU002     | Bob Smith     | bob@univ.example    
STU003     | Charlie Brown | charlie@univ.example
STU004     | Dana Lee      | NULL                
(4 rows)
course_id |   code  |    title    | credits
----------+---------+-------------+--------
C001      | CS101   | Intro to CS |       3
C002      | MATH101 | Calculus I  |       4
C003      | ENG101  | Writing     |       3
(3 rows)
enrollment_id | student_id | course_id | grade
--------------+------------+-----------+------
            1 | STU001     | C001      |    95
            2 | STU001     | C002      |    88
            3 | STU002     | C001      |    72
            4 | STU003     | C002      |    91
(4 rows)
```

### Cleanup — Close the connection

```python
# Cleanup
conn.close()
print("connection closed")
```

Closes the connection. The tables and rules remain in the database.

**Output:**

```
student_id |      name     |   code  |    title    | grade
-----------+---------------+---------+-------------+------
STU001     | Alice Johnson | CS101   | Intro to CS |    95
STU001     | Alice Johnson | MATH101 | Calculus I  |    88
STU002     | Bob Smith     | CS101   | Intro to CS |    72
STU003     | Charlie Brown | MATH101 | Calculus I  |    91
(4 rows)
```

## 11. What We Learnt

- **Modeling:** Primary keys, foreign keys, and a junction table capture many-to-many cleanly.
- **Referential integrity:** `ON DELETE RESTRICT` keeps links valid; `UNIQUE` and `CHECK` enforce rules.
- **Normalization:** 1NF–3NF reduce duplication; denormalization trades duplication for convenience when justified.
- **Joins:** `INNER`, `LEFT`, `RIGHT`, `FULL OUTER`, `CROSS`, and `SELF` each serve different questions.
- **Set operations:** `UNION`, `INTERSECT`, and `EXCEPT` combine result sets.
- **Practical reports:** Combining joins and aggregates turns relationships into answers.
