# Lab 2 — Modeling Runs, Spans, and Tool Calls: Knowledge Check

Complete these exercises after finishing the lab. The answer key is at the bottom — try each one before looking.

---

## Exercises

### 1. Why foreign keys matter (concept)

Lab 1's `event` table used a plain `run_id INTEGER` column — no `REFERENCES`, no enforcement. Lab 2's `span` table uses `run_id INTEGER NOT NULL REFERENCES run(run_id)`. What concrete failure can Lab 1's plain integer column allow that Lab 2's foreign key blocks? How does this change the trust model of the schema?

### 2. What does the CHECK constraint protect? (concept)

Lab 2's `guardrail_event.outcome` has `CHECK (outcome IN ('pass', 'fail', 'warn'))`. Step 7 deliberately triggers a `CheckViolation` by inserting `'maybe'`. Why is this constraint in the *database* rather than in application code? What happens if a downstream report assumes `outcome` is always one of three known values, but a raw `INSERT` with a typo gets through?

### 3. Why indexes on foreign key columns? (concept)

Step 3 creates three indexes: `idx_span_run_id`, `idx_tool_call_span_id`, and `idx_guardrail_event_span_id`. Step 9's reconstruction query runs `WHERE run_id = ?` on `span`, then `WHERE span_id = ?` on `tool_call` and `guardrail_event`. Why do these specific queries need indexes, and what would happen to performance as the audit log grows to millions of rows without them?

### 4. Why does the span mirror the run's lifecycle? (concept)

A `span` row has `started_at` (defaulting to `now()` at creation) and `ended_at` (set via `UPDATE` after work completes), mirroring the `run` table's own lifecycle fields. Why is this open → do work → close pattern repeated at the span level? What would you lose if spans only had a creation timestamp and no end time?

### 5. Write a span insert with two tool calls (short code)

Write the `cursor.execute` calls needed to: (a) insert a new span named `fetch_inventory` under the run with id in `current_run_id`, (b) insert two tool calls under that span — one `check_stock` with `success=True` and one `check_stock` with `success=False` — and (c) close the span with an `ended_at` update. Commit after closing.

```python
# Your code here
```

### 6. Write a guardrail_event insert with a warn outcome (short code)

Write a `cursor.execute` call that inserts a guardrail event on the span with id in `answer_span_id`, with `check_name = 'toxicity_scan'`, `outcome = 'warn'`, and a `reason` explaining what triggered the warning. Commit the transaction.

```python
# Your code here
```

### 7. Applied: a foreign key violation to debug (applied)

A colleague writes this code and gets a `ForeignKeyViolation` error:

```python
cursor.execute(
    "INSERT INTO tool_call (span_id, tool_name, success) VALUES (%s, %s, %s)",
    (999999, "query_db", True),
)
```

The error message says: `insert or update on table "tool_call" violates foreign key constraint "tool_call_span_id_fkey"`. What does this error mean? Why did the `span_id = 999999` value cause a rejection? What are the two valid ways to fix this code, depending on whether you want to attach the tool call to an existing span or create a new span first?

---

## Answer Key

### 1. Why foreign keys matter

Lab 1's plain `run_id INTEGER` column would silently accept any integer value, including one that doesn't match any row in the `run` table. A typo like `run_id = 999999` would insert successfully, producing an orphaned event that points at nothing. Lab 2's `REFERENCES run(run_id)` tells Postgres to reject any `INSERT` into `span` (or `tool_call`, or `guardrail_event`) where the parent id doesn't exist. This makes the hierarchy *physical* — enforced on every write — rather than a convention the application code might forget to check. The trust model shifts from "the application guarantees referential integrity" to "the database guarantees it, unconditionally."

### 2. What does the CHECK constraint protect?

