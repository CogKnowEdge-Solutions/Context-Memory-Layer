# Assignment Answers - How to Guarantee Data Consistency

Sample answers for the tasks. Your wording and code may differ; what matters is that the result is right.

---

## Task 1

```python
for c in courses.find({}, {"_id": 0, "course_id": 1, "seats_available": 1}):
    print(c)
```

## Task 2

```python
print(courses.find_one({"course_id": "CS201"})["seats_available"])
with client.start_session() as session:
    session.with_transaction(lambda s: enroll_student(s, "CS201", "STU050", "Eve Torres"))
print(courses.find_one({"course_id": "CS201"})["seats_available"])
```
The seat count goes down by one, and the enrollment is saved in the same transaction.

## Task 3

```python
print(enrollments.find_one({"student_id": "STU050"}, {"_id": 0}))
```

## Task 4

```python
with client.start_session() as session:
    session.with_transaction(lambda s: enroll_student(s, "MATH101", "STU051", "Student A"))
with client.start_session() as session:
    session.with_transaction(lambda s: enroll_student(s, "MATH101", "STU052", "Student B"))
print(courses.find_one({"course_id": "MATH101"})["seats_available"])
```
The seats left are 0.

## Task 5

```python
try:
    with client.start_session() as session:
        session.with_transaction(lambda s: enroll_student(s, "MATH101", "STU053", "Student C"))
except Exception as e:
    print("Enrollment failed:", e)
```
The function raises an error such as "course is full", which stops the transaction.

## Task 6

```python
print(courses.find_one({"course_id": "MATH101"})["seats_available"])
print(enrollments.count_documents({"course_id": "MATH101"}))
```
The seats stay at 0 (never negative) and there are exactly 2 enrollments: the failed attempt left no trace.

## Task 7

```python
# Without a transaction (do not use in real code)
courses.update_one({"course_id": "CS101"}, {"$inc": {"seats_available": -1}})
enrollments.insert_one({"student_id": "STU060", "student_name": "No Txn", "course_id": "CS101"})
# If the program stops between these two lines, a seat is taken but nobody is enrolled.
```
A transaction makes both writes succeed together or not at all.

## Task 8

```python
with enrollments.watch() as stream:
    enrollments.insert_one({"student_id": "STU070", "student_name": "Stream Test", "course_id": "PHYS101"})
    event = next(stream)
    print(event["operationType"])
```
The event type is `insert`.

## Task 9

```python
print(event["fullDocument"]["student_name"])
```
For inserts the event carries the whole new document in `fullDocument`.
