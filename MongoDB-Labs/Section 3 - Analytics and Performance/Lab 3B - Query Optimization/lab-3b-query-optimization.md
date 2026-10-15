# How to Make Queries Fast

---

# Problem Statement / Use Case Overview

An index can change a query plan from `COLLSCAN` to `IXSCAN`, but real applications need more than that. A university's enrollment system receives a hundred thousand records per year, and the dashboard that lists "the top 20 active Computer Science grades" has started to feel slow. Someone has asked you to find out why and fix it **without adding hardware**.

## What Is Query Optimization, and Why Does It Matter?

**In one sentence:** Query optimization means helping MongoDB find the documents you asked for by reading as *little* data as possible, so the answer comes back fast.

Think of a library. To find every book on physics, you could walk past every shelf and check every spine. Or you could use the **catalogue**, which tells you the exact shelves. An index is that catalogue. A query is "slow" when MongoDB walks every shelf, even though it only needed a few books.

### How MongoDB decides how to run a query

When you run a query, MongoDB does not just start reading. A part called the **query planner** first picks a **query plan**: a recipe of steps (called *stages*) to find the documents. You can ask MongoDB to show you the plan with `explain()`.

```mermaid
flowchart TB
    Q["Your query<br/>filter + sort + limit"] --> P["Query planner<br/>picks the cheapest plan"]
    P --> PL["Query plan<br/>(stages)"]
    PL --> R["Result<br/>documents returned"]
    PL -.->|"explain() shows this"| X["Plan report<br/>stages + counts + time"]

    style Q fill:#e1f5ff,stroke:#333333,stroke-width:1px,color:#111111
    style P fill:#e1f5ff,stroke:#333333,stroke-width:1px,color:#111111
    style PL fill:#fff3cd,stroke:#333333,stroke-width:1px,color:#111111
    style R fill:#d3f9d8,stroke:#333333,stroke-width:1px,color:#111111
    style X fill:#fff3cd,stroke:#333333,stroke-width:1px,color:#111111
```

### A slow plan and a fast plan for the same question

The question is the same in both plans: "the top 20 active Computer Science grades". Only the plan is different.

```mermaid
flowchart LR
    subgraph SLOW["Slow plan: no useful index"]
        S1["COLLSCAN<br/>read all 100,000 documents"] --> S2["SORT<br/>sort the matches in memory"] --> S3["Return 20"]
    end
    subgraph FAST["Fast plan: compound index"]
        F1["IXSCAN<br/>walk the index in order"] --> F2["FETCH<br/>load 20 documents"] --> F3["Return 20"]
    end
    SLOW ~~~ FAST

    style S1 fill:#ffe3e3,stroke:#333333,stroke-width:1px,color:#111111
    style S2 fill:#ffe3e3,stroke:#333333,stroke-width:1px,color:#111111
    style S3 fill:#e1f5ff,stroke:#333333,stroke-width:1px,color:#111111
    style F1 fill:#d3f9d8,stroke:#333333,stroke-width:1px,color:#111111
    style F2 fill:#d3f9d8,stroke:#333333,stroke-width:1px,color:#111111
    style F3 fill:#e1f5ff,stroke:#333333,stroke-width:1px,color:#111111
```

Both plans return the same 20 documents. The slow plan does far more work to get there.

### How to read `explain()`

| Field or stage | What it tells you | What a healthy value looks like |
|----------------|-------------------|---------------------------------|
| `COLLSCAN` | MongoDB read every document in the collection | Avoid it on big collections you query often |
| `IXSCAN` | MongoDB used an index | This is what you want to see |
| `FETCH` | MongoDB loaded the full document for an index entry | Fine, as long as it fetches few documents |
| `SORT` | MongoDB sorted results in memory | Absent, because the index already gives the order |
| `nReturned` | Documents sent back to you | Whatever the query needs |
| `totalDocsExamined` | Documents MongoDB actually read | Close to `nReturned` |
| `totalKeysExamined` | Index entries MongoDB walked | Close to `nReturned` |
| `executionTimeMillis` | Time the server spent | Low. Compare it before and after a change |

The key idea is the gap between **examined** and **returned**. Reading 100,000 documents to return 20 means about 99,980 were read for nothing.

### Why a query is slow

| Symptom in `explain()` | What it means in plain words | Usual fix |
|------------------------|------------------------------|-----------|
| `COLLSCAN` and docs examined much larger than returned | MongoDB walked every shelf | Add an index on the filtered fields |
| A `SORT` stage | MongoDB gathered all matches, then sorted them in memory | Put the sort field in the index, in the right position |
| `FETCH` of many documents you barely use | MongoDB opened full documents just to read a few fields | Return only the fields you need (a projection), and consider a covered query |

### Compound indexes and the ESR rule

A **compound index** is one index over several fields, in a fixed order. The order matters, just like a phone book sorted by last name and then first name. The **ESR rule** is a good starting order:

