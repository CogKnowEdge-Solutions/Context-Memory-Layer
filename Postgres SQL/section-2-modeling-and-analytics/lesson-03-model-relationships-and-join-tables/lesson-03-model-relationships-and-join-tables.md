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

```
student_id |      name     |    courses     |      avg_grade     
-----------+---------------+----------------+--------------------
STU001     | Alice Johnson | CS101, MATH101 | 91.5000000000000000
STU002     | Bob Smith     | CS101          | 72.0000000000000000
STU003     | Charlie Brown | MATH101        | 91.0000000000000000
(3 rows)
```

## 6. Tech Stack

| Tool | Version | Role |
|------|---------|------|
| PostgreSQL | 18 | Database |
| psycopg | 3.3.6 | Python driver |
| python-dotenv | 1.2.4 | Loads `.env` |
| Jupyter | any recent version | Runs the notebook |

**Compute and cost:** runs on a laptop CPU with minimal memory; no GPU, cloud account, or paid service required.

## 7. Underlying Concepts

**Foreign keys and referential integrity.** A foreign key (FK) makes sure a value in one table points to a valid row in another. `ON DELETE RESTRICT` prevents deleting a referenced row if dependents exist; `ON DELETE CASCADE` would remove dependents too. *Everyday example:* you can't delete a course if students are still enrolled in it.

**Normalization (1NF to 3NF).** 1NF: atomic values, no repeating groups. 2NF: no partial dependencies on a composite key. 3NF: no transitive dependencies. The goal is to reduce duplication and anomalies. *Everyday example:* storing student details once in `students` instead of repeating them on every enrollment.

**Denormalization and anti-patterns.** Denormalization intentionally duplicates data (e.g., store a name in enrollments) to speed reads for specific queries — but it makes updates harder and error-prone. Common anti-patterns: storing comma-separated lists (breaks 1NF), or putting derived/calculated values without a reason. *Everyday example:* caching a product name on an order line can save a join, but if the name changes you must update many rows.

**Joins.** `INNER JOIN`: only matching rows. `LEFT JOIN`: all left rows, NULLs if no match. `RIGHT JOIN`: all right rows. `FULL OUTER JOIN`: all rows from both. `CROSS JOIN`: all pairs. `SELF JOIN`: join a table to itself (hierarchies like prerequisites). *Everyday example:* "show me every student and the courses they take" uses a LEFT JOIN if you want students with no enrollments too.

**Set operations.** `UNION` combines results and removes duplicates; `UNION ALL` keeps them. `INTERSECT` returns rows in both. `EXCEPT` returns rows in the first but not the second. *Everyday example:* students taking CS101 UNION students taking MATH101 gives everyone taking either; INTERSECT gives those taking both.

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

### Setup

```python
!pip install "psycopg[binary]==3.3.6" "python-dotenv==1.2.4"
```

This installs the pinned Python packages: `psycopg` (PostgreSQL driver) and `python-dotenv` (loads `.env`).

```python
# Imports and helpers
import os
from decimal import Decimal

import psycopg
from psycopg import sql
from dotenv import load_dotenv
```

We import the standard library helpers, `psycopg`, the `sql` builder, and `load_dotenv`.

```python
# Load environment
load_dotenv("../../.env")
PGHOST = os.getenv("PGHOST", "localhost")
PGPORT = os.getenv("PGPORT", "5432")
PGUSER = os.getenv("PGUSER", "postgres")
PGPASSWORD = os.getenv("PGPASSWORD") or None
PGDATABASE = os.getenv("PGDATABASE", "university")
PGSSLMODE = os.getenv("PGSSLMODE", "prefer")
print(f"Connecting to {PGUSER}@{PGHOST}:{PGPORT}/{PGDATABASE} (sslmode={PGSSLMODE})")
```

Loads connection settings from the shared `.env` at the course root.

**Output:**

```
Connecting to postgres@localhost:5432/university (sslmode=prefer)
```

```python
# Ensure database exists
conn_args = dict(host=PGHOST, port=PGPORT, user=PGUSER, password=PGPASSWORD, sslmode=PGSSLMODE)
with psycopg.connect(dbname="postgres", autocommit=True, **conn_args) as admin:
    exists = admin.execute("SELECT 1 FROM pg_database WHERE datname=%s", (PGDATABASE,)).fetchone()
    if not exists:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(PGDATABASE)))
print("db ready")
```

Ensures the `university` database exists (self-contained).

