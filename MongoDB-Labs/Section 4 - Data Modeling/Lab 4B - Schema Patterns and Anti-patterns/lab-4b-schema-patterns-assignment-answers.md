# Assignment Answers - How to Recognize Schema Patterns

Sample answers for the tasks. Your wording and code may differ; what matters is that the result is right.

---

## Task 1

```python
import bson
fat = db["pat_students_fat"].find_one()
slim = db["pat_students"].find_one()
print(len(bson.encode(fat)), len(bson.encode(slim)))
```
The fat document is much larger because it stores the whole grade history inside it.

## Task 2

The maximum size of one MongoDB document is 16 MB (16 MiB).

## Task 3

```python
print(db["pat_grade_history"].count_documents({"student_id": "STU00001"}))
print(len(db["pat_students"].find_one({"_id": "STU00001"})["recent_grades"]))
```
The full history lives in its own collection, while the student document keeps only a small recent subset (the subset pattern).

## Task 4

```python
for g in db["pat_grade_history"].find({"student_id": "STU00001"}).sort("seq", -1).limit(5):
    print(g)
```

## Task 5

```python
new_entry = {"course": "CS101", "grade": 88}
db["pat_students"].update_one(
    {"_id": "STU00001"},
    {"$push": {"recent_grades": {"$each": [new_entry], "$slice": -3}}}
)
print(db["pat_students"].find_one({"_id": "STU00001"})["recent_grades"])
```
`$slice: -3` keeps only the last three items. Use the fields your documents already use for a grade entry.

## Task 6

```python
db["pat_students"].update_one({"_id": "STU00002"}, {"$inc": {"quiz_count": 1, "quiz_sum": 85}})
doc = db["pat_students"].find_one({"_id": "STU00002"})
print(doc["quiz_sum"] / doc["quiz_count"])
```
This is the computed pattern: the counters are updated on every write, so the average needs no scan of the history.

## Task 7

```python
for reading in ({"t": "10:01", "temp": 21.4}, {"t": "10:02", "temp": 21.6}):
    db["sensor_buckets"].update_one(
        {"sensor": "S7", "date": "2026-09-01"},
        {"$push": {"readings": reading},
         "$inc": {"reading_count": 1, "temp_sum": reading["temp"]}},
        upsert=True)
print(db["sensor_buckets"].find_one({"sensor": "S7"}))
```
This is the bucket pattern: one document holds one day of readings for one sensor, so there is one document per day instead of 1,440.

## Task 8

```python
db["orders_demo"].insert_one({"order_id": "O1", "customer_id": "C1",
                              "customer_name": "Asha Rao", "city": "Pune", "total": 250})
print(db["orders_demo"].find_one({"order_id": "O1"}, {"_id": 0}))
```
This is the extended reference pattern: only the few fields the page needs are copied.

## Task 9

```python
result = db["orders_demo"].update_many({"customer_id": "C1"}, {"$set": {"city": "Mumbai"}})
print(result.modified_count)
```
In a real system you would first update the `customers` collection, which is the source of truth, and then the copies.

## Task 10

This is the unbounded array anti-pattern: the document keeps growing, becomes slow to read and update, and can eventually reach the 16 MB limit. The fix is to store each comment as its own document in a `comments` collection with the post's id, and to keep only a few recent comments in the post if the page needs them.