| Position | Field type | Example from enrollment data | Why it goes here |
|----------|------------|------------------------------|------------------|
| 1st | **E**quality (`==`) | `course` = "Computer Science" | Narrows the index to one small block |
| 2nd | **S**ort | `submitted_at`, newest first | Entries in that block are already in sort order |
| 3rd | **R**ange (`>=`, `<`) | `grade` >= 90 | Checked while walking, so it cannot break the order |

If you put the range field *before* the sort field, the entries are no longer in sort order. MongoDB then has to bring in an in-memory `SORT` again.

### Covered queries and projections

A **projection** lists which fields to return. If the filter fields and the returned fields all live in one index (and `_id` is left out), MongoDB can answer from the index alone. It reads **zero documents**. This is called a *covered query*.

### What your changes cost

| Benefit of an index | Cost of an index |
|---------------------|------------------|
| Queries read fewer documents | Takes extra storage |
| Sorts can skip the in-memory step | Every insert, update of an indexed field, and delete must also update the index |
| Covered queries are possible | An index nobody uses is pure cost |

To find slow queries you did not know about, MongoDB has a **database profiler**. It records operations slower than a time limit you choose. It may not be available on every cluster tier.

> **Honest note:** More indexes do not mean a faster database. Each one slows writes and uses memory and storage. ESR is a strong starting rule, not a law. Do not guess: **measure with `explain()`, change one thing, and measure again.**

**Learn more (official MongoDB documentation):**

