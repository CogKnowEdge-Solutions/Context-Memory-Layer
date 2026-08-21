# MongoDB Advanced: How to Guarantee Data Consistency

## Enrollment Transactions — Assignment

Test your understanding of multi-document transactions, change streams, and data consistency by answering the following questions and completing the short code tasks.

---

## Exercises

### Exercise 1 — Concept Question
What problem do multi-document transactions solve that individual MongoDB writes cannot? Describe a concrete scenario from the enrollment workflow where two separate writes could leave the data inconsistent.

### Exercise 2 — Concept Question
What is the difference between `client.start_session()` and `session.with_transaction()`? What happens if you call `find_one_and_update` inside a session but *outside* a transaction?

### Exercise 3 — Code Task
Write a pymongo snippet using `with_transaction` that atomically decrements a seat in the `courses` collection and inserts an enrollment document into the `enrollments` collection for student `STU050` named `"Eve Torres"` in course `CS201`. Assume `client`, `courses`, and `enrollments` are already connected.

### Exercise 4 — Concept Question
Why does the `find_one_and_update` call inside `enroll_student` use the filter `{"seats_available": {"$gt": 0}}` instead of just `{"course_id": cid}`? What race condition does this prevent?

### Exercise 5 — Concept Question
When a transaction is aborted because a course is full, what happens to the writes that were attempted inside the transaction? Does `seats_available` go negative? Does an enrollment document get created?

### Exercise 6 — Code Task
Write pymongo code that opens a change stream on the `enrollments` collection, inserts a new enrollment document, reads the next change event, and prints the `operationType` and the enrolled student's name from `fullDocument`.

### Exercise 7 — Concept Question
What is a change stream in MongoDB? Name one real-world use case beyond the enrollment example shown in this lab.

### Exercise 8 — Code Task
Write a pymongo function `backup_collection(collection, filepath)` that exports all documents in a given collection to a JSON file, encoding `ObjectId` fields as strings. Then write `restore_collection(collection, filepath)` that reads the JSON file and inserts the documents back into the collection (after dropping it first).

---

## Answer Key

### Exercise 1
Multi-document transactions guarantee that related writes across multiple collections either **all succeed or all fail together**, with no partial state in between. In the enrollment workflow, decrementing a course's `seats_available` and inserting an enrollment document are two separate operations on two separate collections. If the seat decrement succeeds but the enrollment insert fails (or vice versa), the database is left inconsistent — a seat is taken with no enrollment record, or a student is enrolled for a seat that was never reserved. Individual MongoDB writes are atomic, but MongoDB cannot guarantee two separate writes will both succeed or both fail without a transaction.

### Exercise 2
`client.start_session()` creates a **session** — a logical context that groups operations together. `session.with_transaction(callback)` runs a **callback function** inside a transaction within that session: if the callback returns normally, the transaction commits; if it raises an exception, the transaction aborts and all writes are rolled back. If you call `find_one_and_update` inside a session but *outside* a `with_transaction` block, the operation executes immediately without transactional guarantees — it is not rolled back if a later operation fails.

### Exercise 3
```python
def enroll_stu050(session):
    result = courses.find_one_and_update(
        {"course_id": "CS201", "seats_available": {"$gt": 0}},
        {"$inc": {"seats_available": -1}},
        session=session
    )
    if result is None:
        raise Exception("No seats available in CS201")
    enrollments.insert_one({
        "enrollment_id": "ENR050",
        "student_id": "STU050",
        "student_name": "Eve Torres",
        "course_id": "CS201",
        "enrolled_at": datetime.utcnow()
    }, session=session)

with client.start_session() as session:
    session.with_transaction(enroll_stu050)
```
The seat decrement and enrollment insert both run inside the same transaction. If `find_one_and_update` returns `None` (no seats left), the exception causes the transaction to abort — no seat is decremented and no enrollment is created.

### Exercise 4
The filter `{"seats_available": {"$gt": 0}}` ensures that the `find_one_and_update` call only succeeds when at least one seat is actually available. If you used just `{"course_id": cid}`, the update would always succeed (decrementing seats even below zero) regardless of availability. The `$gt: 0` filter combined with `$inc: -1` in a single atomic operation eliminates the race condition: two concurrent transactions cannot both see `seats_available = 1` and both decrement it, because MongoDB applies the filter and the update atomically — only one transaction's `find_one_and_update` will match the document.

### Exercise 5
When a transaction is aborted, **all writes inside it are rolled back** — as if they never happened. `seats_available` does **not** go negative (the `find_one_and_update` returned `None` because no document matched the filter, so the `$inc` was never applied). No enrollment document is created for the rejected student either. The database is left in the same consistent state it was in before the transaction started.

### Exercise 6
```python
change_stream = enrollments.watch()

enrollments.insert_one({
    "enrollment_id": "ENR999",
    "student_id": "STU999",
    "student_name": "Test Student",
    "course_id": "CS101",
    "enrolled_at": datetime.utcnow()
})

event = change_stream.next()
print(f"operationType: {event['operationType']}")
print(f"student name: {event['fullDocument']['student_name']}")

change_stream.close()
```
`watch()` opens the change stream. The `insert_one` generates a change event. `next()` blocks until that event arrives, and `fullDocument` contains the full enrollment document that was just inserted.

### Exercise 7
A **change stream** is a real-time feed of write operations (inserts, updates, deletes, replaces) on a collection, database, or entire cluster. One real-world use case: **audit logging** — recording every write to a sensitive collection (e.g., financial transactions or access logs) for compliance purposes, without polling the database. Another use case: **real-time notifications** — pushing an alert to a dashboard whenever a new document is inserted.

### Exercise 8
```python
import json
from bson import ObjectId

def backup_collection(collection, filepath):
    docs = []
    for doc in collection.find():
        doc["_id"] = str(doc["_id"])
        docs.append(doc)
    with open(filepath, "w") as f:
        json.dump(docs, f, indent=2)
    print(f"Backed up {len(docs)} documents to {filepath}")

def restore_collection(collection, filepath):
    with open(filepath, "r") as f:
        docs = json.load(f)
    for doc in docs:
        doc["_id"] = ObjectId(doc["_id"])
    collection.drop()
    if docs:
        collection.insert_many(docs)
    print(f"Restored {len(docs)} documents to {collection.name}")
```
The `backup_collection` function iterates over all documents, converts `_id` from `ObjectId` to `str` (so `json.dump` can serialize it), and writes them to a JSON file. The `restore_collection` function reads the JSON, converts `_id` back to `ObjectId`, drops the collection, and reinserts the documents.
