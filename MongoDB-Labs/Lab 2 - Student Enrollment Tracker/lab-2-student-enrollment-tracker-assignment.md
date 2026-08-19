# MongoDB Basics: How to Write, Update & Delete Data

## Student Enrollment Tracker — Assignment

Test your understanding of MongoDB write operations by answering the following questions and completing the short code tasks.

---

## Exercises

### Exercise 1 — Concept Question
What is the difference between `$set` and `$inc` in a MongoDB update operation? Give one example of when you would use each.

### Exercise 2 — Code Task
Write a `pymongo` operation that uses `update_many()` to add an `"email"` field with the value `"unknown@university.edu"` to **all** students in the `"Physics"` course. Print how many documents were modified.

### Exercise 3 — Concept Question
What does `upsert=True` do in an `update_one()` call? Describe a real scenario in a university system where an upsert is the right choice.

### Exercise 4 — Code Task
Write a `pymongo` operation that uses `update_one()` with `$inc` to add **10 points** to the grade of the student named `"Laura Palmer"`. After the update, query her record and print the new grade.

### Exercise 5 — Code Task
Write a `pymongo` operation that uses `find_one_and_delete()` to remove the student whose `student_id` is `"STU010"`. Print the name of the deleted student.

### Exercise 6 — Concept Question
What is the difference between `delete_one()` and `delete_many()`? What happens if `delete_one()` matches multiple documents?

### Exercise 7 — Applied Task
Write a three-step sequence: (1) use `update_one()` to set `"status": "inactive"` for the student named `"Sam Wilson"`, (2) use `delete_one()` to remove the student with the **lowest grade** in the collection, and (3) use `count_documents({})` to verify the total number of remaining students. Print the result of each step.

---

## Answer Key

### Exercise 1
`$set` assigns a specific value to a field — it either creates the field if it doesn't exist, or overwrites it if it does. `$inc` adds a numeric value to an existing field. Use `$set` when you're assigning a new value (e.g., `{"$set": {"email": "alice@uni.edu"}}`). Use `$inc` when you're adjusting a number without reading the current value first (e.g., `{"$inc": {"grade": 5}}`).

### Exercise 2
```python
result = students.update_many(
    {"course": "Physics"},
    {"$set": {"email": "unknown@university.edu"}}
)
print(f"Modified {result.modified_count} document(s)")
```
The filter `{"course": "Physics"}` targets only Physics students. `$set` adds the `email` field to each matching document.

### Exercise 3
With `upsert=True`, if the filter matches a document, it updates it. If nothing matches, MongoDB **inserts a new document** combining the filter fields and the update fields. A university scenario: re-enrolling a student who previously withdrew — the student may have been deleted or may still be in the database with `"inactive"` status. An upsert handles both cases in one call without needing to check first.

### Exercise 4
```python
result = students.update_one(
    {"name": "Laura Palmer"},
    {"$inc": {"grade": 10}}
)
laura = students.find_one({"name": "Laura Palmer"}, {"_id": 0})
print(f"Laura Palmer's new grade: {laura['grade']}")
```
`$inc` adds 10 to whatever Laura's current grade is, without needing to read it first.

### Exercise 5
```python
deleted = students.find_one_and_delete(
    {"student_id": "STU010"},
    projection={"_id": 0, "name": 1}
)
print(f"Deleted: {deleted['name']}")
```
`find_one_and_delete` finds the matching document, removes it, and returns the deleted document so you can confirm what was removed.

### Exercise 6
`delete_one()` removes **only the first** document that matches the filter, even if multiple documents match. `delete_many()` removes **every** document that matches. If `delete_one()` matches multiple documents, it still only deletes one — the rest are left untouched. Use `delete_many()` when you intentionally want to remove all matches.

### Exercise 7
```python
# Step 1: Set Sam Wilson to inactive
result = students.update_one(
    {"name": "Sam Wilson"},
    {"$set": {"status": "inactive"}}
)
print(f"Step 1: Updated Sam Wilson — modified_count = {result.modified_count}")

# Step 2: Delete the student with the lowest grade
lowest = students.find_one(sort=[("grade", 1)], projection={"_id": 0, "name": 1, "grade": 1})
if lowest:
    students.delete_one({"name": lowest["name"]})
    print(f"Step 2: Deleted {lowest['name']} (grade: {lowest['grade']})")

# Step 3: Verify total count
total = students.count_documents({})
print(f"Step 3: Total students remaining: {total}")
```
The sort `[("grade", 1)]` with ascending order puts the lowest grade first. `find_one()` returns just that document. After deletion, `count_documents({})` confirms the new total.