- [Explain Results — Database Manual](https://www.mongodb.com/docs/manual/reference/explain-results/)
- [Interpret Explain Plan Results — Database Manual](https://www.mongodb.com/docs/manual/tutorial/analyze-query-plan/)
- [The ESR (Equality, Sort, Range) Guideline — Database Manual](https://www.mongodb.com/docs/manual/tutorial/equality-sort-range-guideline/)
- [Query Plans — Database Manual](https://www.mongodb.com/docs/manual/core/query-plans/)
- [Database Profiler — Database Manual](https://www.mongodb.com/docs/manual/tutorial/manage-the-database-profiler/)

This lab gives you a deliberately unoptimized collection of 100,000 enrollment records and a short list of slow queries. For each one you will read the execution plan, form a diagnosis, apply a fix, and prove the fix worked with numbers: documents examined, index keys examined, and milliseconds. You will also learn the cost side of indexing: every index takes storage and slows writes, so unused ones must be found and removed.

The skill you leave with is a repeatable loop: **measure, diagnose, change one thing, measure again.**

---

# Input Data

| Item | Detail |
|------|--------|
| **Collection** | `school_db.enrollment_log` (created and dropped by the notebook) |
| **Size** | 100,000 synthetic documents, generated with a fixed random seed so every learner gets identical data |
| **Fields** | `record_id`, `student_id`, `course`, `semester`, `status`, `grade`, `credits`, `submitted_at`, `notes` |
| **Courses** | Computer Science, Mathematics, Physics, English, Biology |
| **Statuses** | active (~60%), completed (~25%), withdrawn (~10%), pending (~5%) |
| **Storage** | Roughly 20-30 MB, which fits comfortably inside the 512 MB Atlas M0 free tier |

---

# Processing

### Part A — Diagnose and Fix with Indexes

```mermaid
flowchart TB
    S["Slow query"] --> E["explain()<br/>executionStats"]
    E --> D{"Examined >> Returned?"}
    D -->|Yes| I["Add or reorder index<br/>(ESR rule)"]
    D -->|No| OK["Query is efficient"]
    I --> E2["explain() again"]
    E2 --> C["Compare before / after"]

    style S fill:#ffccbc,stroke:#333333,stroke-width:1px,color:#111111
    style E fill:#e1f5ff,stroke:#333333,stroke-width:1px,color:#111111
    style D fill:#fff9c4,stroke:#333333,stroke-width:1px,color:#111111
    style I fill:#fff9c4,stroke:#333333,stroke-width:1px,color:#111111
    style OK fill:#c8e6c9,stroke:#333333,stroke-width:1px,color:#111111
    style E2 fill:#e1f5ff,stroke:#333333,stroke-width:1px,color:#111111
    style C fill:#c8e6c9,stroke:#333333,stroke-width:1px,color:#111111
```

The notebook runs two slow queries: a "filter then sort" query (Query 1) and a "filter on a range then sort by date" query (Query 2). Query 1 is fixed with a compound index. Query 2 shows how the **order of fields inside the index** decides whether MongoDB can skip an expensive in-memory sort.

### Part B — Covered Queries, Index Cost and Aggregations

```mermaid
flowchart TB
    CQ["Covered query<br/>0 documents read"] --> IC["Index cost<br/>size + write speed"]
    IC --> UI["$indexStats<br/>find unused index"]
    UI --> AG["Aggregation<br/>indexed $match first"]
    AG --> SB["Scoreboard"]

    style CQ fill:#e1f5ff,stroke:#333333,stroke-width:1px,color:#111111
    style IC fill:#fff9c4,stroke:#333333,stroke-width:1px,color:#111111
    style UI fill:#fff9c4,stroke:#333333,stroke-width:1px,color:#111111
    style AG fill:#e1f5ff,stroke:#333333,stroke-width:1px,color:#111111
    style SB fill:#c8e6c9,stroke:#333333,stroke-width:1px,color:#111111
```

After the fixes, you write a query answered entirely from the index, measure what the indexes cost in storage and insert time, detect and drop an index nobody uses, and speed up an aggregation by letting an index feed its first stage.

---

# Output

> **Illustrative output.** Your millisecond values and exact counts will differ by cluster and region. What must match is the *shape*: `COLLSCAN` before, `IXSCAN` after, and a large drop in documents examined.

**Query 1 plan, before and after the compound index:**

```
Query 1 - before index
  stages: COLLSCAN > SORT
  returned: 20 | docs examined: 100000 | keys examined: 0 | server ms: 60

Query 1 - after ESR index
  stages: IXSCAN > FETCH
  returned: 20 | docs examined: 20 | keys examined: 20 | server ms: 0
```

**Index field order decides whether a SORT stage is needed (Query 2):**

```
Query 2 - index order Equality, Range, Sort   (course, grade, submitted_at)
  stages: IXSCAN > FETCH > SORT           <-- in-memory sort required
Query 2 - index order Equality, Sort, Range   (course, submitted_at, grade)
  stages: IXSCAN > FETCH                  <-- no SORT stage
```

**Covered query:**

```
Covered query
  stages: IXSCAN > PROJECTION_COVERED
  returned: 5000 | docs examined: 0 | keys examined: 5000
```

**Scoreboard:**

```
Case                      Docs examined (before -> after)
Query 1: top 20 active    100000 -> 20
Query 2: newest high       ~3300 -> ~60
Covered query             5000 -> 0
Aggregation (one slice)    100000 -> ~6250
```

---

# Tech Stack

| Component | Tool |
|-----------|------|
| **MongoDB driver** | `pymongo[srv,tls]==4.10.1` — Python driver with SRV and TLS support |
| **Credential loader** | `python-dotenv==1.0.1` — loads the `.env` file |
| **CA certificates** | `certifi` — trusted CA bundle for Atlas TLS connections |
| **Standard library** | `random`, `datetime`, `time` — data generation and timing |

> **Note:** This lab connects to a real MongoDB Atlas cluster. The connection string is read from a `.env` file. The data set is sized to fit the free M0 tier.

---

# Underlying Concepts (Summarized)

### The Explain Report

`explain("executionStats")` actually runs the query and reports what happened. Four numbers matter most:

| Field | Meaning | What you want |
|-------|---------|---------------|
| `nReturned` | Documents sent back to the client | Whatever the query needs |
| `totalDocsExamined` | Documents MongoDB read from disk or cache | Close to `nReturned` |
| `totalKeysExamined` | Index entries MongoDB walked | Close to `nReturned` |
| `executionTimeMillis` | Server-side time | As low as possible |

A healthy query examines roughly as many documents as it returns. If it examines 100,000 to return 20, MongoDB did 5,000 times more work than necessary.

### Plan Stages You Will See

`COLLSCAN` reads every document. `IXSCAN` walks an index. `FETCH` loads the full document for an index entry. `SORT` is an **in-memory sort** that happens when no index delivers results in the requested order; it blocks until all matching documents are read and is limited by memory. `PROJECTION_COVERED` means the answer came straight from the index.

### The ESR Rule

For a compound index, order the fields as **E**quality, **S**ort, **R**ange:

1. **Equality** fields first (`course == "Physics"`).
2. **Sort** fields next, so the index already holds entries in the requested order.
3. **Range** fields last (`grade >= 90`, `$gt`, `$lt`, `$in` with many values).

Putting a range field before the sort field breaks the sort order and forces an in-memory `SORT`. ESR is a strong starting rule, not a law: always confirm with `explain`.

### Covered Queries

If every field the query filters on **and** returns lives in one index, and `_id` is excluded from the projection, MongoDB never reads a document. `totalDocsExamined` is `0`.

### The Cost of Indexes

Each index uses storage and must be updated on every insert, update of an indexed field, and delete. An index that no query uses is pure cost. `$indexStats` reports how often each index was used since the server last restarted, so unused indexes can be found and dropped.

### Aggregation and Indexes

Only the **first stages** of a pipeline can use an index. A `$match` (and a `$sort`) at the start of the pipeline can; a `$group` at the start cannot. Filtering early also reduces the number of documents flowing through later stages.

---

# Pre-requisites

- Basic familiarity with aggregation pipelines and creating a simple index (summarised in the concepts section above)
- A working MongoDB Atlas cluster and a `.env` file holding your connection string — set these up before you start
- Comfort reading Python dictionaries and loops

> **Atlas free-tier note.** The database profiler and the Performance Advisor are not available on the free M0 tier. This lab uses `explain` and `$indexStats`, which work everywhere. Step 10 shows how to try the profiler and what to do if your tier refuses it.

---

# Environment / Dependencies Setup

| Package | Purpose |
|---------|---------|
| `pymongo[srv,tls]` | Python driver for MongoDB with SRV and TLS support |
| `python-dotenv` | Loads `.env` files so credentials stay out of the notebook |
| `certifi` | Provides up-to-date CA certificates for reliable SSL/TLS on all platforms |

```bash
pip install -q "pymongo[srv,tls]==4.10.1" python-dotenv==1.0.1 certifi
```

This installs the MongoDB Python driver (`pymongo`), `python-dotenv` for loading credentials, and `certifi` for trusted CA certificates.

---

# Step-wise Instructions — Development


### Step 1 — Connect to MongoDB

```python
import os
import time
import random
import datetime as dt
import certifi
from dotenv import load_dotenv
import pymongo

# Load the Atlas connection string from the .env file
load_dotenv()
uri = os.environ["MONGODB_URI"]

client = pymongo.MongoClient(uri, tlsCAFile=certifi.where())
db = client["school_db"]
log = db["enrollment_log"]

print("Connected to MongoDB Atlas")
```

> **Where does the `.env` file go?** `load_dotenv()` looks for a file named `.env` in the folder you run from and then in each parent folder above it. Save it next to your notebook, or once in the root folder of your course project, with a single line: `MONGODB_URI=mongodb+srv://<user>:<password>@<cluster-host>/` (use your own Atlas connection string, and never commit this file to Git).


`load_dotenv` reads the connection string from the `.env` file, and `certifi.where()` provides trusted CA certificates for SSL.

---

### Step 2 — Generate 100,000 Enrollment Records

```python
random.seed(42)          # fixed seed: every learner gets identical data

COURSES   = ["Computer Science", "Mathematics", "Physics", "English", "Biology"]
STATUSES  = ["active", "completed", "withdrawn", "pending"]
WEIGHTS   = [60, 25, 10, 5]
SEMESTERS = ["2024-Fall", "2025-Spring", "2025-Fall", "2026-Spring"]
START     = dt.datetime(2024, 9, 1)
N         = 100_000

def make_record(i):
    return {
        "record_id":    i,
        "student_id":   f"STU{random.randint(1, 5000):05d}",
        "course":       random.choice(COURSES),
        "semester":     random.choice(SEMESTERS),
        "status":       random.choices(STATUSES, weights=WEIGHTS)[0],
        "grade":        random.randint(35, 100),
        "credits":      random.choice([2, 3, 4]),
        "submitted_at": START + dt.timedelta(minutes=random.randint(0, 60 * 24 * 600)),
        "notes":        "x" * 40,
    }

log.drop()                                   # also removes any old indexes
batch = []
for i in range(N):
    batch.append(make_record(i))
    if len(batch) == 10_000:
        log.insert_many(batch)
        batch = []
if batch:
    log.insert_many(batch)

print("Documents inserted:", log.count_documents({}))
print("Indexes now:", list(log.index_information().keys()))
```

Inserting in batches of 10,000 keeps each network request a reasonable size. `log.drop()` at the start makes the notebook safe to re-run, and it also removes any indexes left from a previous run. Only the automatic `_id_` index exists now, so every query other than a lookup by `_id` will scan the whole collection.

**Colour key used in the table snapshots:** 🟩 inserted &nbsp;·&nbsp; 🟨 updated &nbsp;·&nbsp; 🟥 deleted &nbsp;·&nbsp; 🟦 matched / returned by a query &nbsp;·&nbsp; ⬜ not touched

**Snapshot — the new `enrollment_log` collection after the inserts: all 100,000 documents are 🟩 newly inserted (first 6 shown, 99,994 more not listed). MongoDB adds the hidden `_id` field automatically, so it is left out here.**

| | record_id | student_id | course | semester | status | grade | credits |
|---|---|---|---|---|---|---|---|
| 🟩 | 0 | STU00913 | Computer Science | 2025-Fall | active | 52 | 4 |
| 🟩 | 1 | STU04468 | Computer Science | 2026-Spring | active | 46 | 2 |
| 🟩 | 2 | STU04140 | Biology | 2024-Fall | active | 88 | 2 |
| 🟩 | 3 | STU04828 | Physics | 2024-Fall | completed | 55 | 4 |
| 🟩 | 4 | STU02788 | Physics | 2025-Spring | active | 78 | 2 |
| 🟩 | 5 | STU03113 | Computer Science | 2025-Fall | completed | 68 | 2 |
| 🟩 | … 99,994 more documents (record_id 6 to 99,999) | | | | | | |

The columns `submitted_at` and `notes` also exist in every document but are left out to keep the table narrow. Values shown are what seed 42 produces with the code above.

---

### Step 3 — Build Explain Helpers

```python
def collect_stages(node, found=None):
    """Walk a plan tree and return every stage name, outermost first."""
    found = [] if found is None else found
    if isinstance(node, dict):
        if "stage" in node:
            found.append(node["stage"])
        for value in node.values():
            collect_stages(value, found)
    elif isinstance(node, list):
        for value in node:
            collect_stages(value, found)
    return found

def summarize(label, explain):
    """Boil an explain report down to the numbers that matter."""
    stats  = explain["executionStats"]
    stages = collect_stages(explain["queryPlanner"]["winningPlan"])
    ordered = list(dict.fromkeys(stages))            # drop repeats, keep order
    summary = {
        "label": label,
        "stages": ordered,
        "returned": stats["nReturned"],
        "docs": stats["totalDocsExamined"],
        "keys": stats["totalKeysExamined"],
        "ms": stats["executionTimeMillis"],
    }
    print(label)
    print("  stages:", " > ".join(ordered))
    print(f"  returned: {summary['returned']} | docs examined: {summary['docs']} | "
          f"keys examined: {summary['keys']} | server ms: {summary['ms']}")
    return summary

def has_stage(summary, name):
    return any(name in s for s in summary["stages"])

scoreboard = {}      # filled in as we go
```

`collect_stages` walks the whole plan tree so it works whether MongoDB reports a simple plan or a nested one. `summarize` extracts the four numbers from the concepts section and prints them in one line, so every experiment below is easy to compare.

---

### Step 4 — Query 1 Before: Filter, Sort, Limit with No Index

```python
Q1_FILTER = {"course": "Computer Science", "status": "active"}

def query1():
    return log.find(Q1_FILTER, {"_id": 0, "student_id": 1, "grade": 1}).sort("grade", -1).limit(20)

before_q1 = summarize("Query 1 - before index", query1().explain())
scoreboard["Query 1: top 20 active CS grades"] = {"before": before_q1}

top = list(query1())
print("\nTop 3 results:", top[:3])
```

The dashboard asks for the 20 highest grades among active Computer Science enrollments. With no useful index MongoDB reads **all 100,000 documents** (`COLLSCAN`), keeps the ~12,000 matches, sorts them in memory (`SORT`), and returns 20. The gap between `docs examined` and `returned` is the signal that something can be improved.

**Snapshot — no data changes; the query only reads. Of the 100,000 documents, the 12,011 Computer Science + active ones are 🟦 matched, and only the top 20 by grade are returned. The other documents are ⬜ untouched (but all had to be read).**

| | Group of documents | Count | Note |
|---|---|---|---|
| 🟦 | course = Computer Science and status = active, grade 100 (top of the sort) | 156 of the 12,011 matches | the 20 returned documents all come from this group, because 156 is more than 20 |
| 🟦 | … the other matching documents | 11,855 | read and sorted in memory, then discarded |
| ⬜ | all other documents | 87,989 | read by `COLLSCAN` but do not match |

Counts are computed from the seed-42 data. The plan itself is `COLLSCAN > SORT`: 100,000 documents examined to return 20 (see the Output section).

---

### Step 5 — Query 1 After: A Compound Index Built with ESR

```python
def esr_index(equality, sort, range_fields=()):
    """Return index keys ordered Equality, Sort, Range."""
    return [(f, 1) for f in equality] + list(sort) + [(f, 1) for f in range_fields]

q1_keys = esr_index(equality=["course", "status"], sort=[("grade", -1)])
print("Index keys:", q1_keys)

log.create_index(q1_keys, name="esr_course_status_grade")

after_q1 = summarize("Query 1 - after ESR index", query1().explain())
scoreboard["Query 1: top 20 active CS grades"]["after"] = after_q1

print("\nSORT stage gone?", not has_stage(after_q1, "SORT"))
```

The index stores entries grouped by `course`, then `status`, then `grade` in descending order. MongoDB jumps straight to `(Computer Science, active)` and reads the first 20 entries, which are already in the requested order, so there is no `SORT` stage and only about 20 documents are examined instead of 100,000. The `esr_index` helper simply makes the rule explicit: equality fields, then sort fields, then range fields.

**Snapshot — the documents are unchanged, but the collection gains a new index. The new index is 🟩 added; the plan before is 🟥 shown once as the slow result it replaces; `_id_` is ⬜ untouched.**

| | Indexes on `enrollment_log` | Query 1 plan | Docs examined | Keys examined |
|---|---|---|---|---|
| ⬜ | `_id_` | not used by Query 1 | | |
| 🟩 | `esr_course_status_grade` on (course 1, status 1, grade -1) | `IXSCAN > FETCH` | 20 | 20 |
| 🟥 | (no index) old plan | `COLLSCAN > SORT` | 100,000 | 0 |

Numbers come from the Output section, which is illustrative: your exact times will differ.

---

### Step 6 — Query 2: Why Field Order Inside the Index Matters

```python
Q2_FILTER = {"course": "Physics", "grade": {"$gte": 90}}

def query2():
    return log.find(Q2_FILTER, {"_id": 0, "student_id": 1, "grade": 1, "submitted_at": 1}) \
              .sort("submitted_at", -1).limit(10)

# Attempt A: Equality, Range, Sort  (the order many people write first)
log.create_index([("course", 1), ("grade", 1), ("submitted_at", -1)], name="ers_course_grade_date")
plan_a = summarize("Query 2 - index order Equality, Range, Sort", query2().explain())
log.drop_index("ers_course_grade_date")

# Attempt B: Equality, Sort, Range  (ESR)
log.create_index([("course", 1), ("submitted_at", -1), ("grade", 1)], name="esr_course_date_grade")
plan_b = summarize("Query 2 - index order Equality, Sort, Range (ESR)", query2().explain())

scoreboard["Query 2: newest 10 high grades in Physics"] = {"before": plan_a, "after": plan_b}

print("\nERS needed SORT:", has_stage(plan_a, "SORT"))
print("ESR needed SORT:", has_stage(plan_b, "SORT"))
```

Both indexes contain the same three fields, yet they behave differently. With the range field (`grade`) before the sort field (`submitted_at`), index entries for one course are ordered by grade first, so dates are scattered and MongoDB must gather every match and sort in memory. With the sort field before the range field, entries come out already ordered by date, MongoDB walks them newest-first, checks the grade range as it goes, and stops after 10 matches. The ESR index may examine a few dozen index keys but avoids the blocking sort. Always confirm with `explain` that the trade works for your data.

**Snapshot — the documents are unchanged; only the indexes move. `ers_course_grade_date` was created and dropped again (🟥 deleted), `esr_course_date_grade` is 🟩 created and stays, the other indexes are ⬜ untouched.**

| | Index | Key order | Query 2 plan | Docs examined |
|---|---|---|---|---|
| ⬜ | `_id_` | (_id) | not used | |
| ⬜ | `esr_course_status_grade` | course, status, grade | not used by Query 2 | |
| 🟥 | `ers_course_grade_date` (dropped) | course, grade, submitted_at | `IXSCAN > FETCH > SORT` | 3,430 (every Physics document with grade 90 or more) |
| 🟩 | `esr_course_date_grade` | course, submitted_at, grade | `IXSCAN > FETCH` | a few dozen, no SORT (the Output section shows about 60, illustrative) |

The 10 documents Query 2 returns are 🟦 matched. The newest three (computed from the data) are:

| | student_id | grade | submitted_at |
|---|---|---|---|
| 🟦 | STU00716 | 99 | 2026-04-23 22:30 |
| 🟦 | STU02713 | 95 | 2026-04-23 18:59 |
| 🟦 | STU00259 | 90 | 2026-04-23 17:49 |
| 🟦 | … 7 more documents | | |

---

### Step 7 — A Covered Query: Answer from the Index Alone

```python
covered_filter = {"course": "Biology", "status": "completed"}
covered_projection = {"_id": 0, "course": 1, "status": 1, "grade": 1}

# Uses the index from Step 5 (course, status, grade)
cov_plan = summarize("Covered query",
                     log.find(covered_filter, covered_projection).explain())

uncovered_plan = summarize("Same filter, but returning extra fields",
                           log.find(covered_filter, {"_id": 0, "course": 1, "status": 1, "grade": 1, "notes": 1}).explain())

scoreboard["Covered query: Biology completed"] = {"before": uncovered_plan, "after": cov_plan}

print("\nCovered query read", cov_plan["docs"], "documents")
```

A query is covered when the filter fields and the returned fields all live in one index and `_id` is excluded. Here MongoDB answers from the index alone (`PROJECTION_COVERED`, zero documents examined). Asking for one extra field (`notes`) that is not in the index forces a `FETCH` of every matching document. Covered queries are the fastest queries you can write, but only worth designing for when the query is hot.

**Snapshot — no data changes. The 5,078 Biology + completed documents are 🟦 matched in both queries; the difference is how they are read. The documents are ⬜ untouched, and the plan with `notes` is shown as the slower one.**

| | Query | Plan | Docs examined | Keys examined | Returned |
|---|---|---|---|---|---|
| ⬜ | with `notes` (extra field) | `IXSCAN > FETCH` | 5,078 | 5,078 | 5,078 |
| 🟦 | covered (course, status, grade only) | `IXSCAN > PROJECTION_COVERED` | 0 | 5,078 | 5,078 |

Counts are computed from the seed-42 data (the Output section rounds this to 5,000).

---

### Step 8 — Measure What Indexes Cost

```python
# Storage: size of the data and of each index
stats = db.command("collStats", "enrollment_log")
print(f"Data size:   {stats['size'] / 1_048_576:.1f} MB")
for name, size in stats["indexSizes"].items():
    print(f"  index {name:<28} {size / 1_048_576:.2f} MB")

# Write cost: time the same 5,000 inserts with and without our indexes
def timed_insert(collection, count=5_000):
    docs = [make_record(N + i) for i in range(count)]
    start = time.perf_counter()
    collection.insert_many(docs)
    return (time.perf_counter() - start) * 1000

scratch = db["enrollment_scratch"]
scratch.drop()
ms_plain = timed_insert(scratch)                 # only the _id index
scratch.drop()

ms_indexed = timed_insert(log)                   # _id plus our two compound indexes
log.delete_many({"record_id": {"$gte": N}})      # remove the 5,000 test rows again

print(f"\n5,000 inserts, _id index only:      {ms_plain:7.0f} ms")
print(f"5,000 inserts, with 3 indexes:       {ms_indexed:7.0f} ms")
```

Every index is a second copy of part of your data that must be kept in sync. The first block reports how many megabytes each index occupies. The second block times the same 5,000 inserts into a plain collection and into `enrollment_log`. Network time is included in both numbers, so the difference is modest at this scale; on a busy production system with many indexes it becomes significant. The `delete_many` afterwards restores the collection to exactly 100,000 documents so later steps give consistent results.

**Snapshot — `enrollment_log` after the timed insert and the clean-up: 5,000 test documents were 🟩 inserted and then 🟥 deleted (shown once here), so the 100,000 original documents are ⬜ untouched and the final total is 100,000. The scratch collection is created and dropped on the side.**

| | record_id | student_id | course | status | grade |
|---|---|---|---|---|---|
| ⬜ | 0 to 99,999 (original data) | as in Step 2 | | | |
| ⬜ | … 99,994 more original documents | | | | |
| 🟥 | 100,000 to 104,999 (5,000 test rows, random values) | random | random | random | random |

---

### Step 9 — Find and Drop an Unused Index

```python
# Create an index nobody will use
log.create_index([("notes", 1)], name="idx_notes_unused")

# Run a few normal queries so the other indexes get used
list(query1()); list(query2())
list(log.find({"course": "English", "status": "pending"}).limit(5))

usage = list(log.aggregate([{"$indexStats": {}}]))
print(f"{'Index':<28} {'Times used':>10}")
for entry in usage:
    print(f"{entry['name']:<28} {entry['accesses']['ops']:>10}")

unused = [e["name"] for e in usage if e["accesses"]["ops"] == 0 and e["name"] != "_id_"]
print("\nUnused indexes:", unused)

for name in unused:
    log.drop_index(name)
    print("Dropped:", name)
```

`$indexStats` returns one row per index with `accesses.ops`, the number of times the index was used since the server started. An index that stays at `0` after representative traffic is costing storage and write time for nothing. In production you would check this over days or weeks, not seconds, because the counter resets on restart and a rarely-run monthly report may legitimately use an index only once a month.

**Snapshot — the documents are unchanged; the index list changes. `idx_notes_unused` is 🟩 created and then 🟥 dropped (shown once), the other indexes are ⬜ kept, and 🟦 marks the indexes the sample queries used.**

| | Index | Used by the sample queries | Result |
|---|---|---|---|
| ⬜ | `_id_` | not needed | kept (never dropped) |
| 🟦 | `esr_course_status_grade` | Query 1, and the English + pending query | kept |
| 🟦 | `esr_course_date_grade` | Query 2 | kept |
| 🟥 | `idx_notes_unused` on (notes 1) | no query filters on `notes`, so `accesses.ops` is 0 | dropped |

---

### Step 10 — Speed Up an Aggregation

```python
def explain_aggregate(pipeline):
    report = db.command({
        "explain": {"aggregate": "enrollment_log", "pipeline": pipeline, "cursor": {}},
        "verbosity": "executionStats",
    })
    # Pipelines with a $group report a "stages" list; the first stage holds the cursor plan
    return report["stages"][0]["$cursor"] if "stages" in report else report

def timed_aggregate(pipeline):
    start = time.perf_counter()
    result = list(log.aggregate(pipeline))
    return result, (time.perf_counter() - start) * 1000

group_stage = {"$group": {"_id": "$course", "avg_grade": {"$avg": "$grade"}, "n": {"$sum": 1}}}

# Slow: group everything, then look at the result
pipeline_all = [group_stage, {"$sort": {"avg_grade": -1}}]

# Fast: an indexed $match first, so $group only sees one slice
log.create_index([("semester", 1), ("status", 1)], name="idx_semester_status")
pipeline_slice = [
    {"$match": {"semester": "2026-Spring", "status": "completed"}},
    group_stage,
    {"$sort": {"avg_grade": -1}},
]

plan_all   = summarize("Aggregation - all documents", explain_aggregate(pipeline_all))
plan_slice = summarize("Aggregation - indexed $match first", explain_aggregate(pipeline_slice))

_, ms_all   = timed_aggregate(pipeline_all)
_, ms_slice = timed_aggregate(pipeline_slice)
print(f"\nClient-side timing: all = {ms_all:.0f} ms | sliced = {ms_slice:.0f} ms")

scoreboard["Aggregation: average per course"] = {"before": plan_all, "after": plan_slice}
```

Only the first stages of a pipeline can use an index. Starting with `$match` on indexed fields lets MongoDB read just the matching slice (`IXSCAN`) and hand a much smaller stream to `$group`. A pipeline that starts with `$group` has no choice but to read everything. The two pipelines answer slightly different questions (all data versus one semester and status), which is the point: if the business question only needs a slice, ask for the slice. MongoDB also reorders some stages automatically, so always check `explain` instead of assuming.

**Snapshot — the documents are unchanged; one index is 🟩 added (`idx_semester_status`). The 6,084 documents with semester 2026-Spring and status completed are 🟦 matched by the second pipeline, the earlier indexes are ⬜ untouched, and the first pipeline is shown as the slow one.**

| | Pipeline | Plan at the start | Docs examined |
|---|---|---|---|
| ⬜ | `$group` on everything | `COLLSCAN` | 100,000 |
| 🟦 | `$match` on semester + status, then `$group` | `IXSCAN` on `idx_semester_status` | 6,084 |

Counts are computed from the seed-42 data (the Output section shows about 6,250, illustrative).

---

### Step 11 — Try the Profiler (Where Your Tier Allows It)

```python
try:
    db.command("profile", 1, slowms=20)           # log operations slower than 20 ms
    list(log.find({"notes": "x" * 40}).limit(1))  # a deliberately unindexed query
    slow = list(db["system.profile"].find({"ns": "school_db.enrollment_log"}).sort("ts", -1).limit(3))
    for op in slow:
        print(op.get("millis"), "ms |", op.get("planSummary"), "|", op.get("command", {}).get("filter"))
    db.command("profile", 0)                      # always switch it back off
    print("\nProfiler works on this cluster.")
except pymongo.errors.OperationFailure as err:
    print("Profiler is not available on this cluster tier.")
    print("Reason:", err.details.get("errmsg", str(err)) if err.details else err)
    print("Use Atlas > your cluster > Query Insights / Performance Advisor instead.")
```

The database profiler records every operation slower than a threshold, including its plan summary (`COLLSCAN` or `IXSCAN ...`). It is how you find slow queries you did not know about. Free and shared Atlas tiers refuse the `profile` command, so the cell catches the error and points you to Atlas's Query Insights and Performance Advisor, which perform the same job through the web interface on paid tiers.

---

### Step 12 — The Before / After Scoreboard

```python
print(f"{'Case':<44} {'Docs examined':>22} {'SORT stage':>14}")
print("-" * 82)
for case, result in scoreboard.items():
    b, a = result["before"], result["after"]
    docs = f"{b['docs']:>8} -> {a['docs']:<8}"
    sort = f"{'yes' if has_stage(b, 'SORT') else 'no':>4} -> {'yes' if has_stage(a, 'SORT') else 'no':<4}"
    print(f"{case:<44} {docs:>22} {sort:>14}")

print("\nFinal indexes on enrollment_log:")
for name, info in log.index_information().items():
    print(" ", name, info["key"])
```

This collects every experiment into one table. The pattern to remember is the loop you just followed: measure with `explain`, diagnose from `docs examined` versus `returned` and from the presence of `SORT`, change one thing, and measure again.

**Snapshot — read-only listing of the indexes left on `enrollment_log`: all four are ⬜ untouched by this step (`idx_notes_unused` is gone, `ers_course_grade_date` is gone). The 100,000 documents are unchanged.**

| | Index | Keys |
|---|---|---|
| ⬜ | `_id_` | _id |
| ⬜ | `esr_course_status_grade` | course, status, grade (descending) |
| ⬜ | `esr_course_date_grade` | course, submitted_at (descending), grade |
| ⬜ | `idx_semester_status` | semester, status |

---

# What We Learnt

- **`explain("executionStats")` tells you the truth about a query** — compare `totalDocsExamined` and `totalKeysExamined` to `nReturned`; a large gap means wasted work.
- **`COLLSCAN` + `SORT` is the classic slow plan**; an index that matches the filter and the sort removes both.
- **The ESR rule orders compound index fields: Equality, Sort, Range.** A range field placed before the sort field forces an in-memory `SORT`.
- **Covered queries read zero documents** when every filtered and returned field is in one index and `_id` is excluded.
- **Indexes cost storage and write speed**; `collStats` shows their size and `$indexStats` shows whether they are ever used.
- **Only the leading stages of an aggregation can use an index** — start with an indexed `$match`.
- **The profiler and Performance Advisor find slow queries in production**, but they need a paid Atlas tier; `explain` works on every tier.
- **Optimize by loop, not by guess:** measure, diagnose, change one thing, measure again.

You can now read an `explain` plan, design compound indexes with the Equality-Sort-Range rule, build covered queries, weigh index cost against benefit, and clean up indexes that are not earning their keep.