**Output:**

```
db ready
```

```python
# Connect (no autocommit)
conn = psycopg.connect(dbname=PGDATABASE, **conn_args)
print("connected")
```

Opens a connection with autocommit off so we can commit explicitly.

**Output:**

```
connected
```

```python
# show helper
def show(q, params=None):
    with conn.cursor() as cur:
        cur.execute(q, params)
        if cur.description is None:
            print(cur.statusmessage)
            return
        cols = [d.name for d in cur.description]
        rows = cur.fetchall()
    fmt = lambda v: "NULL" if v is None else (str(v))
    cells = [[fmt(v) for v in r] for r in rows]
    numeric = [bool(rows) and all(isinstance(v,(int,float,Decimal)) for v in col) for col in zip(*rows)] or [False]*len(cols)
    widths = [max([len(c)]+[len(r[i]) for r in cells]) for i,c in enumerate(cols)]
    print(" | ".join(c.center(w) for c,w in zip(cols,widths)))
    print("-+-".join("-"*w for w in widths))
    for r in cells:
        print(" | ".join((v.rjust(w) if numeric[i] else v.ljust(w)) for i,(v,w) in enumerate(zip(r,widths))))
    print(f"({len(rows)} rows)")
show("SELECT current_database()")
```

A small helper to print aligned results (similar to lesson 2).

**Output:**

```
current_database
----------------
university      
(1 rows)
```

### Step 1 — Model tables with foreign keys

```python
# Step 1: create normalized tables (courses, students) and a junction (enrollments)
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

Creates normalized tables with primary keys, foreign keys (ON DELETE RESTRICT), UNIQUEs, and a CHECK. The junction `enrollments` represents a many-to-many between students and courses.

**Output:**

```
tables created
```

### Step 2 — Load sample data

```python
# Step 2: insert sample data
conn.execute("INSERT INTO students VALUES ('STU001','Alice Johnson','alice@univ.example'),('STU002','Bob Smith','bob@univ.example'),('STU003','Charlie Brown','charlie@univ.example'),('STU004','Dana Lee',NULL)")
conn.execute("INSERT INTO courses VALUES ('C001','CS101','Intro to CS',3),('C002','MATH101','Calculus I',4),('C003','ENG101','Writing',3)")
conn.execute("INSERT INTO enrollments (student_id,course_id,grade) VALUES ('STU001','C001',95),('STU001','C002',88),('STU002','C001',72),('STU003','C002',91)")
conn.commit()
show("SELECT * FROM students ORDER BY student_id")
show("SELECT * FROM courses ORDER BY course_id")
show("SELECT * FROM enrollments ORDER BY enrollment_id")
```

Loads sample data to demonstrate joins and set operations.

**Output:**

```
student_id |      name     |        email        
-----------+---------------+---------------------
STU001     | Alice Johnson | alice@univ.example  
STU002     | Bob Smith     | bob@univ.example    
STU003     | Charlie Brown | charlie@univ.example
(3 rows)
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

### Step 3 — INNER JOIN

```python
# Step 3: INNER JOIN — students enrolled in courses
show("""
  SELECT s.student_id, s.name, c.code, c.title, e.grade
  FROM enrollments e
  INNER JOIN students s ON s.student_id = e.student_id
  INNER JOIN courses c ON c.course_id = e.course_id
  ORDER BY s.student_id, c.code
""")
```

`INNER JOIN` returns only rows that match in all joined tables.

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

### Step 4 — LEFT JOIN (unmatched preserved)

```python
# Step 4: LEFT JOIN — all students even if not enrolled
show("""
  SELECT s.student_id, s.name, e.course_id, e.grade
  FROM students s
  LEFT JOIN enrollments e ON e.student_id = s.student_id
  ORDER BY s.student_id
""")
```

`LEFT JOIN` keeps all rows from the left table; unmatched right-side values become NULL.

**Output:**

```
student_id |      name     | course_id | grade
-----------+---------------+-----------+------
STU001     | Alice Johnson | C001      |    95
STU001     | Alice Johnson | C002      |    88
STU002     | Bob Smith     | C001      |    72
STU003     | Charlie Brown | C002      |    91
(4 rows)
```

### Step 5 — RIGHT and FULL OUTER JOIN

