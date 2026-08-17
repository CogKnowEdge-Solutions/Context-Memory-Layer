# Lab 2 — MongoDB Basics: How to Write, Update & Delete Data — Assignment

Test your understanding of MongoDB write operations by answering the following questions and completing the short code tasks.

---

## Exercises

### Exercise 1 — Concept Question
What is the difference between `insert_one()` and `insert_many()`? When would you use each in a real application?

### Exercise 2 — Code Task
Write a MongoDB query that finds all tasks with `"priority"` set to `"critical"` AND `"status"` set to `"pending"`. Include only the `title`, `priority`, and `due_date` fields (exclude `_id`).

### Exercise 3 — Concept Question
What does the `$set` operator do in an `update_one()` call? Why not just replace the entire document with a new dictionary?

### Exercise 4 — Code Task
Write an `update_many()` call that sets `"priority": "low"` on every task in the `"learning"` category. Show how many documents were matched and modified.

### Exercise 5 — Concept Question
Explain what happens when you run an `update_one()` with `upsert=True` and the filter matches an existing document. What about when no document matches?

### Exercise 6 — Code Task
Write a `delete_many()` call that removes all tasks with `"priority": "low"`. Print the number of deleted tasks.

### Exercise 7 — Applied Task
Imagine you need to add a new field `"assigned_to"` to every task document. Write the MongoDB operation (using `update_many()`) that adds `"assigned_to": "unassigned"` to all documents in the `tasks` collection.

---

## Answer Key

### Exercise 1
`insert_one(document)` inserts a **single** document (one dictionary). `insert_many(documents)` inserts a **list** of documents in one call. Use `insert_one()` when adding a single record (e.g., a user creates a new task through a form). Use `insert_many()` when you have a batch of records to add at once (e.g., importing a CSV of initial tasks).

### Exercise 2
```python
results = tasks.find(
    {"priority": "critical", "status": "pending"},
    {"_id": 0, "title": 1, "priority": 1, "due_date": 1}
)
for t in results:
    print(t)
```
Multiple filter conditions separated by commas in the filter dictionary act as AND logic. The projection `{"_id": 0, "title": 1, "priority": 1, "due_date": 1}` explicitly excludes `_id` and includes the three requested fields.

### Exercise 3
`$set` updates **only the specified fields**, leaving all other fields untouched. If you replaced the entire document, any fields not in the new dictionary would be lost. `$set` is safer because it preserves existing data while making the intended changes.

### Exercise 4
```python
result = tasks.update_many(
    {"category": "learning"},
    {"$set": {"priority": "low"}}
)
print(f"Matched {result.matched_count}, modified {result.modified_count}")
```
The filter matches all documents where `category` is `"learning"`, and `$set` changes only the `priority` field.

### Exercise 5
When the filter matches an existing document, MongoDB **updates** that document with the fields from the `$set` operation — `matched_count` is 1 and `modified_count` is 1 (if the value actually changed). When no document matches, MongoDB **inserts** a new document containing the filter fields plus the `$set` fields — `matched_count` is 0, `modified_count` is 0, and `upserted_id` contains the `_id` of the newly inserted document.

### Exercise 6
```python
result = tasks.delete_many({"priority": "low"})
print(f"Deleted {result.deleted_count} tasks.")
```
`delete_many()` removes all documents matching the filter. `deleted_count` tells you how many were actually removed.

### Exercise 7
```python
tasks.update_many(
    {},  # empty filter = match ALL documents
    {"$set": {"assigned_to": "unassigned"}}
)
```
The empty filter `{}` matches every document. `$set` adds or updates the specified field. After this operation, every task document will contain an `assigned_to` field with the value `"unassigned"`.
