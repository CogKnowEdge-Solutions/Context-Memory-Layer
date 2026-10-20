BLOCKS = []
def block(code, explain, heading=""):
    BLOCKS.append({"heading": heading, "code": code.strip("\n"), "explain": explain.strip("\n")})
block('''# Step 1: Model tables with foreign keys
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
      """Creates normalized tables with primary keys, foreign keys (`ON DELETE RESTRICT`), `UNIQUE`, and `CHECK`. The junction `enrollments` represents a many-to-many between students and courses. Foreign keys are not automatically indexed in PostgreSQL — add indexes if needed for performance.""",
      heading="### Step 1 — Model tables with foreign keys")

block('''# Step 1b: FK demo - failing insert and blocked delete
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
    print("FK delete blocked as expected (ON DELETE RESTRICT)")''',
      """Library card analogy: you cannot enroll a student who does not exist (failing insert). You cannot delete a course that has enrollments (blocked delete) when using `ON DELETE RESTRICT`.""",
      heading="### Step 1b — Foreign keys in action (failures)")

block('''# Step 2: insert sample data (include student with no enrollment, course with no students)
conn.execute("INSERT INTO students VALUES ('STU002','Bob Smith','bob@univ.example'),('STU003','Charlie Brown','charlie@univ.example'),('STU004','Dana Lee',NULL)")
conn.execute("INSERT INTO courses VALUES ('C002','MATH101','Calculus I',4),('C003','ENG101','Writing',3)")
conn.execute("INSERT INTO enrollments (student_id,course_id,grade) VALUES ('STU002','C002',88),('STU003','C002',91)")
conn.commit()
show("SELECT * FROM students ORDER BY student_id")
show("SELECT * FROM courses ORDER BY course_id")
show("SELECT * FROM enrollments ORDER BY enrollment_id")''',
      """Loads sample data. STU004 has no enrollments; ENG101 (C003) has no students — so outer joins will differ. The junction table links students and courses.""",
      heading="### Step 2 — Load sample data")

block('''# Step 3: INNER JOIN — only matches
show("""
  SELECT s.student_id, s.name, c.code, c.title, e.grade
  FROM enrollments e
  INNER JOIN students s ON s.student_id = e.student_id
  INNER JOIN courses c ON c.course_id = e.course_id
  ORDER BY s.student_id, c.code
""")''',
      """`INNER JOIN` returns only rows that match in all joined tables. Row count shown below reflects matches only.""",
      heading="### Step 3 — INNER JOIN")

block('''# Step 4: LEFT JOIN — all students
show("""
  SELECT s.student_id, s.name, c.code, e.grade
  FROM students s
  LEFT JOIN enrollments e ON e.student_id = s.student_id
  LEFT JOIN courses c ON c.course_id = e.course_id
  ORDER BY s.student_id
""")''',
      """`LEFT JOIN` keeps all rows from the left table (`students`); unmatched right-side values become `NULL`. STU004 appears with NULLs.""",
      heading="### Step 4 — LEFT JOIN (unmatched preserved)")

block('''# Step 5: RIGHT JOIN and FULL OUTER JOIN
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
""")''',
      """`RIGHT JOIN` keeps all right-side rows; `FULL OUTER JOIN` keeps rows from both sides. Here we also show courses with no students.""",
      heading="### Step 5 — RIGHT and FULL OUTER JOIN")

block('''# Step 6: CROSS JOIN
show("""
  SELECT s.name, c.code
  FROM students s CROSS JOIN courses c
  ORDER BY s.name, c.code
""")''',
      """`CROSS JOIN` produces the Cartesian product (all pairs).""",
      heading="### Step 6 — CROSS JOIN")

block('''# Step 7: SELF JOIN
show("""
  SELECT c.code AS course, p.code AS prereq
  FROM courses c
  LEFT JOIN courses p ON p.course_id = c.prerequisite
  ORDER BY c.code
""")''',
      """A `SELF JOIN` joins a table to itself to represent hierarchical relationships like prerequisites.""",
      heading="### Step 7 — SELF JOIN")
block('''# Cleanup
conn.close()
print("connection closed")''',
      """Closes the connection. The tables and rules remain in the database.""",
      heading="### Cleanup — Close the connection")