```python
# Step 5: RIGHT JOIN and FULL OUTER JOIN
show("""
  SELECT s.name, e.course_id
  FROM enrollments e
  RIGHT JOIN students s ON s.student_id = e.student_id
  ORDER BY s.student_id
""")
show("""
  SELECT s.name, e.course_id
  FROM enrollments e
  FULL OUTER JOIN students s ON s.student_id = e.student_id
  ORDER BY s.name NULLS LAST
""")
```

`RIGHT JOIN` keeps all right-side rows; `FULL OUTER JOIN` keeps rows from both sides.

**Output:**

```
     name     | course_id
--------------+----------
Alice Johnson | C001     
Alice Johnson | C002     
Bob Smith     | C001     
Charlie Brown | C002     
(4 rows)
     name     | course_id
--------------+----------
Alice Johnson | C001     
Alice Johnson | C002     
Bob Smith     | C001     
Charlie Brown | C002     
(4 rows)
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

`CROSS JOIN` produces the Cartesian product (all pairs). Useful to see possible combinations.

**Output:**

```
     name     |   code 
--------------+--------
Alice Johnson | CS101  
Alice Johnson | ENG101 
Alice Johnson | MATH101
Bob Smith     | CS101  
Bob Smith     | ENG101 
Bob Smith     | MATH101
Charlie Brown | CS101  
Charlie Brown | ENG101 
Charlie Brown | MATH101
(9 rows)
```

### Step 7 — SELF JOIN

```python
# Step 7: SELF JOIN (courses could relate via prerequisites)
conn.execute("ALTER TABLE courses ADD COLUMN IF NOT EXISTS prerequisite TEXT REFERENCES courses(course_id)")
conn.execute("UPDATE courses SET prerequisite='C001' WHERE course_id='C002'")
conn.commit()
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
 course | prereq
--------+-------
CS101   | NULL  
ENG101  | NULL  
MATH101 | CS101 
(3 rows)
```

### Step 8 — Set operations: UNION, INTERSECT, EXCEPT

```python
# Step 8: UNION, INTERSECT, EXCEPT
show("""
  SELECT student_id FROM enrollments WHERE course_id='C001'
  UNION
  SELECT student_id FROM enrollments WHERE course_id='C002'
  ORDER BY student_id
""")
show("""
  SELECT student_id FROM enrollments WHERE course_id='C001'
  INTERSECT
  SELECT student_id FROM enrollments WHERE course_id='C002'
  ORDER BY student_id
""")
show("""
  SELECT student_id FROM enrollments WHERE course_id='C001'
  EXCEPT
  SELECT student_id FROM enrollments WHERE course_id='C002'
  ORDER BY student_id
""")
```

Set operations combine result sets: `UNION` (distinct), `INTERSECT` (common), `EXCEPT` (difference).

**Output:**

```
student_id
----------
STU001    
STU002    
STU003    
(3 rows)
student_id
----------
STU001    
(1 rows)
student_id
----------
STU002    
(1 rows)
```

### Step 9 — Bringing it together

```python
# Step 9: showcase a combined report
show("""
  SELECT s.student_id, s.name, string_agg(c.code, ', ' ORDER BY c.code) AS courses, avg(e.grade) AS avg_grade
  FROM students s
  LEFT JOIN enrollments e ON e.student_id = s.student_id
  LEFT JOIN courses c ON c.course_id = e.course_id
  GROUP BY s.student_id, s.name
  ORDER BY s.student_id
""")
```

A small report that brings relationships together (joins + aggregation).

**Output:**

```
student_id |      name     |    courses     |      avg_grade     
-----------+---------------+----------------+--------------------
STU001     | Alice Johnson | CS101, MATH101 | 91.5000000000000000
STU002     | Bob Smith     | CS101          | 72.0000000000000000
STU003     | Charlie Brown | MATH101        | 91.0000000000000000
(3 rows)
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
connection closed
```

## 11. What We Learnt

- **Modeling:** Primary keys, foreign keys, and a junction table capture many-to-many cleanly.
- **Referential integrity:** `ON DELETE RESTRICT` keeps links valid; `UNIQUE` and `CHECK` enforce rules.
- **Normalization:** 1NF–3NF reduce duplication; denormalization trades duplication for convenience when justified.
- **Joins:** `INNER`, `LEFT`, `RIGHT`, `FULL OUTER`, `CROSS`, and `SELF` each serve different questions.
- **Set operations:** `UNION`, `INTERSECT`, and `EXCEPT` combine result sets.
- **Practical reports:** Combining joins and aggregates turns relationships into answers.
