# Update Data and Enforce Constraints — Assignment

## Exercises

### Exercise 1 — Change one row
Write a single statement that raises the grade of `STU005` to 90 and hands the changed row back, so you can confirm exactly what moved.

### Exercise 2 — The missing WHERE
Explain why running `UPDATE students SET grade = 0` with no `WHERE` clause is dangerous, and describe how this lesson lets you undo a change like that.

### Exercise 3 — Deleting rows
Explain the difference between `DELETE FROM students WHERE status = 'withdrawn'` and `TRUNCATE students`, and give one situation where each is the right choice.

### Exercise 4 — Adding a column and a rule
Write the commands to add a new column `phone` of type `TEXT` to the `students` table, and then a rule that `phone` can never be missing. What must be true of the existing rows before the second command succeeds?

### Exercise 5 — Unique and missing
The `email` column carries a `UNIQUE` rule, yet several rows could hold no email at all. Explain why that is allowed.

### Exercise 6 — A status rule
Write the command to add a `CHECK` rule named `students_status_check` that allows only the values `'active'`, `'inactive'`, and `'withdrawn'` in the `status` column.

### Exercise 7 — Three kinds of key
Describe the difference between the `student_id` primary key, a `GENERATED ALWAYS AS IDENTITY` key, and a `uuidv7()` key. Give one situation where each fits best.

### Exercise 8 — Keeping a feed in sync
Explain what `INSERT ... ON CONFLICT (student_id) DO UPDATE` does. Then explain how `MERGE` is different when you have many rows to reconcile at once.

## Answer Key

### Exercise 1
**Answer:**
```python
show("""
    UPDATE students
    SET grade = 90
    WHERE student_id = 'STU005'
    RETURNING student_id, name, grade
""")
conn.commit()
```
**Why:** The `WHERE` clause limits the change to the single matching row, and `RETURNING` prints that row so you can see the new value instead of guessing. `conn.commit()` makes the change permanent.

### Exercise 2
**Answer:** With no `WHERE`, the statement changes **every** row — all students would get a grade of 0. The lesson runs changes with autocommit off, so the change is not final until you commit; calling `conn.rollback()` throws the whole transaction away and restores the rows.

**Why:** `WHERE` decides which rows a change touches. Forgetting it is the most common way to damage a real database, and a transaction is the safety net that lets you undo the mistake before it is saved.

### Exercise 3
**Answer:** `DELETE FROM students WHERE status = 'withdrawn'` removes only the rows you name, writing a record of each removal, so it can be rolled back row by row — it is the right choice when you want to remove specific rows. `TRUNCATE students` empties the whole table in one operation and is far faster, but it cannot be aimed at some rows — it is the right choice when you genuinely want a table cleared, such as reloading a staging table.

**Why:** `DELETE` trades speed for precision; `TRUNCATE` trades precision for speed. Choosing between them is really asking, "do I want to remove some rows, or all of them?".

### Exercise 4
**Answer:**
```python
conn.execute("ALTER TABLE students ADD COLUMN phone TEXT")
conn.commit()

conn.execute("UPDATE students SET phone = 'not provided' WHERE phone IS NULL")
conn.commit()

conn.execute("ALTER TABLE students ALTER COLUMN phone SET NOT NULL")
conn.commit()
```
Before the last command can succeed, **no existing row may have a `NULL` phone**. Adding the column makes every existing row `NULL` in it, so we fill those values first; otherwise PostgreSQL refuses the rule and reports that the column contains null values.

**Why:** This is the same pattern as the `NOT NULL` rule in the lesson: clean the rows you already have, then lock in the rule so the problem cannot come back.

### Exercise 5
**Answer:** A `NULL` means "unknown", and two unknowns are never treated as equal, so the uniqueness test does not see two `NULL` emails as duplicates. That is why any number of rows can leave `email` empty while still satisfying the `UNIQUE` rule.

**Why:** Uniqueness is about stopping two *known* values from colliding — for example, the same person enrolled twice — not about forcing every row to have a value at all.

### Exercise 6
**Answer:**
```python
conn.execute(
    "ALTER TABLE students ADD CONSTRAINT students_status_check "
    "CHECK (status IN ('active', 'inactive', 'withdrawn'))"
)
conn.commit()
```
**Why:** `CHECK` enforces a condition on every row, and `IN (...)` lists the allowed values in one tidy test. If any existing row already held some other value, adding the rule would be refused until that row is fixed.

### Exercise 7
**Answer:** The `student_id` primary key is a value a human chooses (a business key like `STU001`); it fits when the data already has a natural identifier. A `GENERATED ALWAYS AS IDENTITY` key is a number the server counts out for you, unique within one database; it fits rows that have no natural key of their own, like a transcript line. A `uuidv7()` Universally Unique Identifier (UUID) key is a long, globally unique value that still sorts by creation time; it fits rows created in many places at once, or when you would rather not expose a running number.

**Why:** All three identify a row, but they suit different sources of truth: a chosen value, a server-generated counter, or a globally unique identifier.

### Exercise 8
**Answer:** `INSERT ... ON CONFLICT (student_id) DO UPDATE` handles **one** row: it inserts the row, or, if the key already exists, updates it using the values we tried to insert (referred to as `EXCLUDED`). `MERGE` does the same job for a whole **batch**: it compares a source list against the target table and, row by row, updates the ones that match and inserts the ones that do not — all in a single statement.

**Why:** An upsert is the right tool for a single record, while `MERGE` is the right tool for syncing a whole list, such as a nightly data feed, without writing one statement per row.
