# MongoDB Intermediate: How to Design Schemas & Search Data

## Courses & Instructors — Assignment

Test your understanding of schema design, `$lookup`, and text search by answering the following questions and completing the short code tasks.

---

## Exercises

### Exercise 1 — Concept Question
What is the difference between **embedding** and **referencing** in MongoDB schema design? Give one example of each from the `courses` collection.

### Exercise 2 — Concept Question
When should you choose embedding over referencing? Describe two factors that favor embedding, based on what README Section 3.2 explains.

### Exercise 3 — Code Task
Write an aggregation pipeline using `$lookup` that joins the `courses` collection to the `instructors` collection and returns only the course title and the instructor's name. Use `$project` to exclude the `_id` field.

### Exercise 4 — Concept Question
What does `$unwind` do after a `$lookup`? What happens if you skip `$unwind` and try to access `instructor_info.name` directly?

### Exercise 5 — Code Task
Write a query that finds all courses taught by "Dr. Maria Chen" using the `$lookup` pipeline (not a hardcoded instructor_id). The output should show the course_id and title.

### Exercise 6 — Concept Question
What is a text index in MongoDB? How does a `$text` search query differ from a regular `find()` with an exact string match?

### Exercise 7 — Code Task
Write the pymongo command to create a text index on the `description` field of the `courses` collection, then search for courses containing the word "data". Print the course_id and title of each matching course.

### Exercise 8 — Applied Task
You need to add a new course "CS301: Machine Learning" taught by Dr. Sarah Thorne. Write the full pymongo code: insert the course document (with an embedded schedule and the correct instructor_id reference), then use a `$lookup` pipeline to verify the course appears with Dr. Thorne's name in the output.

---

## Answer Key

### Exercise 1
**Embedding** means nesting related data directly inside the document. In the `courses` collection, the `schedule` subdocument (with `meeting_times` and `location`) is embedded — it lives inside each course document. **Referencing** means storing an ID that points to a document in another collection. In the `courses` collection, `instructor_id` is a reference — it links to the `instructors` collection, where the instructor's full record (name, department, bio) lives.

### Exercise 2
Embedding is favored when data is **always read together** with the main document (the schedule is always displayed alongside the course) and when the embedded data is **bounded** (a course has exactly one schedule, not a growing list). Referencing is favored when the data is **shared across many documents** (one instructor teaches multiple courses) or **updated independently** (changing an instructor's bio should update one document, not every course they teach).

### Exercise 3
```python
pipeline = [
    {"$lookup": {
        "from": "instructors",
        "localField": "instructor_id",
        "foreignField": "instructor_id",
        "as": "instructor_info"
    }},
    {"$unwind": "$instructor_info"},
    {"$project": {
        "_id": 0,
        "title": 1,
        "instructor_name": "$instructor_info.name"
    }}
]
results = courses.aggregate(pipeline)
for doc in results:
    print(f"{doc['title']} -> {doc['instructor_name']}")
```
`$lookup` joins the two collections. `$unwind` flattens the array. `$project` selects only the fields we want and excludes `_id`.

### Exercise 4
`$unwind` deconstructs the array created by `$lookup`, producing one output document per array element. If you skip `$unwind`, `instructor_info` remains an **array** (even with one element), so `instructor_info.name` would return `None` or raise an error — you would need `instructor_info.0.name` or a `$project` with array indexing. `$unwind` converts the array into a plain subdocument, so `.name` works directly.

### Exercise 5
```python
pipeline = [
    {"$lookup": {
        "from": "instructors",
        "localField": "instructor_id",
        "foreignField": "instructor_id",
        "as": "instructor_info"
    }},
    {"$unwind": "$instructor_info"},
    {"$match": {"instructor_info.name": "Dr. Maria Chen"}},
    {"$project": {"_id": 0, "course_id": 1, "title": 1}}
]
results = courses.aggregate(pipeline)
for doc in results:
    print(f"{doc['course_id']}: {doc['title']}")
```
The `$match` stage filters after `$lookup` and `$unwind`, so you can match on the joined instructor's name rather than the raw `instructor_id`.

### Exercise 6
A **text index** is a special index type that enables full-text search on string fields. Unlike a regular `find({"field": "exact value"})` which requires an exact match, a `$text` search query like `{"$text": {"$search": "word"}}` matches any document where the indexed field *contains* the search word as a substring or token. Text search also supports multi-word queries and phrase matching with double quotes.

### Exercise 7
```python
courses.create_index([("description", "text")])

results = courses.find(
    {"$text": {"$search": "data"}},
    {"_id": 0, "course_id": 1, "title": 1}
)
for doc in results:
    print(f"{doc['course_id']}: {doc['title']}")
```
This matches "Data Structures and Algorithms" (CS201, description contains "data structures") and "Linear Algebra" (MATH201, description contains "data science"). The text index tokenizes the description field and matches any document containing the word "data" as a separate token.

### Exercise 8
```python
courses.insert_one({
    "course_id": "CS301",
    "title": "Machine Learning",
    "description": "Supervised learning, neural networks, and model evaluation",
    "instructor_id": "INS001",
    "seats": 60,
    "schedule": {"meeting_times": "TTh 2:00-3:15", "location": "Science Building Room 310"}
})

pipeline = [
    {"$lookup": {
        "from": "instructors",
        "localField": "instructor_id",
        "foreignField": "instructor_id",
        "as": "instructor_info"
    }},
    {"$unwind": "$instructor_info"},
    {"$match": {"course_id": "CS301"}},
    {"$project": {
        "_id": 0,
        "course_id": 1,
        "title": 1,
        "instructor_name": "$instructor_info.name"
    }}
]
result = list(courses.aggregate(pipeline))
for doc in result:
    print(f"{doc['course_id']}: {doc['title']} -> {doc['instructor_name']}")
```
The course stores `instructor_id: "INS001"` (Dr. Thorne's ID from the instructors collection). The `$lookup` pipeline joins this to the instructors collection and resolves the ID to the instructor's name.
