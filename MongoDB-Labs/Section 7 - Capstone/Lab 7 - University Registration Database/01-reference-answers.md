# Capstone: Reference Answers to the Post-Capstone Assignment

This is the instructor answer key for Section 10 of the capstone spec. Every answer follows the design fixed in Sections 6 and 7: a transactional `enroll()` that checks the student, takes one seat with a conditional atomic update and inserts the enrollment, backed by the unique index `uniq_student_course` and the ESR index `esr_course_status_date`.

---

## Question 1: Trace two enrollments into a course with one seat left

**Setup:** CS101 has `seats_available = 1`. S004 (active) enrolls first, then S009 (active).

**Colour key used in the table snapshots:** 🟩 inserted &nbsp;·&nbsp; 🟨 updated &nbsp;·&nbsp; 🟥 rolled back / rejected &nbsp;·&nbsp; 🟦 read &nbsp;·&nbsp; ⬜ not touched

| Step | Student | Action | `courses` (CS101) | `enrollments` |
|------|---------|--------|-------------------|---------------|
| 1 | S004 | read the student | ⬜ unchanged | ⬜ unchanged (`students` is read, 🟦) |
| 2 | S004 | conditional update (`seats_available > 0`, decrement) | `seats_available` 1 → 0 (🟨) | ⬜ unchanged |
| 3 | S004 | insert the enrollment | ⬜ stays 0 | one new S004 row (🟩) |
| 4 | S004 | commit | 0 | S004 enrolled |
| 5 | S009 | read the student | ⬜ unchanged | ⬜ unchanged |
| 6 | S009 | conditional update | **no document matches** (`seats_available` is 0), so nothing changes | ⬜ unchanged |
| 7 | S009 | abort with "course is full" | 0 | no S009 row (🟥 rejected) |

**Pattern to check in a student's answer.**

- The seat count never goes below zero.
- The enrollment row is written only after the seat was taken.
- A rejection leaves **both** collections exactly as they were.

---

## Question 2: Why both an atomic update and a transaction?

The conditional update (`find_one_and_update` with the filter `seats_available > 0` and `$inc: -1`) checks and changes the counter in **one atomic step**, so two students cannot both take the last seat.

A plain "read the seat count, then update it" has a gap between the read and the write. Two requests can both read `1`, both decide there is room, and both enroll, so the course is over-booked by one.

The transaction solves a different problem: it ties the seat to the enrollment. If the seat is taken and the insert then fails, the transaction aborts and the seat is returned. Without it, a failed insert would leave a seat taken by nobody.

---

## Question 3: Why is the dashboard index in this order?

The query filters on two **equalities** (`course_id`, `status`) and sorts by `enrolled_at`. The ESR rule (Equality, Sort, Range) orders the index as `(course_id, status, enrolled_at descending)`.

In that order, all entries for one course and status sit together, already newest-first. MongoDB jumps to them, reads the first 10 and stops: stages `LIMIT`, `FETCH`, `IXSCAN`, no `SORT`, about 10 documents examined instead of about 30,003.

With `(enrolled_at, course_id, status)`, the entries are ordered by date across **all** courses. MongoDB must walk entries and discard those of other courses and statuses, examining far more of them, so the index barely helps.

---

## Question 4: The copied course title

| | Answer |
|---|--------|
| **Benefit** | A student's course list is one query on `enrollments`, with no `$lookup` join. |
| **Risk** | The copy becomes stale if the course is renamed: old enrollments keep the old title. |
| **Handling a rename** | Update `courses` first (the source of truth), then propagate the new title with one `update_many({"course_id": ...}, {"$set": {"course_title": new}})` on `enrollments`. |

A good answer also says why the copy is acceptable: titles change rarely, and the page that shows them is read far more often than a rename happens.

---

## Question 5: Enrolling twice in the same course

**Which write fails.** The enrollment insert (step 3), because the unique index `uniq_student_course` rejects a second `(student_id, course_id)` pair with a duplicate-key error.

**What happens to the seat.** The seat was already taken in step 2, inside the same transaction. When the insert raises the duplicate-key error, the transaction **aborts** and the seat decrement is rolled back, so `seats_available` is back to what it was before the request.

**What the learner sees.** A clear "already enrolled" rejection from `enroll()`. The error is a business rejection, not a transient one, so it is not retried.

| Collection | Before | During | After the abort |
|------------|--------|--------|-----------------|
| `courses` (CS101) | `seats_available` 2 | 1 (🟨 uncommitted) | 2 (🟥 rolled back) |
| `enrollments` | one existing row for the student | second insert rejected | still one row |

---

## Question 6: Health checks

**Replica set.** Run `db.command("hello")`: `setName` names the replica set and `hosts` lists its members (a free M0 cluster is a three-member replica set). It proves the data is copied to more than one server, so one failure does not lose it.

**TLS.** A `mongodb+srv://` connection string always uses TLS, so `tls_enforced = True` when the string uses that scheme. It proves data in transit is encrypted.

**Roles.** `db.command("connectionStatus")["authInfo"]["authenticatedUserRoles"]` lists the roles of the current user. It proves what the application is allowed to do, and shows whether it follows **least privilege**.

**What M0 does not let you change.** You cannot add replica-set members or shard a collection on the free tier, so the capstone only inspects the deployment.
