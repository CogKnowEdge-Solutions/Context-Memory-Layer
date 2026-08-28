# Lab 4 — Filtering, Search, and Pagination: Knowledge Check

Complete these exercises after finishing the lab. The answer key is at the bottom — try each one before looking.

---

## Exercises

### 1. Time-window vs range filter: what's the difference? (concept)

Lab 4's Step 4 filters by time (`started_at >= now() - interval '24 hours'`) and Step 5 filters by cost (`total_cost > 0.02`). Both use a `WHERE` clause and a comparison. What actually distinguishes a **time-window** filter from a **range** filter? Could a time filter ever be written the same way as a cost filter, and if so how?

### 2. Why parameterized queries instead of string interpolation? (concept)

Lab 4 always passes values as `%s` parameters — never by pasting them into the SQL string. Give the two reasons this matters specifically for an **audit database**. Why is string interpolation a worse idea here than in, say, a one-off analysis script?

### 3. IN vs = ANY(array): what's the real difference? (concept)

Step 6 shows that `status = ANY(%s)` can express "in this set of statuses" with a single parameter. Write the `IN` form that means the same thing, and explain the practical reason a Python program would prefer `= ANY(array)` when the set of values is built at runtime.

### 4. ILIKE vs full-text search: when does each win? (concept)

Step 7 shows `ILIKE '%refund_query%'` finding payloads by substring. Full-text search (`to_tsvector` / `to_tsquery`) is described as the scalable alternative. State one scenario where `ILIKE` is the right choice and one where full-text search is the right choice.

### 5. OFFSET vs keyset: what breaks? (concept)

Step 8 contrasts `LIMIT %s OFFSET %s` with keyset (`WHERE (started_at, run_id) < (%s, %s)`). Name the two problems OFFSET pagination has at scale, and explain why the composite `(started_at, run_id)` key is needed rather than `started_at` alone.

### 6. Write a query that finds runs with a payload mention (short code)

Write a `cursor.execute` that returns the `run_id` and `status` of every tagged run (`agent_name` matching `pytest-lab4-%`) that has at least one `event` whose `payload` contains the case-insensitive substring `"failed"` (using ILIKE). Reuse the join idiom from Step 7.

### 7. Applied: a paged "recent failures" report (applied)

A colleague wants a dashboard query: page through the *failed* runs of a given agent, newest first, one page of 5 at a time. Write the **keyset** version — the query that returns the first page, and the query that returns the next page given the last row seen — and say whether combining the keyset key with a `status = %s` filter is valid, and why.

---

## Answer Key

### 1. Time-window vs range filter

Both are numerical comparisons, and a time filter *is* a range filter — timestamps are just numbers. `started_at >= now() - interval '24 hours'` is a one-sided range on a time column; `total_cost > 0.02` is a one-sided range on a money column. The distinction is the *column's meaning and scale*, not the SQL shape: time windows are "since when" questions on a column that grows monotonically as the log appends, so they are the most frequent audit filter and the most important to index. You could absolutely write a time filter with a concrete literal — `started_at >= '2026-08-27 10:00:00+00'` — but the lab computes it with `now() - interval` so the window is always relative to the current moment.

### 2. Why parameterized queries

Two reasons, both acute in an audit database:
- **Injection safety.** The log stores untrusted data retrieved from live agent activity. If a value (an `agent_name`, a search `needle`, a status) is pasted into a SQL string, an attacker who controls that value can inject their own SQL — for example a `'; DROP TABLE ... --` fragment — turning a log lookup into a data-destruction or data-exfiltration path. Parameters send the value as data, and the driver binds it safely so it can never be parsed as SQL.
- **Correctness and cleanliness.** Values with quotes, special characters, or `%` wildcards don't need manual escaping, and a Python list is passed straight to `= ANY(%s)` without generating a variable number of placeholders. In a one-off analysis script the risk is lower because the values are usually your own constants; in an audit system the values come from untrusted sources, so the safer pattern is mandatory.

