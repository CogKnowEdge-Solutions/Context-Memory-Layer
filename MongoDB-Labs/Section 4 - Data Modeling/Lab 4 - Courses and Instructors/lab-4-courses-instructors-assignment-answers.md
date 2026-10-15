# Assignment Answers - How to Design Schemas & Search Data

Sample answers for the tasks. Your wording and code may differ; what matters is that the result is right.

---

## Task 1

```python
course = db.courses.find_one({}, {"_id": 0})
print(course)
```
`schedule` is embedded: it is stored inside the course. `instructor_id` is a reference: it only holds the id of a document in another collection.

## Task 2

```python
print(db.courses.find_one({"course_id": "CS101"})["schedule"]["location"])
```

## Task 3

```python
course = db.courses.find_one({"course_id": "CS101"})
instructor = db.instructors.find_one({"instructor_id": course["instructor_id"]})
print(instructor["name"])
```

## Task 4

```python
pipeline = [
    {"$lookup": {"from": "instructors", "localField": "instructor_id",
                "foreignField": "instructor_id", "as": "instructor_info"}},
    {"$unwind": "$instructor_info"},
    {"$project": {"_id": 0, "title": 1, "instructor": "$instructor_info.name"}}
]
for row in db.courses.aggregate(pipeline):
    print(row)
```

## Task 5

Without `$unwind`, `instructor_info` is a list with one instructor inside it. With `$unwind`, the list is turned into a single object, so you can use `instructor_info.name` directly.

```python
lookup = {"$lookup": {"from": "instructors", "localField": "instructor_id",
                      "foreignField": "instructor_id", "as": "instructor_info"}}
print(next(db.courses.aggregate([lookup])))
print(next(db.courses.aggregate([lookup, {"$unwind": "$instructor_info"}])))
```

## Task 6

```python
pipeline = [
    {"$lookup": {"from": "instructors", "localField": "instructor_id",
                "foreignField": "instructor_id", "as": "instructor_info"}},
    {"$unwind": "$instructor_info"},
    {"$match": {"instructor_info.name": "Dr. Maria Chen"}},
    {"$project": {"_id": 0, "course_id": 1, "title": 1}}
]
for row in db.courses.aggregate(pipeline):
    print(row)
```

## Task 7

```python
for row in db.courses.aggregate([{"$group": {"_id": "$instructor_id", "courses": {"$sum": 1}}}]):
    print(row)
```

## Task 8

```python
db.courses.create_index([("description", "text")])
for c in db.courses.find({"$text": {"$search": "data"}}, {"_id": 0, "course_id": 1, "title": 1}):
    print(c)
```
A text search finds the word inside the text, not only an exact full value.

## Task 9

```python
db.courses.insert_one({
    "course_id": "CS301", "title": "Machine Learning",
    "description": "Introduction to machine learning with data.",
    "schedule": {"meeting_times": "TTh 10:00-11:15", "location": "Hamilton Hall Room 101"},
    "instructor_id": "INS001"
})
# run the pipeline from Task 4 and check that CS301 appears with the instructor's name
```
Use an `instructor_id` that exists in your `instructors` collection.
