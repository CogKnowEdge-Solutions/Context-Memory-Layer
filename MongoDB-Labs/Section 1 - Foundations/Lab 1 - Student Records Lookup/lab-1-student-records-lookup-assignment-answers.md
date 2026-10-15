# Assignment Answers - How to Query Data

Sample answers for the tasks. Your wording and code may differ; what matters is that the result is right.

---

## Task 1

```python
print(students.count_documents({}))
```

## Task 2

```python
for s in students.find({"course": "Computer Science"}, {"_id": 0, "name": 1, "grade": 1}):
    print(s["name"], s["grade"])
```

## Task 3

```python
for s in students.find({"grade": {"$lt": 60}}):
    print(s["name"])
```
`$lt` means less than.

## Task 4

```python
for s in students.find({"grade": {"$gte": 70, "$lte": 80}}, {"_id": 0, "name": 1, "course": 1, "grade": 1}):
    print(s)
```
`$gte` is greater than or equal, `$lte` is less than or equal. In a projection, `1` shows a field and `0` hides it.

## Task 5

```python
for s in students.find({"status": "inactive"}, {"_id": 0}).sort("enrollment_date", 1):
    print(s)
```
`1` sorts from smallest to largest, so the earliest dates come first.

## Task 6

```python
for s in students.find({}, {"_id": 0, "name": 1, "grade": 1}).sort("grade", -1).limit(3):
    print(s)
```

## Task 7

```python
for row in students.aggregate([{"$group": {"_id": "$course", "count": {"$sum": 1}}}]):
    print(row["_id"], row["count"])
```
`$group` collects the students of each course, and `$sum: 1` adds one for each student.

## Task 8

```python
pipeline = [
    {"$group": {"_id": "$course", "avg_grade": {"$avg": "$grade"}}},
    {"$sort": {"avg_grade": -1}}
]
for row in students.aggregate(pipeline):
    print(row["_id"], round(row["avg_grade"], 1))
```

## Task 9

```python
students.insert_one({"name": "Your Name", "student_id": "STU900", "course": "Physics",
                    "grade": 85, "enrollment_date": "2025-01-10", "status": "active"})
print(students.find_one({"student_id": "STU900"}, {"_id": 0}))
```
Use any values you like; the point is that `find_one` returns the record you just saved.