The `CHECK` constraint guarantees that `outcome` is always one of `'pass'`, `'fail'`, or `'warn'` — the only three values any downstream report or aggregation query knows how to handle. Without the constraint, a raw `INSERT` with a typo like `'maybe'` or `'passs'` would succeed silently. A report counting `WHERE outcome = 'pass'` would miss that row, and a dashboard grouping by `outcome` would show an unexpected category. Putting the constraint in the database (not just application code) means every writer — every lab, every script, every direct SQL client — is bound by the same rule. Step 7 proved this by deliberately triggering the rejection with `'maybe'`.

### 3. Why indexes on foreign key columns?

Step 9's reconstruction query runs `WHERE run_id = %s` on `span`, then `WHERE span_id = %s` on `tool_call` and `guardrail_event` — one lookup per span, per child table. Without an index, Postgres must scan every row in the child table to find matching rows. With an index, it jumps straight to the matching rows via a tree lookup. As the audit log grows to millions of rows — thousands of runs, each with many spans, each with tool calls and guardrail events — a full table scan becomes catastrophically slow while an indexed lookup stays fast. The indexes are placed on exactly the columns the query pattern actually filters on, not as a generic best practice.

### 4. Why does the span mirror the run's lifecycle?

The open → work → close pattern captures the *duration* of each span — how long the retrieval step took, how long the LLM call took. Without `ended_at`, you only know when a span started, not when it finished. For an auditor reconstructing a run, duration is essential: a 3-second retrieval step is normal, a 3-minute one suggests a timeout or retry. The lifecycle update on `ended_at` is the same append-only discipline Lab 1 used for `run` — one write at creation, one write at completion, nothing in between.

### 5. Write a span insert with two tool calls

```python
cursor.execute(
    "INSERT INTO span (run_id, span_name) VALUES (%s, %s) RETURNING span_id",
    (current_run_id, "fetch_inventory"),
)
inventory_span_id = cursor.fetchone()[0]

cursor.execute(
    "INSERT INTO tool_call (span_id, tool_name, success) VALUES (%s, %s, %s)",
    (inventory_span_id, "check_stock", True),
)
cursor.execute(
    "INSERT INTO tool_call (span_id, tool_name, success) VALUES (%s, %s, %s)",
    (inventory_span_id, "check_stock", False),
)

cursor.execute("UPDATE span SET ended_at = now() WHERE span_id = %s", (inventory_span_id,))
connection.commit()
```

The span follows the same open → work → close lifecycle from Steps 5 and 6. Each `tool_call` insert references the `inventory_span_id` returned by the span's `RETURNING` clause. The `UPDATE` closing the span is the one allowed lifecycle write, matching the pattern the lab established.

### 6. Write a guardrail_event insert with a warn outcome

```python
cursor.execute(
    "INSERT INTO guardrail_event (span_id, check_name, outcome, reason) VALUES (%s, %s, %s, %s)",
    (answer_span_id, "toxicity_scan", "warn",
     "flagged borderline language in generated draft; manual review recommended"),
)
connection.commit()
```

`'warn'` is one of the three legal values in the `CHECK` constraint — the insert succeeds. The `reason` field explains what triggered the warning, completing the audit trail for this guardrail check.

### 7. Applied: a foreign key violation to debug

The error means that `span_id = 999999` does not match any existing row in the `span` table. The foreign key constraint `tool_call.span_id → span.span_id` enforces that every tool call must point at a real span — a non-existent id is rejected.

Two fixes, depending on intent:
- **Attach to an existing span:** Replace `999999` with the id of a span that already exists (e.g., one created in a previous step via `RETURNING span_id`).
- **Create the span first:** Insert the span row before inserting the tool call, then use the returned `span_id`:

```python
cursor.execute(
    "INSERT INTO span (run_id, span_name) VALUES (%s, %s) RETURNING span_id",
    (current_run_id, "new_span"),
)
new_span_id = cursor.fetchone()[0]

cursor.execute(
    "INSERT INTO tool_call (span_id, tool_name, success) VALUES (%s, %s, %s)",
    (new_span_id, "query_db", True),
)
connection.commit()
```

Both approaches ensure the foreign key points at a real parent row before the child is inserted.
