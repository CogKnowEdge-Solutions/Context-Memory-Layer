# Lab 6 — Alerting on Anomalies: Knowledge Check

Complete these exercises after finishing the lab. The answer key is at the bottom — try each one before looking.

---

## Exercises

### 1. What exactly is an alert, as this lab defines it? (concept)

Lab 6's whole thesis is "an alert is a query that returns rows only when something is wrong." Step in
detail what the **threshold** is, what the **metric** is, and what **"firing"** means. Then say what
an *empty* result set means and why that is a *good* thing rather than an error.

### 2. Row-level threshold vs grouped threshold: what differs? (concept)

Step 5a (`WHERE total_cost > 1.0`) and Step 5b (`HAVING count(*) > 4`) are both "fire when too
much," but one uses `WHERE` and the other uses `HAVING`. Explain precisely what each one measures,
why Step 5b needs a `GROUP BY`, and what each would detect that the other could not.

### 3. Why can't the fixed error-rate alert catch `tricky`? (concept)

Step 4's static alert (`HAVING error rate > 50`) stays silent on `tricky`, yet Step 8's baseline alert
fires on it. Using the seed values (recent `33%`, baseline `0%`, margin `25` points, window
`60 minutes`), explain the two different reasons each alert gives.

### 4. Fixed vs percentile threshold: which one "maintains itself"? (concept)

Step 7 compares a hard-coded `120s` budget to `percentile_cont(0.95)` derived from the workload.
Describe a scenario where the fixed `120s` budget would be wrong but the percentile would adapt, and
a scenario where the percentile could be *more* surprising to reason about than a fixed number.

### 5. Write the volume alert for a stricter spike (short code)

Write a `cursor.execute` that returns every hour bucket containing **more than 6** tagged runs
(`agent_name` matching `pytest-lab6-%`), ordered most-loaded-first. Start from Step 5b's query and
change only what must change. State, in a sentence, whether `bursty`'s five-run burst would still
appear under this stricter threshold.

### 6. Write the retry-storm alert for a single tool (short code)

Step 6 groups tool calls by `(run, tool_name)` and fires at `count(*) >= 5`. Write a
`cursor.execute` that instead returns, for each tagged run, only the `check_status` calls: the run's
`agent_name`, `tool_name`, and a count of attempts, filtering the `tool_name` in the `WHERE` and
grouping by run. Reuse the `tool_call → span → run` join idiom from Step 6.

### 7. Applied: a baseline alert for cost, not errors (applied)

The relative idea from Step 8 works for any metric. Write a `WITH recent / baseline` query (two CTEs)
that returns each tagged logical agent whose **average cost** in the last `30 minutes` deviates from
its own older baseline average cost by more than `0.10` (absolute). Use `NULLIF(..., 0)` and
`COALESCE` the same way Step 8 does, and require at least `2` recent runs. Explain in one sentence
why comparing an agent's cost to *its own past* is more robust than a single global cost cap.

---

## Answer Key

### 1. What exactly is an alert?

- The **threshold** is the `WHERE`/`HAVING` clause that encodes the "bad" condition (e.g.
  `HAVING error_rate > 50`).
- The **metric** is the value being measured — the grouped error rate, a run's `total_cost`, a count
  of runs in an hour, a retry count, a latency.
- **"Firing"** means the query returned **at least one row** — a non-empty result set is the alarm,
  and the rows themselves are the evidence.
- An **empty** result set means the system is healthy. It is a *good* signal precisely because the
  whole design is "return rows only when something is wrong"; zero rows means nothing is wrong, so
  the absence of a result is not an error but the success case a scheduler waits for.

### 2. Row-level vs grouped threshold

- **Step 5a (`WHERE total_cost > 1.0`)** is a **row-level** filter: it looks at each `run` by itself
  and fires when an *individual* run exceeds the cap. No grouping is needed, so it can only catch
  single-run problems.
- **Step 5b (`HAVING count(*) > 4`)** is a **grouped** filter: after `GROUP BY
  date_trunc('hour', started_at)` folds runs into hour buckets, `HAVING` decides whether an entire
  *group* is too big. It needs the `GROUP BY` because the threshold is over an aggregate count, and
  it catches load problems (a crowded hour) that no single row would reveal.
