# Lab 5 — Metrics and Dashboards: Knowledge Check

Complete these exercises after finishing the lab. The answer key is at the bottom — try each one before looking.

---

## Exercises

### 1. View vs materialized view: what actually differs? (concept)

Lab 5's Step 4 creates a *view* for error rate and Step 8 creates a *materialized view* for the whole-log error count. State, precisely, what each one stores, what happens when you read it, and what happens when the underlying `run` table gains a new row.

### 2. Why does that difference become a *problem* at scale? (concept)

Step 8 runs `EXPLAIN` on a whole-log aggregate. What does the plan show, and why is that a reason a dashboard wouldn't want to read a plain *view* for a whole-log metric on every refresh? What is the trade-off a materialized view introduces in exchange?

### 3. FILTER vs WHERE inside an aggregate: same thing or not? (concept)

Step 4 uses `count(*) FILTER (WHERE status = 'error')` *inside* a `GROUP BY` query, while Lab 4 filtered whole rows with a `WHERE` clause. Explain the difference in what each filters: what data the `WHERE` shrinks before grouping vs what `FILTER` shrinks during aggregation.

### 4. Averages versus percentiles (concept)

Step 6 computes both `avg(total_cost)` and `percentile_cont(0.95) WITHIN GROUP (ORDER BY total_cost)`. Describe the scenario in the lab's seed where the average would mislead, and say precisely what the 95th-percentile number tells you that the average does not.

### 5. `date_trunc` and the shape of a time series (concept)

Step 5 buckets runs by `date_trunc('hour', started_at)`. Write the query that answers "how many runs started in each day of the last week?" instead of per hour (you only need to change the truncation unit and the window), and explain what would happen if two runs started at `14:03` and `14:51` with **no** truncation.

### 6. Write the guardrail-fail metric for a single check (short code)

Write a `cursor.execute` that returns, for each tagged run (`agent_name` matching `pytest-lab5-%`) that has a `toxicity_scan` guardrail check, the run's `agent_name` and that check's `outcome`. Reuse the two-table join idiom from Step 7. What must you add to turn this into a *fail rate* for `toxicity_scan` across the whole log?

### 7. Applied: refresh a weekly cost snapshot (applied)

A manager wants a weekly "average cost per agent" number, and is happy to see it at most one week old. Write two statements: (a) the `CREATE MATERIALIZED VIEW` that stores `agent_name` and `avg(total_cost)`, scoped to `pytest-lab5-%`; and (b) the one statement that brings it up to date a week later. Then explain — in a sentence — why a plain view would be a worse fit for a *weekly* metric read repeatedly, and why a materialized view is the right call here.

---

## Answer Key

### 1. View vs materialized view

- A **view** stores the *query definition* only. Reading it re-runs the underlying SQL against the current table contents, so it always reflects new rows immediately — but the recompute happens on every read.
- A **materialized view** stores the *result rows* on disk. Reading it is a plain table read (instant), but it does **not** notice new rows in `run` on its own. After a new row is inserted, the materialized view still reports the old totals until you run `REFRESH MATERIALIZED VIEW`, which re-runs the query and swaps in fresh data.
- Net: views are always current but recompute each read; materialized views are instant to read but go stale until explicitly refreshed.

### 2. The scaling problem

`EXPLAIN` shows a **Seq Scan on run** — Postgres must read every row in the table to count errors. With a plain view, that full scan would run on *every* dashboard refresh, even though the whole-log answer changes only slightly between reads. A materialized view avoids that: it pays the expensive scan **once** when built (and again only on `REFRESH`), then serves the stored answer for every intermediate read. The trade-off is **staleness**: the stored snapshot does not include rows inserted since the last refresh, so you must choose how often to refresh — trading a little correctness-lag for a lot of speed.

### 3. FILTER vs WHERE

- A `WHERE` clause runs **before** grouping: it removes rows from the input set entirely, so the aggregation never sees them. `WHERE status = 'error'` would feed the `GROUP BY` *only* errored runs — which would break a query that wants counts of all statuses.
- A `FILTER (WHERE ...)` runs **during** aggregation, on a *per-output-row* basis: it decides, independently for each aggregate, which rows contribute. `count(*) FILTER (WHERE status = 'error')` counts only errored runs *while other aggregates in the same SELECT still count every run*. That is why Step 4 can return `total_runs`, `errored_runs`, and a rate all in one grouped row — a `WHERE`-only rewrite could not.

### 4. Averages versus percentiles

In the seed, `billing` has a `90 seconds` timeout among otherwise fast runs (5, 22, 6, 10-second runs). Its `avg` latency is dragged up toward the timeout, while its `p95` shows the value below which 95% of its runs fall — essentially ignoring the single extreme and reflecting the "normal" long-run behavior. The 95th-percentile tells you the **tail**: the value you expect to be at-or-below for 95% of runs, i.e. the worst case a dashboard should plan for — whereas the average says "in the middle," which the outlier distorts.

### 5. `date_trunc` and the shape of a time series

```sql
SELECT date_trunc('day', started_at) AS day_bucket, count(*) AS runs
FROM run
WHERE agent_name LIKE 'pytest-lab5-%'
  AND started_at >= now() - interval '7 days'
GROUP BY day_bucket
ORDER BY day_bucket;
```

Only the unit (`'day'` instead of `'hour'`) and the window change. Without truncation, `14:03` and `14:51` would be *different rows* in a `GROUP BY started_at` — a separate bucket per exact timestamp — so you'd get one bucket per run rather than one bucket per day. Truncation is what collapses many distinct timestamps into a small number of meaningful time windows.

### 6. Write the guardrail-fail metric for a single check

```python
cursor.execute("""
    SELECT r.agent_name, ge.outcome
    FROM guardrail_event ge
    JOIN span s ON s.span_id = ge.span_id
    JOIN run r ON r.run_id = s.run_id
    WHERE r.agent_name LIKE %s
      AND ge.check_name = %s
    ORDER BY r.agent_name
""", ("pytest-lab5-%", "toxicity_scan"))
```

To turn it into a **fail rate for `toxicity_scan`** across the whole log, add aggregation: `GROUP BY ge.check_name` (or a fixed filter for `toxicity_scan`), `count(*) AS total_checks`, `count(*) FILTER (WHERE ge.outcome = 'fail') AS failed_checks`, and `round(100.0 * failed / total, 1) AS fail_rate_pct` — the same shape as Step 7, optionally scoped to `check_name = 'toxicity_scan'`.

### 7. Applied: refresh a weekly cost snapshot

```sql
CREATE MATERIALIZED VIEW mv_weekly_cost AS
SELECT agent_name, round(avg(total_cost)::numeric, 4) AS avg_cost
FROM run
WHERE agent_name LIKE 'pytest-lab5-%'
GROUP BY agent_name;
```

```sql
REFRESH MATERIALIZED VIEW mv_weekly_cost;
```

A plain view is a worse fit because it would re-run the scan over the whole log (or the whole tagged set) on **every** read — a cost that grows with the log — while a weekly metric is read many times but only needs updating once a week. The materialized view pays the scan once per `REFRESH` (weekly) and serves the stored answer at every intermediate read, which is exactly the staleness-for-speed trade-off Step 8 demonstrated.