### 3. IN vs = ANY(array)

The equivalent `IN` form for `status = ANY(%s)` with the list `['error', 'timeout']` is:

```sql
status IN ('error', 'timeout')
```

`IN` reads naturally but is awkward to build at runtime: with a variable-length Python list you'd have to produce the right number of `%s` placeholders (`IN (%s, %s, ...)`) and expand the list to match. `= ANY(%s)` takes the whole list as a single array parameter, so the query text never changes no matter how long the list is, and you keep exactly one bound value. That single-parameter property is also nice for injection safety — one placeholder, one bound value, nothing constructed from user input.

### 4. ILIKE vs full-text search

- **ILIKE wins** for a quick, exact substring poke at a small log, or when you genuinely need a literal substring match (e.g. searching payloads for a specific hex token or an exact API key fragment) and understand that the search will scan. It requires zero setup.
- **Full-text search wins** for a large, growing log where you search free text repeatedly. `to_tsvector`/`to_tsquery` is token-aware (it can be indexed with a GIN index, so queries stay fast), understands language (stops words, stemming), and matches on word semantics rather than raw substrings. If payloads are long prose and the table has millions of rows, full-text is the scalable choice.

### 5. OFFSET vs keyset

OFFSET pagination has two problems:
- **Drift.** As new rows are inserted (or deleted) between page requests, the *positions* shift, so `OFFSET N` can re-show a row already seen or skip one. The page boundaries aren't anchored to the data itself; they're anchored to a changing count.
- **Degrading cost.** The database must scan and discard every skipped row on every page, so cost grows linearly with the offset — the deeper the page, the slower the query, even though the page size is constant.

The composite `(started_at, run_id)` key is needed because `started_at` alone can tie — two runs can share the exact same instant — and a tie makes `started_at < %s` ambiguous about which row is "the next one." Adding `run_id` (the unique primary key) as a tiebreaker makes the ordering and the seek fully deterministic. A single-column `started_at < %s` is fine only if you can guarantee the values are unique, which a log generally can't.

### 6. Write a query that finds runs with a payload mention

```python
cursor.execute("""
    SELECT DISTINCT r.run_id, r.status
    FROM run r
    JOIN event e ON e.run_id = r.run_id
    WHERE r.agent_name LIKE %s
      AND e.payload ILIKE %s
    ORDER BY r.run_id
""", ("pytest-lab4-%", "%failed%"))
```

`ILIKE '%failed%'` matches the substring case-insensitively. Because a run can have many events, `SELECT DISTINCT` collapses multiple payload hits on the same run into one row. The `JOIN event` pulls the payload into scope; without it, we couldn't search text that lives in the `event` table.

### 7. Applied: a paged "recent failures" report

First page — newest 5 failed runs for a given agent:

```python
agent = "%some-agent%"
cursor.execute("""
    SELECT run_id, status, started_at FROM run
    WHERE agent_name LIKE %s AND status = %s
    ORDER BY started_at DESC, run_id DESC
    LIMIT 5
""", (agent, "error"))
page1 = cursor.fetchall()
```

Next page — keyset from the last row of the previous page:

```python
last = page1[-1]  # (run_id, status, started_at)
cursor.execute("""
    SELECT run_id, status, started_at FROM run
    WHERE agent_name LIKE %s AND status = %s
      AND (started_at, run_id) < (%s, %s)
    ORDER BY started_at DESC, run_id DESC
    LIMIT 5
""", (agent, "error", last[2], last[0]))
page2 = cursor.fetchall()
```

Combining the keyset key with `status = %s` is completely valid — and important. The keyset predicate is just another `WHERE` condition; it locates the position in the *filtered* stream, and filters compose with `AND`. That's the whole power of keyset: you seek within the result set you actually want (failed runs of this agent), so the tiebreaker and the status filter work together cleanly. If the sort key and the filter touched the same column ambiguously you'd be more careful, but `started_at`/`run_id` (ordering) and `status` (filtering) are independent, so there is no conflict.