- Each detects something the other cannot: the row-level alert sees one pathological run; the grouped
  alert sees too many *ordinary* runs at once.

### 3. Why the fixed alert misses `tricky`

- **Step 4 (fixed):** it fires only when the *absolute* error rate exceeds `50%`. `tricky`'s recent
  rate is `33%`, which is **below** `50%`, so it is absent — the fixed number is simply not crossed.
- **Step 8 (relative):** it never looks at a fixed number. It compares `tricky`'s *recent* `33%`
  against *`tricky`'s own* older baseline `0%`; the difference is `33` points, which clears the `25`
  margin, so it fires. Two different reasons: one checks absolute value, the other checks
  deviation-from-self.

### 4. Fixed vs percentile threshold

- **Fixed wrong, percentile right:** if the workload's typical run doubled in duration overnight the
  hand-picked `120s` would become meaningless (either drowning in false alerts if typical runs now
  exceed it, or catching nothing new if it was already slack), whereas `percentile_cont(0.95)`
  recomputes from the current data and always flags only the true top ~5% — the alert "maintains
  itself."
- **Percentile more surprising:** the p95 value is *emergent*, so you must query it to know what the
  threshold actually is at any moment; a human cannot predict it by reading the code. A fixed number
  is transparent and auditable, which some teams prefer even at the cost of manual upkeep.

### 5. Write the volume alert for a stricter spike

```python
cursor.execute("""
    SELECT date_trunc('hour', started_at) AS hour_bucket, count(*) AS runs
    FROM run
    WHERE agent_name LIKE %s
    GROUP BY hour_bucket
    HAVING count(*) > %s
    ORDER BY runs DESC
""", ("pytest-lab6-%", 6))
```

`bursty`'s five-run burst would **not** appear: `5 > 6` is false, so the stricter threshold stays
silent on it — only a genuine `7+` run hour bucket would trip this version.

### 6. Write the retry-storm alert for a single tool

```python
cursor.execute("""
    SELECT r.agent_name, tc.tool_name, count(*) AS attempts
    FROM tool_call tc
    JOIN span s ON s.span_id = tc.span_id
    JOIN run r  ON r.run_id  = s.run_id
    WHERE r.agent_name LIKE %s
      AND tc.tool_name = %s
    GROUP BY r.agent_name, tc.tool_name
    ORDER BY attempts DESC
""", ("pytest-lab6-%", "check_status"))
```

The difference from Step 6 is that the tool name moves from being the group key to a `WHERE` filter,
so the result is scoped to `check_status` calls only, grouped per run.

### 7. Applied: a baseline alert for cost

```python
cursor.execute("""
    WITH recent AS (
        SELECT split_part(agent_name, '-', 3) AS agent_name,
               count(*) AS recent_runs,
               avg(total_cost) AS recent_avg
        FROM run
        WHERE agent_name LIKE %s
          AND started_at >= now() - interval '30 minutes'
        GROUP BY split_part(agent_name, '-', 3)
    ),
    baseline AS (
        SELECT split_part(agent_name, '-', 3) AS agent_name,
               avg(total_cost) AS base_avg
        FROM run
        WHERE agent_name LIKE %s
          AND started_at < now() - interval '30 minutes'
        GROUP BY split_part(agent_name, '-', 3)
    )
    SELECT r.agent_name,
           round(COALESCE(r.recent_avg, 0), 4) AS recent_avg,
           round(COALESCE(b.base_avg, 0), 4)   AS base_avg
    FROM recent r
    LEFT JOIN baseline b ON b.agent_name = r.agent_name
    WHERE r.recent_runs >= %s
      AND (r.recent_avg - COALESCE(b.base_avg, 0)) > %s
    ORDER BY (r.recent_avg - COALESCE(b.base_avg, 0)) DESC
""", ("pytest-lab6-%", "pytest-lab6-%", 2, 0.10))
```

Comparing cost to an agent's *own past* is more robust than a single global cap because "expensive"
is relative: an agent that normally runs cheap operations might still cost tiny amounts in absolute
terms yet suddenly be 10× its own normal, which a global cap would never notice — the per-agent
baseline detects exactly that kind of anomaly.
