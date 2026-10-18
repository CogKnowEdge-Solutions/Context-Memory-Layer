"""Lesson 3 blocks: relationships and joins."""

BLOCKS = []

def block(code, explain, heading=""):
    BLOCKS.append({"heading": heading, "code": code.strip("\n"), "explain": explain.strip("\n")})


# Setup
block(
    '''!pip install "psycopg[binary]==3.3.6" "python-dotenv==1.2.4"''',
    """This installs the pinned Python packages: `psycopg` (PostgreSQL driver) and `python-dotenv` (loads `.env`).""",
    heading="### Setup",
)
block(
    '''# Imports and helpers
import os
from decimal import Decimal

import psycopg
from psycopg import sql
from dotenv import load_dotenv''',
    """We import the standard library helpers, `psycopg`, the `sql` builder, and `load_dotenv`."""
)
block(
    '''# Load environment
load_dotenv("../../.env")
PGHOST = os.getenv("PGHOST", "localhost")
PGPORT = os.getenv("PGPORT", "5432")
PGUSER = os.getenv("PGUSER", "postgres")
PGPASSWORD = os.getenv("PGPASSWORD") or None
PGDATABASE = os.getenv("PGDATABASE", "university")
PGSSLMODE = os.getenv("PGSSLMODE", "prefer")
print(f"Connecting to {PGUSER}@{PGHOST}:{PGPORT}/{PGDATABASE} (sslmode={PGSSLMODE})")''',
    """Loads connection settings from the shared `.env` at the course root."""
)
block(
    '''# Ensure database exists
conn_args = dict(host=PGHOST, port=PGPORT, user=PGUSER, password=PGPASSWORD, sslmode=PGSSLMODE)
with psycopg.connect(dbname="postgres", autocommit=True, **conn_args) as admin:
    exists = admin.execute("SELECT 1 FROM pg_database WHERE datname=%s", (PGDATABASE,)).fetchone()
    if not exists:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(PGDATABASE)))
print("db ready")''',
    """Ensures the `university` database exists (self-contained)."""
)
block(
    '''# Connect (no autocommit)
conn = psycopg.connect(dbname=PGDATABASE, **conn_args)
print("connected")''',
    """Opens a connection with autocommit off so we can commit explicitly."""
)
block(
    '''# show helper
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
show("SELECT current_database()")''',
    """A small helper to print aligned results (similar to lesson 2)."""
)

# Step 1: model tables
block(
    '''# Step 1: create normalized tables (courses, students) and a junction (enrollments)
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
print("tables created")''',
    """Creates normalized tables with primary keys, foreign keys (ON DELETE RESTRICT), UNIQUEs, and a CHECK. The junction `enrollments` represents a many-to-many between students and courses.""",
    heading="### Step 1 — Model tables with foreign keys",
)
block(
    '''# Step 2: insert sample data
conn.execute("INSERT INTO students VALUES ('STU001','Alice Johnson','alice@univ.example'),('STU002','Bob Smith','bob@univ.example'),('STU003','Charlie Brown','charlie@univ.example')")
conn.execute("INSERT INTO courses VALUES ('C001','CS101','Intro to CS',3),('C002','MATH101','Calculus I',4),('C003','ENG101','Writing',3)")
conn.execute("INSERT INTO enrollments (student_id,course_id,grade) VALUES ('STU001','C001',95),('STU001','C002',88),('STU002','C001',72),('STU003','C002',91)")
conn.commit()
show("SELECT * FROM students ORDER BY student_id")
show("SELECT * FROM courses ORDER BY course_id")
show("SELECT * FROM enrollments ORDER BY enrollment_id")''',
    """Loads sample data to demonstrate joins and set operations.""",
    heading="### Step 2 — Load sample data",
)
block(
    '''# Step 3: INNER JOIN — students enrolled in courses
show("""
  SELECT s.student_id, s.name, c.code, c.title, e.grade
  FROM enrollments e
  INNER JOIN students s ON s.student_id = e.student_id
  INNER JOIN courses c ON c.course_id = e.course_id
  ORDER BY s.student_id, c.code
""")''',
    """`INNER JOIN` returns only rows that match in all joined tables.""",
    heading="### Step 3 — INNER JOIN",
)
block(
    '''# Step 4: LEFT JOIN — all students even if not enrolled
show("""
  SELECT s.student_id, s.name, e.course_id, e.grade
  FROM students s
  LEFT JOIN enrollments e ON e.student_id = s.student_id
  ORDER BY s.student_id
""")''',
    """`LEFT JOIN` keeps all rows from the left table; unmatched right-side values become NULL.""",
    heading="### Step 4 — LEFT JOIN (unmatched preserved)",
)
block(
    '''# Step 5: RIGHT JOIN and FULL OUTER JOIN
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
""")''',
    """`RIGHT JOIN` keeps all right-side rows; `FULL OUTER JOIN` keeps rows from both sides.""",
    heading="### Step 5 — RIGHT and FULL OUTER JOIN",
)
block(
    '''# Step 6: CROSS JOIN
show("""
  SELECT s.name, c.code
  FROM students s CROSS JOIN courses c
  ORDER BY s.name, c.code
""")''',
    """`CROSS JOIN` produces the Cartesian product (all pairs). Useful to see possible combinations.""",
    heading="### Step 6 — CROSS JOIN",
)
block(
    '''# Step 7: SELF JOIN (courses could relate via prerequisites)
conn.execute("ALTER TABLE courses ADD COLUMN prerequisite TEXT REFERENCES courses(course_id)")
conn.execute("UPDATE courses SET prerequisite='C001' WHERE course_id='C002'")
conn.commit()
show("""
  SELECT c.code AS course, p.code AS prereq
  FROM courses c
  LEFT JOIN courses p ON p.course_id = c.prerequisite
  ORDER BY c.code
""")''',
    """A `SELF JOIN` joins a table to itself to represent hierarchical relationships like prerequisites.""",
    heading="### Step 7 — SELF JOIN",
)
block(
    '''# Step 8: UNION, INTERSECT, EXCEPT
show("""
  SELECT student_id FROM enrollments WHERE course_id='C001'
  UNION
  SELECT student_id FROM enrollments WHERE course_id='C002'
""")
show("""
  SELECT student_id FROM enrollments WHERE course_id='C001'
  INTERSECT
  SELECT student_id FROM enrollments WHERE course_id='C002'
""")
show("""
  SELECT student_id FROM enrollments WHERE course_id='C001'
  EXCEPT
  SELECT student_id FROM enrollments WHERE course_id='C002'
""")''',
    """Set operations combine result sets: `UNION` (distinct), `INTERSECT` (common), `EXCEPT` (difference).""",
    heading="### Step 8 — Set operations: UNION, INTERSECT, EXCEPT",
)
block(
    '''# Step 9: showcase a combined report
show("""
  SELECT s.student_id, s.name, string_agg(c.code, ', ' ORDER BY c.code) AS courses, avg(e.grade) AS avg_grade
  FROM students s
  LEFT JOIN enrollments e ON e.student_id = s.student_id
  LEFT JOIN courses c ON c.course_id = e.course_id
  GROUP BY s.student_id, s.name
  ORDER BY s.student_id
""")''',
    """A small report that brings relationships together (joins + aggregation).""",
    heading="### Step 9 — Bringing it together",
)
block(
    '''# Cleanup
conn.close()
print("connection closed")''',
    """Closes the connection. The tables and rules remain in the database.""",
    heading="### Cleanup — Close the connection",
)
