# Lab 7 — Enforcing Access Control and Detecting Tampering: Knowledge Check

Complete these exercises after finishing the lab. The answer key is at the bottom — try each one before looking.

---

## Exercises

### 1. Why a BEFORE trigger, not an AFTER trigger? (concept)

Lab 7's Step 6 creates a `BEFORE UPDATE OR DELETE` trigger that raises an exception. What would happen if you changed it to an `AFTER UPDATE OR DELETE` trigger instead? Would the row still be modified?

### 2. What is GENESIS and why does the chain need it? (concept)

The hash chain uses `GENESIS` as the `prev_hash` for the first event in a run. What would happen to verification if the first event's `prev_hash` were `NULL` instead? How does `GENESIS` make the chain verification logic simpler?

### 3. Why does the hash chain use md5, not sha256? (concept)

Lab 7 uses `md5()` for the hash chain. Postgres has `sha256()` available via `pgcrypto`. In what scenario would `sha256()` be preferable? In what scenario is `md5()` sufficient?

### 4. What does SECURITY DEFINER actually change? (concept)

Step 8 drops the trigger, tampers with data, and re-creates the trigger. Could you instead create a `SECURITY DEFINER` function that UPDATEs `event` without dropping the trigger? Would the BEFORE trigger still fire? Why or why not?

### 5. Write a query that verifies the hash chain for a single event (short code)

Write a Python function that, given a connection and an `event_id`, recomputes the expected hash from the live `event` data and compares it to the stored hash in `event_hash_chain`. Print whether the hash matches or is broken.

```python
def verify_single_event(conn, event_id):
    cur = conn.cursor()
    # Your query here
    cur.close()
```

### 6. Write an INSERT that the append-only trigger allows (short code)

Write a Python `cursor.execute` that inserts a new row into the `event` table for an existing `run_id`. The trigger should NOT reject this INSERT — it only blocks UPDATE and DELETE.

```python
cursor.execute("""
    -- your INSERT here
""")
connection.commit()
```

### 7. Applied: a trigger that blocks INSERT too (applied)

A colleague wants to make the `event` table completely immutable — no INSERT, no UPDATE, no DELETE. They modify the trigger to fire on `INSERT OR UPDATE OR DELETE`. What would break? The notebook's Step 3 inserts events, and the auto-hash trigger (created in Step 6) also inserts into `event_hash_chain`. Which of these would fail, and why?

---

## Answer Key

### 1. Why a BEFORE trigger, not an AFTER trigger?

A `BEFORE` trigger fires before the row modification is applied. If the trigger raises an exception, the modification never happens — the row is not updated or deleted. An `AFTER` trigger fires *after* the modification is already committed to the row. If the AFTER trigger raises an exception, the row has already been modified; the exception rolls back the transaction, but the modification happened within the transaction. The key difference: `BEFORE` prevents the modification from ever reaching the row; `AFTER` allows it but rolls it back. For an append-only invariant, `BEFORE` is the correct choice because it guarantees the row is never touched.

### 2. What is GENESIS and why does the chain need it?

If the first event's `prev_hash` were `NULL`, the hash computation would include the literal string `None` (Python's string representation of `None`) — or `NULL` in SQL — which is ambiguous and could collide with a row that genuinely has `NULL` as its `prev_hash`. `GENESIS` is an explicit sentinel that cannot appear as a real hash value (it's not a valid md5 output), so the chain's start is unambiguous. It also simplifies verification: you never need a special case for "is this the first event?" — you just use `prev_hash or 'GENESIS'` uniformly.

### 3. Why does the hash chain use md5, not sha256?

`md5()` is faster and produces a shorter hash (32 hex characters vs. 64 for sha256). For a hash chain whose purpose is tamper *detection* (not cryptographic security), md5 is sufficient — any modification to the input changes the output. `sha256()` would be preferable if the chain needed to resist deliberate collision attacks (e.g., an attacker crafting a payload that produces the same hash as the original). For an audit log where the threat is accidental or opportunistic tampering, not a determined adversary, md5 is adequate and simpler to display.

### 4. What does SECURITY DEFINER actually change?

A `SECURITY DEFINER` function runs with the privileges of the function *owner* (typically `postgres`), not the calling user. However, `BEFORE` triggers still fire on every row modification, regardless of who calls it. So a SECURITY DEFINER function that UPDATEs `event` would still trigger `fn_prevent_event_tamper()`, and the trigger would still `RAISE EXCEPTION`. The SECURITY DEFINER doesn't bypass the trigger — it only changes which user's permissions are checked for the underlying operation. To actually bypass the trigger, you'd need to drop it first (as Step 8 demonstrates).

### 5. Write a query that verifies the hash chain for a single event

```python
def verify_single_event(conn, event_id):
    cur = conn.cursor()
    cur.execute("""
        SELECT ec.row_hash AS stored_hash, ec.prev_hash,
               e.run_id, e.event_type, e.payload
        FROM event_hash_chain ec
        JOIN event e ON e.event_id = ec.event_id
        WHERE ec.event_id = %s
    """, (event_id,))
    row = cur.fetchone()
    if row is None:
        print(f"event {event_id}: not found in chain")
        cur.close()
        return
    stored, prev, rid, etype, payload = row
    content = f"{event_id}|{rid}|{etype}|{payload}|{prev or 'GENESIS'}"
    recomputed = md5_fn(content.encode()).hexdigest()
    if stored == recomputed:
        print(f"event {event_id}: hash matches ({stored[:20]}...)")
    else:
        print(f"event {event_id}: BROKEN stored={stored[:20]}... recomputed={recomputed[:20]}...")
    cur.close()
```

### 6. Write an INSERT that the append-only trigger allows

```python
cursor.execute("""
    INSERT INTO event (run_id, event_type, payload)
    VALUES (%s, %s, %s)
""", (lab4_run_id, "new_event", "This INSERT is allowed by the trigger."))
connection.commit()
```

### 7. Applied: a trigger that blocks INSERT too

If the trigger fires on `INSERT OR UPDATE OR DELETE`, the `INSERT INTO event` in Step 3 would be rejected — the trigger would `RAISE EXCEPTION` on every INSERT, so no events could ever be added. The auto-hash trigger (created in Step 6) inserts into `event_hash_chain` (not `event`), so it would not be directly blocked — but since no events could be inserted into `event` in the first place, there would be nothing to hash. The entire pipeline would fail at Step 3. The lesson: an append-only trigger must allow INSERT and only block UPDATE and DELETE.
