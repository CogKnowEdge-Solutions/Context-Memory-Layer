# MongoDB Mastery — Table of Contents

A hands-on MongoDB course in 7 sections and 10 labs, all built on one university/student domain and run against a free MongoDB Atlas cluster. Start with the [README](README.md) (concepts and Atlas setup), then follow the sections in order.

## Quick Navigation

1. [Section 1 — Foundations](#section-1--foundations) — Document model, connecting to Atlas, reading data
2. [Section 2 — Writing Data](#section-2--writing-data) — Full CRUD lifecycle
3. [Section 3 — Analytics and Performance](#section-3--analytics-and-performance) — Aggregation, indexing and query tuning
4. [Section 4 — Data Modeling](#section-4--data-modeling) — Schema design, patterns and anti-patterns
5. [Section 5 — Search and AI](#section-5--search-and-ai) — Keyword search, vector search, hybrid ranking
6. [Section 6 — Reliability and Scale](#section-6--reliability-and-scale) — Transactions, replication and security
7. [Section 7 — Capstone](#section-7--capstone) — university registration database
8. [Course Summary](#course-summary)

## Before You Start

- [README.md](README.md): what MongoDB is, core concepts, and the 7-step Atlas + `.env` setup (Section 8 of the README)
- [.env.example](.env.example): copy to `.env` and add your `MONGODB_URI` (the `.env` stays at this folder's root)
- [MongoDB_Labs_Overview.pptx](MongoDB_Labs_Overview.pptx): overview deck (still shows the original 7-lab structure)

Each lab folder contains four things: the runnable **notebook**, the **write-up** (problem, diagrams, steps), the **assignment** (exercises plus answer key), and the **tests**.

---

## Section 1 — Foundations

*Document model, connecting to Atlas, reading data*

### [Lab 1 - Student Records Lookup](Section%201%20-%20Foundations/Lab%201%20-%20Student%20Records%20Lookup/)

**MongoDB Basics: How to Query Data**  
Beginner | ~35 min | Requires: None

- [Notebook](Section%201%20-%20Foundations/Lab%201%20-%20Student%20Records%20Lookup/lab-1-student-records-lookup.ipynb)
- [Write-up](Section%201%20-%20Foundations/Lab%201%20-%20Student%20Records%20Lookup/lab-1-student-records-lookup.md)
- [Assignment and answer key](Section%201%20-%20Foundations/Lab%201%20-%20Student%20Records%20Lookup/lab-1-student-records-lookup-assignment.md)
- [Tests](Section%201%20-%20Foundations/Lab%201%20-%20Student%20Records%20Lookup/test_lab1_student_records_lookup.py)

---

## Section 2 — Writing Data

*Full CRUD lifecycle*

### [Lab 2 - Student Enrollment Tracker](Section%202%20-%20Writing%20Data/Lab%202%20-%20Student%20Enrollment%20Tracker/)

**MongoDB Basics: How to Write, Update & Delete Data**  
Beginner | ~35 min | Requires: Lab 1

- [Notebook](Section%202%20-%20Writing%20Data/Lab%202%20-%20Student%20Enrollment%20Tracker/lab-2-student-enrollment-tracker.ipynb)
- [Write-up](Section%202%20-%20Writing%20Data/Lab%202%20-%20Student%20Enrollment%20Tracker/lab-2-student-enrollment-tracker.md)
- [Assignment and answer key](Section%202%20-%20Writing%20Data/Lab%202%20-%20Student%20Enrollment%20Tracker/lab-2-student-enrollment-tracker-assignment.md)
- [Tests](Section%202%20-%20Writing%20Data/Lab%202%20-%20Student%20Enrollment%20Tracker/test_lab2_student_enrollment_tracker.py)

---

## Section 3 — Analytics and Performance

*Aggregation, indexing and query tuning*

### [Lab 3 - Academic Performance Analytics](Section%203%20-%20Analytics%20and%20Performance/Lab%203%20-%20Academic%20Performance%20Analytics/)

**MongoDB Intermediate: How to Analyze Data at Scale**  
Intermediate | ~40 min | Requires: Labs 1-2

- [Notebook](Section%203%20-%20Analytics%20and%20Performance/Lab%203%20-%20Academic%20Performance%20Analytics/lab-3-academic-performance-analytics.ipynb)
- [Write-up](Section%203%20-%20Analytics%20and%20Performance/Lab%203%20-%20Academic%20Performance%20Analytics/lab-3-academic-performance-analytics.md)
- [Assignment and answer key](Section%203%20-%20Analytics%20and%20Performance/Lab%203%20-%20Academic%20Performance%20Analytics/lab-3-academic-performance-analytics-assignment.md)
- [Tests](Section%203%20-%20Analytics%20and%20Performance/Lab%203%20-%20Academic%20Performance%20Analytics/test_lab3_academic_performance_analytics.py)

### [Lab 3B - Query Optimization](Section%203%20-%20Analytics%20and%20Performance/Lab%203B%20-%20Query%20Optimization/)

**MongoDB Intermediate: How to Make Queries Fast**  
Intermediate | ~50 min | Requires: Lab 3

- [Notebook](Section%203%20-%20Analytics%20and%20Performance/Lab%203B%20-%20Query%20Optimization/lab-3b-query-optimization.ipynb)
- [Write-up](Section%203%20-%20Analytics%20and%20Performance/Lab%203B%20-%20Query%20Optimization/lab-3b-query-optimization.md)
- [Assignment and answer key](Section%203%20-%20Analytics%20and%20Performance/Lab%203B%20-%20Query%20Optimization/lab-3b-query-optimization-assignment.md)
- [Tests](Section%203%20-%20Analytics%20and%20Performance/Lab%203B%20-%20Query%20Optimization/test_lab3b_query_optimization.py)

---

## Section 4 — Data Modeling

*Schema design, patterns and anti-patterns*

### [Lab 4 - Courses and Instructors](Section%204%20-%20Data%20Modeling/Lab%204%20-%20Courses%20and%20Instructors/)

**MongoDB Intermediate: How to Design Schemas & Search Data**  
Intermediate | ~40 min | Requires: Labs 1-3

- [Notebook](Section%204%20-%20Data%20Modeling/Lab%204%20-%20Courses%20and%20Instructors/lab-4-courses-instructors.ipynb)
- [Write-up](Section%204%20-%20Data%20Modeling/Lab%204%20-%20Courses%20and%20Instructors/lab-4-courses-instructors.md)
- [Assignment and answer key](Section%204%20-%20Data%20Modeling/Lab%204%20-%20Courses%20and%20Instructors/lab-4-courses-instructors-assignment.md)
- [Tests](Section%204%20-%20Data%20Modeling/Lab%204%20-%20Courses%20and%20Instructors/test_lab4_courses_instructors.py)

### [Lab 4B - Schema Patterns and Anti-patterns](Section%204%20-%20Data%20Modeling/Lab%204B%20-%20Schema%20Patterns%20and%20Anti-patterns/)

**MongoDB Intermediate: How to Recognize Schema Patterns and Anti-patterns**  
Intermediate | ~45 min | Requires: Lab 4

- [Notebook](Section%204%20-%20Data%20Modeling/Lab%204B%20-%20Schema%20Patterns%20and%20Anti-patterns/lab-4b-schema-patterns.ipynb)
- [Write-up](Section%204%20-%20Data%20Modeling/Lab%204B%20-%20Schema%20Patterns%20and%20Anti-patterns/lab-4b-schema-patterns.md)
- [Assignment and answer key](Section%204%20-%20Data%20Modeling/Lab%204B%20-%20Schema%20Patterns%20and%20Anti-patterns/lab-4b-schema-patterns-assignment.md)
- [Tests](Section%204%20-%20Data%20Modeling/Lab%204B%20-%20Schema%20Patterns%20and%20Anti-patterns/test_lab4b_schema_patterns.py)

---

## Section 5 — Search and AI

*Keyword search, vector search, hybrid ranking*

### [Lab 4C - Atlas Search and Vector Search](Section%205%20-%20Search%20and%20AI/Lab%204C%20-%20Atlas%20Search%20and%20Vector%20Search/)

**MongoDB Intermediate: How to Search by Keywords and by Meaning**  
Intermediate to Advanced | ~60 min | Requires: Lab 4

- [Notebook](Section%205%20-%20Search%20and%20AI/Lab%204C%20-%20Atlas%20Search%20and%20Vector%20Search/lab-4c-atlas-search-vector-search.ipynb)
- [Write-up](Section%205%20-%20Search%20and%20AI/Lab%204C%20-%20Atlas%20Search%20and%20Vector%20Search/lab-4c-atlas-search-vector-search.md)
- [Assignment and answer key](Section%205%20-%20Search%20and%20AI/Lab%204C%20-%20Atlas%20Search%20and%20Vector%20Search/lab-4c-atlas-search-vector-search-assignment.md)
- [Tests](Section%205%20-%20Search%20and%20AI/Lab%204C%20-%20Atlas%20Search%20and%20Vector%20Search/test_lab4c_atlas_search_vector_search.py)

---

## Section 6 — Reliability and Scale

*Transactions, replication and security*

### [Lab 5 - Enrollment Transactions](Section%206%20-%20Reliability%20and%20Scale/Lab%205%20-%20Enrollment%20Transactions/)

**MongoDB Advanced: How to Guarantee Data Consistency**  
Advanced | ~40 min | Requires: Labs 1-4

- [Notebook](Section%206%20-%20Reliability%20and%20Scale/Lab%205%20-%20Enrollment%20Transactions/lab-5-enrollment-transactions.ipynb)
- [Write-up](Section%206%20-%20Reliability%20and%20Scale/Lab%205%20-%20Enrollment%20Transactions/lab-5-enrollment-transactions.md)
- [Assignment and answer key](Section%206%20-%20Reliability%20and%20Scale/Lab%205%20-%20Enrollment%20Transactions/lab-5-enrollment-transactions-assignment.md)
- [Tests](Section%206%20-%20Reliability%20and%20Scale/Lab%205%20-%20Enrollment%20Transactions/test_lab5_enrollment_transactions.py)

### [Lab 6 - Scaling the University Database](Section%206%20-%20Reliability%20and%20Scale/Lab%206%20-%20Scaling%20the%20University%20Database/)

**MongoDB Advanced: How to Inspect a Replica Set and Secure Access**  
Advanced | ~40 min | Requires: Labs 1-5

- [Notebook](Section%206%20-%20Reliability%20and%20Scale/Lab%206%20-%20Scaling%20the%20University%20Database/lab-6-scaling-university-database.ipynb)
- [Write-up](Section%206%20-%20Reliability%20and%20Scale/Lab%206%20-%20Scaling%20the%20University%20Database/lab-6-scaling-university-database.md)
- [Assignment and answer key](Section%206%20-%20Reliability%20and%20Scale/Lab%206%20-%20Scaling%20the%20University%20Database/lab-6-scaling-university-database-assignment.md)
- [Tests](Section%206%20-%20Reliability%20and%20Scale/Lab%206%20-%20Scaling%20the%20University%20Database/test_lab6_scaling_university_database.py)

---

## Section 7 — Capstone

*One short project that reuses every earlier lab*

### [Lab 7 - University Registration Database](Section%207%20-%20Capstone/Lab%207%20-%20University%20Registration%20Database/)

**MongoDB Capstone: University Registration Database**  
Capstone | ~90 min in one sitting | Requires: Labs 1-6 (and 3B, 4B, 4C)

- [Starter notebook](Section%207%20-%20Capstone/Lab%207%20-%20University%20Registration%20Database/lab-7-registration-database.ipynb)
- [Solution notebook](Section%207%20-%20Capstone/Lab%207%20-%20University%20Registration%20Database/lab-7-registration-database-solution.ipynb)
- [Write-up](Section%207%20-%20Capstone/Lab%207%20-%20University%20Registration%20Database/lab-7-registration-database.md)
- [Assignment and answer key](Section%207%20-%20Capstone/Lab%207%20-%20University%20Registration%20Database/lab-7-registration-database-assignment.md)
- [Tests](Section%207%20-%20Capstone/Lab%207%20-%20University%20Registration%20Database/test_lab7_registration_database.py)

---

## Course Summary

| Section | Labs | Time |
|---|---|---|
| 1 Foundations | Lab 1 | ~35 min |
| 2 Writing Data | Lab 2 | ~35 min |
| 3 Analytics and Performance | Labs 3, 3B | ~90 min |
| 4 Data Modeling | Labs 4, 4B | ~85 min |
| 5 Search and AI | Lab 4C | ~60 min |
| 6 Reliability and Scale | Labs 5, 6 | ~80 min |
| 7 Capstone | Lab 7 | ~90 min |
| **Total** | **10 labs** | **about 8 hours including the capstone** |

Labs 3B, 4B and 4C were added to the original seven. They keep letter numbers so existing database names, tests and cross-references stay valid.

## Other Files

- [test-results/](test-results/): JUnit XML and Excel results from earlier test runs of Labs 1-7
- [_archive/](_archive/): the earlier two-week AI Agent Memory capstone, kept for reference
