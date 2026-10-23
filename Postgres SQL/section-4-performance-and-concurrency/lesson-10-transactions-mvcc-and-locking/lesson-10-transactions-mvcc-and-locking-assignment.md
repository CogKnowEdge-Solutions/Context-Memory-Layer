# Transactions, MVCC and Locking — Assignment

The code exercises build their own small tables, so run them in a scratch file with a Python connection called `conn` (opened with `psycopg.connect(...)`) or in any Structured Query Language (SQL) window. Use PostgreSQL 18 (14 or newer works for everything here).

## Exercises

### Exercise 1 — Name the promise that broke
A booking app lets two customers book the same seat, exactly as in Step 4. Which of the four promises in Atomicity, Consistency, Isolation and Durability (ACID) did the application break, and why is it *not* the database's atomicity that failed?

### Exercise 2 — Why the reader never waits
In Step 5, Alice updates seat 3 without committing, and Bob's plain `SELECT` on the same row returns `NULL` immediately. Explain in your own words where that `NULL` comes from and why Bob's read did not have to wait. What is the one kind of statement that *would* have waited?

### Exercise 3 — Undo only the failed part
Write the statements that: start a transaction, book seat 1 for `ana`, book seat 2 for `ana`, undo **only** the seat 2 booking, and keep the seat 1 booking. Name the two savepoint statements you used and say what each one does.

### Exercise 4 — Fix a check-then-write
This code double-books seat 7 whenever two requests arrive together:

```python
with conn.cursor() as cur:
    cur.execute("SELECT booked_by FROM seats WHERE seat_no = 7")
    if cur.fetchone()[0] is None:
        cur.execute("UPDATE seats SET booked_by = %s WHERE seat_no = 7", ("ana",))
        conn.commit()
        send_confirmation("ana", 7)
```

Rewrite the write so it only succeeds when the seat is still free, and show how the application knows whether it won. Why does this version need no `FOR UPDATE`?

### Exercise 5 — A queue, not a queue of waiters
A `jobs` table has `job_id`, `status` and `claimed_by`. Five worker processes run this claim statement at the same time:

```sql
UPDATE jobs SET status = 'running', claimed_by = %s
WHERE job_id = (
    SELECT job_id FROM jobs WHERE status = 'new'
    ORDER BY job_id
    FOR UPDATE SKIP LOCKED
    LIMIT 1
)
RETURNING job_id;
```

What does each worker get, and what would change if you removed `SKIP LOCKED`? What happens to a worker when no `new` job is left?

### Exercise 6 — The report that changes under you
A report runs inside one transaction and reads the same `count(*)` twice, a few seconds apart. Between the two reads another session commits a new order, and the two totals disagree. Which isolation level is the report running at, which level would give it one stable answer, and what new error can that level raise? What must the application do when it sees that error?

### Exercise 7 — Lock a name, not a row
Your nightly cache-rebuild job must never run twice at the same time, but it does not touch any single row you could lock. Which tool from the lesson fits, which function gives a non-blocking yes/no answer, and what does the job do when the answer is no?

### Exercise 8 — Break the cycle
Two sessions deadlock: session A locks `orders` row 10 then row 11, and session B locks row 11 then row 10. Name two changes that make this deadlock much less likely, and state what the application should do when PostgreSQL reports a deadlock anyway.

## Answer Key

### Exercise 1
**Answer:** **Isolation** broke. Each transaction was internally atomic and the database stayed consistent and durable — but the two transactions were not kept apart, so one customer's committed booking was silently overwritten by the other's. The database ran two perfectly valid `UPDATE` statements; nothing in them said "only if still free".

**Why:** atomicity means "all of *my* statements or none of them", which was true for both customers. It says nothing about *two* transactions competing for the same row — that is isolation's job, and the fix belongs in how the application writes (a lock or a condition that names the rule).

### Exercise 2
**Answer:** The `NULL` is the last **committed** version of the row, kept alive by Multi-Version Concurrency Control (MVCC). Alice's `UPDATE` wrote a *new* version and marked the old one as replaced; her new version is invisible to anyone else until she commits. Bob's plain `SELECT` reads the old version from his own snapshot, so there is nothing to wait for. A `SELECT ... FOR UPDATE` (or any `UPDATE`/`DELETE` of that row) would have waited, because it asks for the row's lock as well as its contents.

