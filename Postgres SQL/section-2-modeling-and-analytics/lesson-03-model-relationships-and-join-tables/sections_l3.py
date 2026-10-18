TITLE = "# Model Relationships and Join Tables"

SECTION1 = """## 1. What are Relationships and Joins?

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
"""

SECTION2 = """## 2. Problem Statement / Use Case Overview

You need to model how students, courses, and enrollments relate, enforce valid links with foreign keys, and answer questions like "Who is taking which course and what grade?" using joins and set operations. You also learn the basics of normalization, denormalization, and common anti-patterns.

In this lesson you build a small normalized model, add relationships, and practice INNER/LEFT/RIGHT/FULL/CROSS and SELF joins, plus UNION/INTERSECT/EXCEPT.
"""

SECTION3 = """## 3. Input

Sample data for a tiny university:

- **students** (student_id, name, email) — 3 students
- **courses** (course_id, code, title, credits) — 3 courses
- **enrollments** (enrollment_id, student_id, course_id, grade) — links students to courses

All defined inside the notebook so the lesson stays self-contained.
"""

SECTION4 = """## 4. Processing

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
"""

SECTION5_MARKER = "{{SECTION5}}"

SECTION6 = """## 6. Tech Stack

| Tool | Version | Role |
|------|---------|------|
| PostgreSQL | 18 | Database |
| psycopg | 3.3.6 | Python driver |
| python-dotenv | 1.2.4 | Loads `.env` |
| Jupyter | any recent version | Runs the notebook |

**Compute and cost:** Runs on a laptop CPU with minimal memory. No GPU, cloud account, or paid service required.
"""

SECTION7 = """## 7. Underlying Concepts

**Foreign keys and referential integrity.** A foreign key (FK) makes sure a value in one table points to a valid row in another. `ON DELETE RESTRICT` prevents deleting a referenced row if dependents exist; `ON DELETE CASCADE` would remove dependents too. *Everyday example:* you can't delete a course if students are still enrolled in it.

**Normalization (1NF to 3NF).** 1NF: atomic values, no repeating groups. 2NF: no partial dependencies on a composite key. 3NF: no transitive dependencies. The goal is to reduce duplication and anomalies. *Everyday example:* storing student details once in `students` instead of repeating them on every enrollment.

**Denormalization and anti-patterns.** Denormalization intentionally duplicates data (e.g., store a name in enrollments) to speed reads for specific queries — but it makes updates harder and error-prone. Common anti-patterns: storing comma-separated lists (breaks 1NF), or putting derived/calculated values without a reason. *Everyday example:* caching a product name on an order line can save a join, but if the name changes you must update many rows.

**Joins.** `INNER JOIN`: only matching rows. `LEFT JOIN`: all left rows, NULLs if no match. `RIGHT JOIN`: all right rows. `FULL OUTER JOIN`: all rows from both. `CROSS JOIN`: all pairs. `SELF JOIN`: join a table to itself (hierarchies like prerequisites). *Everyday example:* "show me every student and the courses they take" uses a LEFT JOIN if you want students with no enrollments too.

**Set operations.** `UNION` combines results and removes duplicates; `UNION ALL` keeps them. `INTERSECT` returns rows in both. `EXCEPT` (or `MINUS`) returns rows in the first but not the second. *Everyday example:* students taking CS101 UNION students taking MATH101 gives everyone taking either; INTERSECT gives those taking both.

**Entity-Relationship (ER) intuition.** Entities (students, courses) become tables; relationships become FKs or junction tables. *Everyday example:* drawing boxes and lines on a whiteboard maps cleanly to tables and foreign keys.
"""

SECTION8 = """## 8. Prerequisites

- Basic SQL from lesson 1 and 2 (SELECT, WHERE, INSERT, constraints).
- A running PostgreSQL server (version 18) and the `.env` file at the course root.
- Familiarity with Python/notebook basics.
"""

SECTION9 = """## 9. Environment / Dependencies Setup

All connection settings live in the global `.env` at the course root. Every notebook loads it with `load_dotenv("../../.env")`, so start Jupyter from inside this lesson folder.

Install packages:
```
pip install "psycopg[binary]==3.3.6" "python-dotenv==1.2.4"
```
"""

SECTION11 = """## 11. What We Learnt

- **Modeling:** Primary keys, foreign keys, and a junction table capture many-to-many cleanly.
- **Referential integrity:** `ON DELETE RESTRICT` keeps links valid; `UNIQUE` and `CHECK` enforce rules.
- **Normalization:** 1NF–3NF reduce duplication; denormalization trades duplication for convenience when justified.
- **Joins:** `INNER`, `LEFT`, `RIGHT`, `FULL OUTER`, `CROSS`, and `SELF` each serve different questions.
- **Set operations:** `UNION`, `INTERSECT`, and `EXCEPT` combine result sets.
- **Practical reports:** Combining joins and aggregates turns relationships into answers.
"""
