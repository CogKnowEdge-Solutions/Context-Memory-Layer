# Lab 1 — Student Records Lookup System: Assignment

Test your understanding of MongoDB basics by answering the following questions and completing the short code tasks.

---

## Exercises

### Exercise 1 — Concept Question
What is the key difference between a **document database** (like MongoDB) and a **relational database** (like MySQL)? Give one example of when a document database is a better fit.

### Exercise 2 — Code Task
Write a `pymongo` query that finds all students whose grade is **between 70 and 80 inclusive** (i.e., `70 <= grade <= 80`). Include only the `name`, `course`, and `grade` fields in the results (exclude `_id`).

### Exercise 3 — Concept Question
What does the `{"_id": 0}` projection do in a MongoDB `find()` call? Why did we use it in this lab?

### Exercise 4 — Code Task
Write an aggregation pipeline that calculates the **average grade** for each course. The output should show the course name and its average grade, sorted by average grade descending.

### Exercise 5 — Code Task
Write a query that finds all students with status `"inactive"`, sorted by `enrollment_date` in ascending order (earliest first).

### Exercise 6 — Concept Question
What is the difference between `insert_one()` and `insert_many()`? When would you use each?

### Exercise 7 — Applied Task
Imagine you need to add a new field `"email"` to every student document. Write the MongoDB operation (using `update_many()`) that adds `"email": "unknown@example.com"` to **all** documents in the `students` collection.

---

## Answer Key

### Exercise 1
A **relational database** stores data in fixed-schema tables where every row has the same columns. A **document database** stores data as flexible JSON-like documents where each record can have different fields. A document database is a better fit when the data shape varies across records — for example, student profiles where some have scholarships and others don't, without needing to alter a table schema.

### Exercise 2
```python
results = students.find(
    {"grade": {"$gte": 70, "$lte": 80}},
    {"_id": 0, "name": 1, "course": 1, "grade": 1}
)
for s in results:
    print(s)
```
`$gte` means "greater than or equal to" and `$lte` means "less than or equal to." The projection `{"_id": 0, "name": 1, "course": 1, "grade": 1}` explicitly excludes `_id` and includes the three requested fields.

### Exercise 3
`{"_id": 0}` tells MongoDB to **exclude** the auto-generated `_id` field from the results. MongoDB adds an `_id` to every document by default; since it's an internal identifier with no meaning to us, we hide it to keep the output clean and focused on the fields we care about.

### Exercise 4
```python
pipeline = [
    {"$group": {"_id": "$course", "avg_grade": {"$avg": "$grade"}}},
    {"$sort": {"avg_grade": -1}}
]
results = students.aggregate(pipeline)
for doc in results:
    print(f"{doc['_id']}: {doc['avg_grade']:.1f}")
```
`$avg` is an accumulator that computes the mean of the `grade` field within each group. `$sort` with `-1` orders highest average first.

### Exercise 5
```python
results = students.find(
    {"status": "inactive"},
    {"_id": 0}
).sort("enrollment_date", 1)  # 1 = ascending
for s in results:
    print(s)
```
Using `1` for ascending order puts the earliest enrollment dates first.

### Exercise 6
`insert_one(document)` inserts a **single** document (one dictionary). `insert_many(documents)` inserts a **list** of documents in one call. Use `insert_one()` when adding a single record (e.g., a new student enrolling mid-semester). Use `insert_many()` when you have a batch of records to add at once (e.g., importing a semester's worth of enrollment data).

### Exercise 7
```python
students.update_many(
    {},  # empty filter = match ALL documents
    {"$set": {"email": "unknown@example.com"}}
)
```
The empty filter `{}` matches every document. `$set` adds or updates the specified field. After this operation, every student document will contain an `email` field with the value `"unknown@example.com"`.