**Why:** readers and writers work on different versions of the same row, so they never need the same lock. Only two writers — or a writer and a locking reader — contend.

### Exercise 3
**Answer:**

```python
conn.execute("UPDATE seats SET booked_by = 'ana' WHERE seat_no = 1")
conn.execute("SAVEPOINT after_seat_1")
conn.execute("UPDATE seats SET booked_by = 'ana' WHERE seat_no = 2")
conn.execute("ROLLBACK TO SAVEPOINT after_seat_1")
conn.commit()
```

`SAVEPOINT after_seat_1` marks a point inside the open transaction. `ROLLBACK TO SAVEPOINT after_seat_1` discards everything done after that mark and keeps everything before it, so seat 1 stays booked and seat 2 does not.

**Why:** without a savepoint the only choices are "keep everything" (`COMMIT`) or "lose everything" (`ROLLBACK`). A savepoint gives you the middle option an application needs when one step of several fails.

### Exercise 4
**Answer:**

```python
cur.execute(
    "UPDATE seats SET booked_by = %s WHERE seat_no = 7 AND booked_by IS NULL",
    ("ana",),
)
won = cur.rowcount == 1
conn.commit()
if won:
    send_confirmation("ana", 7)
else:
    tell_customer("that seat was just taken")
```

The `WHERE booked_by IS NULL` makes the condition part of the write itself, and `rowcount` reports whether the row was still free (`1`) or already taken (`0`). No `FOR UPDATE` is needed because the `UPDATE` already takes the row lock while it runs and re-checks its `WHERE` clause against the newest committed version of the row — so it cannot overwrite someone else's booking.

**Why:** this is optimistic concurrency: assume conflicts are rare, do not hold a lock, and let the write itself prove the condition still holds. It trades a possible retry for never making anyone wait.

### Exercise 5
**Answer:** Each worker gets a **different** job: the subquery locks the first `new` job and `SKIP LOCKED` makes every other worker ignore rows that are already locked, so they move on to the next one instead of queuing. Without `SKIP LOCKED`, workers would block behind each other on the same row and effectively process one job at a time. When no `new` job is left, the subquery returns no row, the `UPDATE` changes nothing, and `RETURNING` gives the worker an empty result — the worker should then wait and poll again rather than treat it as an error.

**Why:** `SKIP LOCKED` turns a table into a work queue. Every worker takes a different row instantly, which is exactly what job runners, outbox tables and background processors need.

### Exercise 6
**Answer:** The report is running at **`READ COMMITTED`** (the default), where each statement takes a fresh snapshot — so a commit between the two reads changes the second answer. **`REPEATABLE READ`** gives the whole transaction one snapshot, so both reads agree. The new risk is SQLSTATE `40001` (*could not serialize access due to concurrent update*) when the transaction later writes a row that changed after its snapshot. The application must **roll back and rerun the whole transaction** on that error — usually with a small delay and a retry limit — rather than forcing a stale write through.

**Why:** a stable snapshot and concurrent writes cannot both be free. PostgreSQL chooses consistency and hands you an error you can retry; the retry loop is part of using the level, not an optional extra.

### Exercise 7
**Answer:** An **advisory lock** fits: it locks a number you choose rather than a row. `pg_try_advisory_lock(<key>)` gives a non-blocking `true`/`false` answer. When it returns `false`, another copy already holds the lock, so the job logs that it is skipping this run and exits (or retries later); when the running copy finishes, it releases the lock with `pg_advisory_unlock(<key>)` so the next run can take it.

**Why:** there is no row to lock, and waiting would pile up duplicate jobs. A non-blocking advisory lock makes "only one at a time" a single decision the job can act on immediately.

### Exercise 8
**Answer:** Two changes: (1) **lock in a consistent order** — every transaction that needs rows 10 and 11 locks them lowest first (10 then 11), so a cycle cannot form; (2) **keep the transaction short**, so it holds the first lock for as little time as possible. When PostgreSQL reports a deadlock (SQLSTATE `40P01`), roll back the transaction and retry it — the server has already aborted one participant to break the cycle.

**Why:** a deadlock is a cycle of waits. Consistent ordering removes the cycle by construction, and a retry handles the cycles you cannot design away — after the server aborts one transaction, a retry usually succeeds on the first attempt.
