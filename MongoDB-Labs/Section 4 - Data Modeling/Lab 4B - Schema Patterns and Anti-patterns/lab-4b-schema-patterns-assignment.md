# MongoDB Intermediate: How to Recognize Schema Patterns and Anti-patterns

## Schema Patterns and Anti-patterns — Assignment

Test your understanding of document size limits and the five patterns from the lab.

---

## Exercises

### Exercise 1 — Concept Question
What is the maximum size of a single MongoDB document? Describe two problems a very large document causes *before* it reaches that limit.

### Exercise 2 — Concept Question
A blog post document stores every comment in a `comments` array. Name the anti-pattern, say why it is dangerous, and describe the fix.

### Exercise 3 — Code Task
A `pat_students` document has a `recent_grades` array. Write one `update_one` call that adds a new grade object `new_entry` and keeps only the **last 3** grades in the array.

### Exercise 4 — Code Task
Write the update that records a new quiz score of 85 for student `STU00002` while maintaining the counters `quiz_count` and `quiz_sum` in the same operation. Then write one line that computes the average from the stored values.

### Exercise 5 — Concept Question
A weather app stores one document per sensor reading, every minute, for 10,000 sensors. Which pattern would you apply, what window would you choose for the bucket, and why must the bucket be bounded?

### Exercise 6 — Code Task
Write an upsert that adds a sensor reading `{"t": "10:01", "temp": 21.4}` to the bucket document for sensor `S7` on date `"2026-09-01"`, maintaining `reading_count` and `temp_sum`.

### Exercise 7 — Applied Task
An orders page shows each order's customer name and city next to the order. Customer name and city are stored only in a `customers` collection, and the page does a `$lookup` per load. Describe how the extended reference pattern would change the schema, which fields you would copy, and which you would not. Then explain how you would handle a customer moving to a new city.

### Exercise 8 — Concept Question
Pick any two patterns from this lab and describe a situation where applying each would be the **wrong** choice.

---

## Answer Key

### Exercise 1
16 megabytes. Problems before the limit: (1) every read of the document transfers the whole thing from disk to memory to the network, even if only one field is needed, which wastes cache, bandwidth and time; (2) any update to the document may rewrite a large amount of data and increases contention, and a large working set of big documents pushes useful data out of memory.

### Exercise 2
This is the **unbounded array** anti-pattern. Comments are unlimited, so the post document grows with every comment, slowing reads and updates and eventually hitting the 16 MB limit. The fix is **referencing**: store each comment as its own document in a `comments` collection with a `post_id` field (indexed), and query the comments you need (for example the newest 20) separately.

### Exercise 3
```python
students.update_one(
    {"_id": "STU00001"},
    {"$push": {"recent_grades": {"$each": [new_entry], "$slice": -3}}}
)
```
`$each` wraps the item(s) to add, and `$slice: -3` keeps only the last three elements after the push, so the array never exceeds three entries.

### Exercise 4
```python
students.update_one(
    {"_id": "STU00002"},
    {"$inc": {"quiz_count": 1, "quiz_sum": 85}}
)
# average from the stored values:
doc = students.find_one({"_id": "STU00002"})
average = doc["quiz_sum"] / doc["quiz_count"]
```
Doing both `$inc` operations in the same update keeps the two counters consistent, because a single-document update is atomic.

### Exercise 5
The **bucket pattern**. One document per sensor per hour (60 readings) or per day (1,440 readings) cuts the document count by 60x or 1,440x and makes "last hour of readings" a single read. The bucket must be bounded (a fixed time window) so that the array inside it cannot grow without limit. An unbounded bucket would simply recreate the unbounded-array anti-pattern.

### Exercise 6
```python
sensor_buckets.update_one(
    {"sensor_id": "S7", "date": "2026-09-01"},
    {
        "$push": {"readings": {"t": "10:01", "temp": 21.4}},
        "$inc":  {"reading_count": 1, "temp_sum": 21.4},
    },
    upsert=True,
)
```
`upsert=True` creates the bucket on the first reading of the day and updates it afterwards. A unique index on `(sensor_id, date)` is recommended so two buckets can never exist for the same window.

### Exercise 7
Store the customer reference (`customer_id`) plus a small copied sub-document in each order, for example `customer: {name, city}`. Copy fields that are display-only and change rarely (name, city). Do **not** copy fields that change often or are large (full address history, preferences, order totals, loyalty points). When a customer moves, update `customers` first (source of truth), then propagate with `orders.update_many({"customer_id": cid}, {"$set": {"customer.city": new_city}})`, possibly as a background job. Decide separately whether past orders should keep the *old* city, since for shipping records the historical value may be the correct one and should not be updated.

### Exercise 8
Examples (any two sensible answers are acceptable). **Subset:** wrong when most reads need the full list (a transcript viewer) because the extra query for the tail is paid on nearly every request. **Computed:** wrong when the underlying data changes far more often than it is read, so the write overhead outweighs the saved read work. **Bucket:** wrong when you often need to read or update individual items independently, or when events are sparse so buckets stay nearly empty. **Extended reference:** wrong when the copied field changes frequently or must always be exactly current (a stock balance). **Referencing for an array:** wrong when the list is small and always read with its parent (an order's three shipping labels), where embedding is simpler and faster.
