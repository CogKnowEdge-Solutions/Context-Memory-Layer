# MongoDB Capstone: University Registration Database

## Assignment

Complete the starter notebook, then answer three short reflection questions. This capstone is intentionally small: finish it in one sitting.

---

# Objective Sheet

Build and verify a registration database on MongoDB Atlas that enrolls students safely, reports accurately, answers its busiest query quickly, supports typo-tolerant search, and cleans up after itself.

---

# Checklist

Every item has a **check cell** in the notebook. A step is complete when its check prints *passed*.

| # | Step | Skill reused | Points |
|---|------|--------------|--------|
| 1 | Seed students and courses, add the unique index | Labs 1, 4, 4B | 10 |
| 2 | Query, update and upsert | Labs 1, 2 | 10 |
| 3 | Transactional enrollment (full course and inactive student rejected) | Labs 2, 5 | 20 |
| 4 | Per-course enrollment and average-grade report | Lab 3 | 15 |
| 5 | ESR index: `COLLSCAN` and `SORT` replaced by `IXSCAN` with no `SORT` | Labs 3, 3B | 15 |
| 6 | Typo-tolerant catalog search (`programing` finds CS101) | Lab 4C | 15 |
| 7 | Replica set, TLS and roles read correctly; database cleaned up | Lab 6 | 5 |
| | Reflection questions (below) | All | 10 |
| | **Total** | | **100** |

**Passing: 60 points. Distinction: 85 points.**

---

# Deliverables

| Deliverable | What to submit |
|-------------|----------------|
| Completed notebook | `lab-7-registration-database.ipynb` with every step's check printing *passed* |
| Reflection answers | Your answers to the three questions below (a few sentences each) |

---

# Reflection Questions (10 points)

1. **(3 pts)** Why does the `enroll` function take the seat with `find_one_and_update` *and* run inside a transaction? What would go wrong with a plain "read the seat count, then update it" approach?
2. **(4 pts)** The dashboard index is `(course_id, status, enrolled_at descending)`. Explain why the fields are in that order, and what would go wrong if the index were `(enrolled_at, course_id, status)` instead.
3. **(3 pts)** Each enrollment stores a copy of the course title. Name one benefit and one risk of that copy, and say how you would handle a course being renamed.

---

# Answer Key

### Reflection 1
`find_one_and_update` with the filter `seats_available > 0` checks and decrements the counter in **one atomic step**, so two students cannot both take the last seat. A plain read-then-update has a gap between the read and the write: two requests can both read "1 seat left" and both enroll, over-booking the course. The transaction adds the second guarantee: the seat decrement and the enrollment insert **succeed or fail together**, so a seat is never taken without a matching enrollment record, and a failed insert (for example a duplicate) rolls the seat back.

### Reflection 2
The query filters on two **equalities** (`course_id`, `status`) and sorts by `enrolled_at`, so the ESR order is Equality, Equality, Sort. The index entries for one course and status are then already stored newest-first, and MongoDB reads the first 10 and stops: `IXSCAN`, no `SORT`, about 10 documents examined. With `(enrolled_at, course_id, status)` the entries are ordered by date across **all** courses, so MongoDB cannot jump straight to one course's group: it has to walk many entries newest-first and skip those with the wrong course or status, examining far more keys before it finds 10 matches.

---

### Reflection 3
**Benefit:** the "my enrollments" page shows the course title with a single query on `enrollments`, with no `$lookup` join (extended reference pattern). **Risk:** the copy goes stale if the course is renamed, so old enrollments would show the old title. **Handling:** update the source in `courses` first, then propagate with `enrollments.update_many({"course_id": cid}, {"$set": {"course_title": new_title}})`, possibly as a background job. (For historical records, keeping the title the student originally enrolled under can be the correct behaviour.)

---

# Rubric

| Band | Points | Meaning |
|------|--------|---------|
| Distinction | 85-100 | All steps pass and the reflection answers are accurate |
| Pass | 60-84 | Steps 1-5 pass; some reflection gaps or Step 6 or 7 incomplete |
| Not yet | below 60 | Revisit the earlier labs for the failing steps, then retry |

---

# Tips

- Do the steps **in order**: later steps rely on earlier data.
- Read the **check cell's message** when it stops; it tells you exactly what is missing.
- Step 6 needs Atlas Search, so make sure your cluster is running and wait for the index to build.
- If you run a step twice and see duplicates or unexpected counts, restart from Step 0, which clears the collections.
