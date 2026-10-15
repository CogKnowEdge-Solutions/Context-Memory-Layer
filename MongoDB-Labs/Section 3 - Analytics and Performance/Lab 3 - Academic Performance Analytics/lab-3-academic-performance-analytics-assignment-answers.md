# Assignment Answers - How to Analyze Data at Scale

Sample answers for the tasks. Your wording and code may differ; what matters is that the result is right.

---

## Task 1

```python
for row in students.aggregate([{"$group": {"_id": "$course", "students": {"$sum": 1}}}]):
    print(row)
```

## Task 2

```python
pipeline = [
    {"$group": {"_id": "$course", "avg_grade": {"$avg": "$grade"}}},
    {"$sort": {"avg_grade": -1}}
]
for row in students.aggregate(pipeline):
    print(row)
```

## Task 3

```python
pipeline = [{"$group": {"_id": "$course", "highest": {"$max": "$grade"}, "lowest": {"$min": "$grade"}}}]
for row in students.aggregate(pipeline):
    print(row)
```

## Task 4

```python
pipeline = [
    {"$group": {"_id": "$course", "avg_grade": {"$avg": "$grade"}}},
    {"$match": {"avg_grade": {"$gt": 75}}}
]
for row in students.aggregate(pipeline):
    print(row)
```
The average only exists after `$group`, so `$match` comes after it.

## Task 5

```python
pipeline = [
    {"$match": {"status": "active"}},
    {"$group": {"_id": "$course", "avg_grade": {"$avg": "$grade"}}}
]
for row in students.aggregate(pipeline):
    print(row)
```
Filtering first means fewer documents reach the grouping step.

## Task 6

```python
pipeline = [{"$bucket": {"groupBy": "$grade", "boundaries": [0, 60, 70, 80, 90, 101],
                         "default": "other", "output": {"count": {"$sum": 1}}}}]
for row in students.aggregate(pipeline):
    print(row)
```
Each bucket includes its lower boundary and excludes its upper one, so the last boundary is 101 to include a grade of 100.

## Task 7

```python
for row in students.aggregate([{"$group": {"_id": "$status", "count": {"$sum": 1}}}]):
    print(row)
```

## Task 8

```python
stats = students.find({"course": "Physics"}).explain()["executionStats"]
print(stats["totalDocsExamined"], stats["nReturned"])
```
Without an index, MongoDB examines every document in the collection.

## Task 9

```python
students.create_index("course")
stats = students.find({"course": "Physics"}).explain()["executionStats"]
print(stats["totalDocsExamined"], stats["nReturned"])
```
With the index, `totalDocsExamined` drops to about the number of Physics students, because MongoDB jumps straight to them instead of scanning everything.
