# Assignment - How to Recognize Schema Patterns

Practise what you learned in **How to Recognize Schema Patterns**. The lesson built each design the wrong way first, measured the damage and then fixed it with named patterns. In these tasks you measure document sizes, use two of the patterns and spot an anti-pattern.

**How to work:** Use the connection and the collections from the lesson: `pat_students_fat` (the bad design), `pat_students` (the slim design) and `pat_grade_history` (one document per grade). Answers are in a separate file; try each task first.

---

**1.** Measure the size in bytes of one document from `pat_students_fat` and one from `pat_students`. Print both sizes. *Hint:* `len(bson.encode(doc))` after `import bson`.

**2.** State in a comment the maximum size of one MongoDB document.

**3.** Count the grade entries stored in `pat_grade_history` for student `"STU00001"` and print the number. Then print how many grades are kept in that student's `recent_grades` array in `pat_students`.

**4.** Print the five newest grades of student `"STU00001"` from `pat_grade_history`, newest first. *Hint:* sort by `seq` descending and limit to 5.

**5.** Add one new grade object to the `recent_grades` array of student `"STU00001"` in `pat_students`, but keep only the last 3 grades. Print the array afterwards. *Hint:* `$push` with `$each` and `$slice`.

**6.** Record a quiz score of 85 for student `"STU00002"` with one `update_one` that also increases the counters `quiz_count` by 1 and `quiz_sum` by 85. Then print the average from the stored values.

**7.** A weather app stores one reading per sensor per minute. Write an upsert that adds the reading `{"t": "10:01", "temp": 21.4}` to one document per sensor per day (sensor `"S7"`, date `"2026-09-01"`) in a new collection `sensor_buckets`. Run it twice with different readings and print the document.

**8.** An orders page needs the customer's name and city. Insert an order into a new collection `orders_demo` that stores `customer_id` and **also** copies `customer_name` and `city` into the order. Print the order.

**9.** The customer from Task 8 moves to a new city. Update every order for that customer with one call, and print how many orders changed.

**10.** A blog post document keeps every comment in a `comments` array that never stops growing. In a comment, name this anti-pattern and say how you would fix it.
