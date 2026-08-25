# Lab 3 — Querying Across the Hierarchy with JOINs: Knowledge Check

Complete these exercises after finishing the lab. The answer key is at the bottom — try each one before looking.

---

## Exercises

### 1. Why LEFT JOIN, not INNER JOIN? (concept)

Lab 3's Step 4 uses `LEFT JOIN` instead of `INNER JOIN`. What would happen to the output if you changed all four `LEFT JOIN`s to `INNER JOIN`s? Which spans would disappear and why?

### 2. What does GROUP BY actually collapse? (concept)

In Step 5's aggregation query, what would the output look like if you removed `DISTINCT` from `count(DISTINCT s.span_id)`? How many rows would the run with 2 spans and 2 guardrail events produce in the joined result set before `GROUP BY` collapses them?

### 3. Why does rank() skip numbers? (concept)

Step 6's window function output shows ranks 1, 1, 1, 4 — not 1, 1, 1, 2. Why does `rank()` skip to 4? What would `dense_rank()` produce instead, and when would you choose one over the other?

### 4. What does the EXPLAIN plan tell you about the run lookup? (concept)

In Step 7's EXPLAIN output, the `run` table uses `Seq Scan` while `span`, `tool_call`, and `guardrail_event` use index scans. Why does Postgres sequential-scan the `run` table instead of using an index? Is this a problem?

### 5. Write a JOIN that reconstructs a single span's children (short code)

Write a single SQL query (inside a Python `cursor.execute`) that, given a `span_id`, returns the span's name, all its tool call names and results, and all its guardrail check names and outcomes — in one round trip using LEFT JOINs. Use the `span` variable already holding a valid span_id from the notebook.

```python
# Your query here — pass span_id as a parameter
cursor.execute("""
    -- your LEFT JOIN query here
""", (span_id,))
for row in cursor.fetchall():
    print(row)
```

### 6. Write a GROUP BY that counts guardrail outcomes per run (short code)

Write a SQL query (inside Python) that returns, for each `support-agent` run, the count of `'pass'` outcomes and the count of `'fail'` outcomes in separate columns. Your result should have columns: `run_id`, `passes`, `fails`.

```python
cursor.execute("""
    -- your GROUP BY query here
""")
for row in cursor.fetchall():
    print(row)
```

### 7. Applied: a query that returns too many rows (applied)

A colleague writes this query to get "all tool calls for a run":

```python
cursor.execute("""
    SELECT r.run_id, s.span_name, tc.tool_name, tc.result
    FROM run r
    JOIN span s ON s.run_id = r.run_id
    JOIN tool_call tc ON tc.span_id = s.span_id
    WHERE r.agent_name = 'support-agent'
""")
rows = cursor.fetchall()
print(f"Got {len(rows)} rows")
```

They expected 4 rows (one tool call per run across 4 runs), but got more. What went wrong? How would you fix the query or the Python code to get the expected count?

---

## Answer Key

### 1. Why LEFT JOIN, not INNER JOIN?

Changing all `LEFT JOIN`s to `INNER JOIN`s would drop any span that has no children on at least one side. Specifically, `retrieve_orders` (which has a tool call but no guardrail events) would disappear when the `guardrail_event` join is `INNER`, because there's no matching guardrail row to satisfy the join condition. Similarly, `generate_answer` (which has guardrail events but no tool calls) would disappear when the `tool_call` join is `INNER`. `LEFT JOIN` preserves every span and fills `NULL` for missing children.

### 2. What does GROUP BY actually collapse?

Without `DISTINCT`, the JOIN produces one row per (span, child) pair. A run with 2 spans and 2 guardrail events produces: span 1 × 1 tool call = 1 row, span 2 × 2 guardrail events = 2 rows, total 3 joined rows. `count(s.span_id)` without `DISTINCT` would count span 2 twice (once per guardrail event), giving an incorrect span count of 3 instead of the real 2. `count(DISTINCT s.span_id)` ensures each span is counted once regardless of how many times it appears in the joined result.

### 3. Why does rank() skip numbers?

`rank()` assigns the same rank to tied values, then skips numbers: if three rows tie at rank 1, the next rank is 4 (not 2). This reflects the position the row would occupy if the tied rows were expanded. `dense_rank()` does not skip — it would produce 1, 1, 1, 2. Use `rank()` when position matters (e.g., "top 3 runs"); use `dense_rank()` when you want consecutive ranks (e.g., "tier 1, tier 2").

### 4. What does the EXPLAIN plan tell you about the run lookup?

Postgres uses a sequential scan on `run` because the table is tiny (4 rows) — the planner correctly determines that scanning 4 rows is cheaper than doing an index lookup. This is not a problem; it's optimal behavior. As the `run` table grows into thousands of rows, Postgres will automatically switch to an index scan if one exists on the filtered column. The key insight: the planner chooses the cheapest path based on table size, not on a fixed rule.

### 5. Write a JOIN that reconstructs a single span's children

```python
cursor.execute("""
    SELECT s.span_name,
           tc.tool_name, tc.result,
           ge.check_name, ge.outcome
    FROM span s
    LEFT JOIN tool_call tc ON tc.span_id = s.span_id
    LEFT JOIN guardrail_event ge ON ge.span_id = s.span_id
    WHERE s.span_id = %s
    ORDER BY tc.tool_call_id, ge.guardrail_event_id
""", (span_id,))
for row in cursor.fetchall():
    print(row)
```

### 6. Write a GROUP BY that counts guardrail outcomes per run

```python
cursor.execute("""
    SELECT r.run_id,
           count(*) FILTER (WHERE ge.outcome = 'pass') AS passes,
           count(*) FILTER (WHERE ge.outcome = 'fail') AS fails
    FROM run r
    JOIN span s ON s.run_id = r.run_id
    JOIN guardrail_event ge ON ge.span_id = s.span_id
    WHERE r.agent_name = 'support-agent'
    GROUP BY r.run_id
    ORDER BY r.run_id
""")
for row in cursor.fetchall():
    print(row)
```

### 7. Applied: a query that returns too many rows

The query uses `JOIN` (inner) on `span` and `tool_call`, which correctly filters to only spans with tool calls. The issue is that `WHERE r.agent_name = 'support-agent'` returns **all** support-agent runs — not just the latest one. If there are 4 support-agent runs and each has 1 span with 1 tool call, the result is 4 rows. But if a run has multiple spans with tool calls, each span's tool call appears as a separate row, inflating the count beyond 4. To get exactly the latest run's tool calls, add `AND r.run_id = (SELECT max(run_id) FROM run WHERE agent_name = 'support-agent')` to the `WHERE` clause.
