# MongoDB Intermediate: How to Analyze Data at Scale

## Academic Performance Analytics — Assignment

Test your understanding of aggregation pipelines and indexing by answering the following questions and completing the short code tasks.

---

## Exercises

### Exercise 1 — Concept Question
What is the difference between a **simple query** (`find()`) and an **aggregation pipeline** (`aggregate()`)? When would you choose one over the other?

### Exercise 2 — Code Task
Write an aggregation pipeline that finds the **highest grade** in each course. The output should show the course name and the maximum grade, sorted by maximum grade descending.

### Exercise 3 — Concept Question
What does the `$bucket` stage do in an aggregation pipeline? Explain what the `boundaries` and `output` parameters control.

### Exercise 4 — Code Task
Write an aggregation pipeline that calculates the **average grade per course**, but only for courses where the average is **above 75**. Use `$match` after `$group` to filter the grouped results.

### Exercise 5 — Concept Question
What is the difference between `IXSCAN` and `COLLSCAN` in a `.explain()` output? Which one indicates that an index is being used?

### Exercise 6 — Code Task
Write the pymongo command to create a **compound index** on the `status` and `grade` fields (in that order). Then write a query that finds all active students with a grade above 80, sorted by grade descending.

### Exercise 7 — Applied Task
You are asked to build a semester-end report that shows, for each course: (1) the number of students enrolled, (2) the average grade, (3) the highest grade, and (4) the lowest grade. Write a single aggregation pipeline that produces this report, sorted by average grade descending.

### Exercise 8 — Concept Question
Why does creating an index slow down `insert_one()` and `update_one()` operations? Explain the tradeoff in practical terms.

---

## Answer Key

### Exercise 1
A `find()` query returns raw documents that match a filter — it can filter, project, and sort, but it cannot compute new values or group documents. An `aggregation pipeline` can do everything `find()` does, plus compute aggregations (averages, counts, sums), reshape documents, group by fields, and chain multiple transformations. Use `find()` for simple retrieval; use `aggregate()` when you need to compute or transform data.

### Exercise 2
```python
pipeline = [
    {"$group": {"_id": "$course", "max_grade": {"$max": "$grade"}}},
    {"$sort": {"max_grade": -1}}
]
results = students.aggregate(pipeline)
for doc in results:
    print(f"{doc['_id']}: {doc['max_grade']}")
```
`$max` is an accumulator that returns the highest value within each group. `$sort` with `-1` orders highest maximum first.

### Exercise 3
`$bucket` distributes documents into predefined ranges based on a field's value. The `boundaries` parameter is a sorted list of inclusive lower bounds — each consecutive pair defines a bucket (e.g., `[0, 60, 70]` creates buckets 0–59 and 60–69). The `output` parameter defines what to compute for each bucket — here, `{"count": {"$sum": 1}}` counts documents in each range.

### Exercise 4
```python
pipeline = [
    {"$group": {"_id": "$course", "avg_grade": {"$avg": "$grade"}}},
    {"$match": {"avg_grade": {"$gt": 75}}},
    {"$sort": {"avg_grade": -1}}
]
results = students.aggregate(pipeline)
for doc in results:
    print(f"{doc['_id']}: {doc['avg_grade']:.1f}")
```
The `$match` after `$group` filters on the **computed** `avg_grade` field (not the raw `grade` field). This is the pipeline equivalent of SQL's `HAVING` clause.

### Exercise 5
`IXSCAN` means MongoDB performed an **index scan** — it used an index to locate matching documents, which is fast. `COLLSCAN` means MongoDB performed a **collection scan** — it read every document in the collection to find matches, which is slow for large collections. `IXSCAN` indicates an index is being used.

### Exercise 6
```python
students.create_index([("status", 1), ("grade", 1)])

results = students.find(
    {"status": "active", "grade": {"$gt": 80}},
    {"_id": 0}
).sort("grade", -1)
for s in results:
    print(s)
```
A compound index on `[("status", 1), ("grade", 1)]` supports queries that filter on `status` alone, `status` + `grade`, or `status` + `grade` with a sort — but not `grade` alone (the index fields must be used from left to right).

### Exercise 7
```python
pipeline = [
    {"$group": {
        "_id": "$course",
        "count": {"$sum": 1},
        "avg_grade": {"$avg": "$grade"},
        "max_grade": {"$max": "$grade"},
        "min_grade": {"$min": "$grade"}
    }},
    {"$sort": {"avg_grade": -1}}
]
results = students.aggregate(pipeline)
for doc in results:
    print(f"{doc['_id']}: {doc['count']} students, avg {doc['avg_grade']:.1f}, "
          f"high {doc['max_grade']}, low {doc['min_grade']}")
```
`$sum: 1` counts documents in each group, `$avg` computes the mean, `$max` and `$min` find the extremes. All four accumulators run in a single `$group` stage.

### Exercise 8
Every index must be updated whenever a document is inserted, updated, or deleted — MongoDB has to add, remove, or modify the index entry alongside the actual document change. This means writes are slower with more indexes because MongoDB does more work per write. The tradeoff is that reads (queries) are faster because MongoDB can use the index to find documents without scanning the full collection. The right balance depends on your workload: a read-heavy application benefits from more indexes; a write-heavy application benefits from fewer.
