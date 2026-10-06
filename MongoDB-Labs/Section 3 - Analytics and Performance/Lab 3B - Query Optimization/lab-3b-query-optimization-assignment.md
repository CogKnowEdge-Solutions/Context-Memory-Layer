# MongoDB Intermediate: How to Make Queries Fast

## Query Optimization — Assignment

Test your understanding of execution plans, compound index design, covered queries and index cost. Exercises 2, 5 and 7 are code tasks that use the `enrollment_log` collection from the lab (`log`).

---

## Exercises

### Exercise 1 — Concept Question
A query returns 15 documents but `explain` shows `totalDocsExamined: 80000`. What does this tell you, and what is the usual remedy?

### Exercise 2 — Code Task
Write the pymongo call that creates the best single compound index for this query, then write the query itself:

```python
log.find({"semester": "2025-Fall", "status": "active"}).sort("grade", -1).limit(50)
```

### Exercise 3 — Concept Question
State the ESR rule and explain why a range field placed before the sort field in a compound index usually forces an in-memory `SORT` stage.

### Exercise 4 — Concept Question
What makes a query *covered*? Name two things that would stop a query from being covered.

### Exercise 5 — Code Task
Write a covered query that returns only `course` and `credits` for all documents where `course` is `"Physics"` and `credits` is 4. State the compound index you need and the projection you must use.

### Exercise 6 — Concept Question
Your collection has eight indexes and writes have become slow. Describe how you would decide which indexes to remove, naming the aggregation stage you would use and one risk of removing an index too quickly.

### Exercise 7 — Applied Task
The following pipeline is slow. Rewrite it so that an index on `(status, submitted_at)` can feed the first stage, and explain the change.

```python
pipeline = [
    {"$group": {"_id": "$course", "n": {"$sum": 1}}},
    {"$sort": {"n": -1}},
]
# Business need: only count active records submitted in 2025 or later.
```

### Exercise 8 — Concept Question
Why does a query using an anchored regex such as `^STU0042` run efficiently against an index on `student_id`, while `42$` does not?

---

## Answer Key

### Exercise 1
MongoDB read about 5,000 documents for every document it returned, so most of the work was wasted. This usually means there is no index matching the filter (a `COLLSCAN`), or the existing index only partly matches. The remedy is to create or reorder a compound index so the filter fields (and sort fields) are served by the index, then re-run `explain` to confirm `docs examined` drops close to `nReturned`.

### Exercise 2
```python
log.create_index([("semester", 1), ("status", 1), ("grade", -1)])

results = log.find({"semester": "2025-Fall", "status": "active"}).sort("grade", -1).limit(50)
```
Both filter fields are equalities, so they come first; the sort field `grade` comes last. The index delivers entries already ordered by grade, so no `SORT` stage is needed. (Equality order between `semester` and `status` can be swapped without harming this query; choose by which other queries share a prefix.)

### Exercise 3
ESR means **E**quality fields first, then **S**ort fields, then **R**ange fields. Inside the index, entries are ordered by the first field, then the second within equal first values, and so on. If a range field comes before the sort field, the entries that satisfy the range are ordered by the *range* field and the sort field's values are scattered across it, so the index cannot hand results back in sort order. MongoDB must collect all matches and sort them in memory, which is the `SORT` stage.

### Exercise 4
A query is covered when all filtered fields and all returned fields are in a single index and `_id` is excluded, so MongoDB answers from the index with `totalDocsExamined: 0`. Examples that prevent covering: returning a field that is not in the index, forgetting `{"_id": 0}` in the projection, or having an indexed field that is an array (multikey indexes cannot cover queries on the array field).

### Exercise 5
```python
log.create_index([("course", 1), ("credits", 1)])

results = log.find(
    {"course": "Physics", "credits": 4},
    {"_id": 0, "course": 1, "credits": 1}
)
```
Both filter fields and both returned fields are in the index, and `_id` is excluded, so `explain` shows `PROJECTION_COVERED` and zero documents examined.

### Exercise 6
Run `log.aggregate([{"$indexStats": {}}])` and look at `accesses.ops` for each index. Indexes with a count of 0 after a representative period of traffic are candidates to drop. Risks: the counters reset when the server restarts, and a rarely-run job (a monthly report, a quarterly audit) might depend on an index that shows few or no uses in a short window. Dropping it then makes that job suddenly slow. Mitigation: observe over a long enough window and drop one index at a time while watching performance (or hide the index first, on versions that support hidden indexes).

### Exercise 7
```python
pipeline = [
    {"$match": {"status": "active", "submitted_at": {"$gte": datetime(2025, 1, 1)}}},
    {"$group": {"_id": "$course", "n": {"$sum": 1}}},
    {"$sort": {"n": -1}},
]
```
Placing `$match` first lets MongoDB use the `(status, submitted_at)` index to read only the matching slice (`IXSCAN`) rather than scanning every document, and `$group` then processes far fewer documents. A `$group` as the first stage can never use an index for filtering.

### Exercise 8
An index is sorted by the stored string value, so a prefix such as `^STU0042` maps to a contiguous range of the index (all entries from `STU0042` to the next possible prefix). MongoDB can jump to that range and read only those keys. A suffix like `42$` could match anywhere in the sorted order, so MongoDB has to examine every index key (or every document) to test it; the index gives no way to skip. Prefix searches on indexed strings are efficient; suffix and unanchored patterns are not.
