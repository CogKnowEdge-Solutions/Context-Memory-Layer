# Assignment Answers - How to Make Queries Fast

Sample answers for the tasks. Your wording and code may differ; what matters is that the result is right.

---

## Task 1

```python
print(log.count_documents({}))
```

## Task 2

```python
e = log.find({"course": "Physics", "status": "active"}).explain()["executionStats"]
print(e["nReturned"], e["totalKeysExamined"], e["totalDocsExamined"])
```
Without an index, `totalDocsExamined` equals the size of the collection (100,000).

## Task 3

```python
log.create_index([("course", 1), ("status", 1)])
e = log.find({"course": "Physics", "status": "active"}).explain()["executionStats"]
print(e["nReturned"], e["totalKeysExamined"], e["totalDocsExamined"])
```
Now both examined numbers are close to `nReturned`: MongoDB goes straight to the matching entries instead of reading everything.

## Task 4

```python
log.create_index([("semester", 1), ("status", 1), ("grade", -1)], name="sem_status_grade")
```
The two equality fields come first and the sort field last (the ESR rule: Equality, Sort, Range).

## Task 5

```python
q = log.find({"semester": "2025-Fall", "status": "active"}).sort("grade", -1).limit(50)
plan = q.explain()
print("SORT" in str(plan["queryPlanner"]["winningPlan"]))
```
This prints `False`: the index already returns the rows in grade order.

## Task 6

```python
log.create_index([("grade", -1), ("semester", 1), ("status", 1)], name="bad_order")
q = log.find({"semester": "2025-Fall", "status": "active"}).sort("grade", -1).limit(50).hint("bad_order")
print(q.explain()["executionStats"]["totalKeysExamined"])
```
With the wrong order, MongoDB walks through many index entries that do not match, so `totalKeysExamined` is much larger than with `sem_status_grade`.

## Task 7

```python
log.create_index([("course", 1), ("credits", 1)], name="course_credits")
q = log.find({"course": "Physics", "credits": 4}, {"_id": 0, "course": 1, "credits": 1})
print(q.explain()["executionStats"]["totalDocsExamined"])
```
The answer is 0: every field the query uses and returns is in the index, and `_id` is hidden.

## Task 8

```python
for s in log.aggregate([{"$indexStats": {}}]):
    print(s["name"], s["accesses"]["ops"])
```

## Task 9

```python
log.drop_index("bad_order")
print(list(log.index_information().keys()))
```
Unused indexes cost disk space and slow down every insert, so drop the ones you do not need.
