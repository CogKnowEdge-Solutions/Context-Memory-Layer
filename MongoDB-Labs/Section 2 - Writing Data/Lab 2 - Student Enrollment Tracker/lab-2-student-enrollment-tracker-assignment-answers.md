# Assignment Answers - How to Write, Update & Delete Data

Sample answers for the tasks. Your wording and code may differ; what matters is that the result is right.

---

## Task 1

```python
before = students.count_documents({})
students.insert_one({"name": "Test One", "student_id": "STU026", "course": "English",
                    "grade": 70, "enrollment_date": "2025-01-10", "status": "active"})
print(before, students.count_documents({}))
```

## Task 2

```python
students.insert_many([
    {"name": "Test Two",   "student_id": "STU027", "course": "Physics",   "grade": 66, "enrollment_date": "2025-01-10", "status": "active"},
    {"name": "Test Three", "student_id": "STU028", "course": "Biology",   "grade": 81, "enrollment_date": "2025-01-10", "status": "active"},
    {"name": "Test Four",  "student_id": "STU029", "course": "Mathematics", "grade": 59, "enrollment_date": "2025-01-10", "status": "active"},
])
print(students.count_documents({}))
```
`insert_many` takes a list and saves all of it in one call.

## Task 3

```python
students.update_one({"student_id": "STU012"}, {"$set": {"status": "inactive"}})
print(students.find_one({"student_id": "STU012"})["status"])
```
`$set` replaces the value of a field.

## Task 4

```python
students.update_one({"student_id": "STU012"}, {"$inc": {"grade": 5}})
print(students.find_one({"student_id": "STU012"})["grade"])
```
`$inc` adds a number to the current value (use a negative number to subtract).

## Task 5

```python
result = students.update_many({"course": "Physics"}, {"$set": {"email": "unknown@university.edu"}})
print(result.modified_count)
```

## Task 6

The first run finds no student with that id, so `upsert=True` creates one. The second run finds the student it created, so it only updates it. The count stays at 1 because an upsert never creates a second copy.

```python
for _ in range(2):
    students.update_one({"student_id": "STU999"},
                        {"$set": {"name": "Test Student", "course": "English"}},
                        upsert=True)
    print(students.count_documents({"student_id": "STU999"}))
```

## Task 7

```python
from pymongo import ReturnDocument

doc = students.find_one_and_update({"student_id": "STU001"}, {"$inc": {"grade": 3}},
                                   return_document=ReturnDocument.AFTER)
print(doc["grade"])
```
The change and the read happen in one step, so nothing can change in between.

## Task 8

```python
result = students.delete_one({"student_id": "STU999"})
print(result.deleted_count)
```

## Task 9

```python
result = students.delete_many({"status": "inactive"})
print(result.deleted_count, students.count_documents({}))
```
`delete_one` removes only the first match; `delete_many` removes every match.
