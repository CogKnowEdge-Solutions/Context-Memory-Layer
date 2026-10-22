# Tune Workloads with Stats and Partitioning — Assignment

The code exercises build their own small tables, so run them in a scratch file with a Python connection called `conn` (opened with `psycopg.connect(...)`) or in any Structured Query Language (SQL) window. Use PostgreSQL 18 (14 or newer works for everything here).

## Exercises

### Exercise 1 — Turn on the workload receipt
`pg_stat_statements` records every query's calls and times. What must be configured on the *server* before the counters work, and when does it take effect? What happens in the lesson's Step 2 if you skip it? See Sections 7 and 9.

### Exercise 2 — Statistics went stale
A team loads 2 million new rows into `orders` every night. After last night's load, a report that used to take 50 ms now takes 6 s, and `EXPLAIN` shows an estimate far below the real row count. What is the first fix, why does it work, and why did the problem appear only after the load?

### Exercise 3 — Correlated columns
A `deliveries` table has `city TEXT` and `postcode TEXT` where each city has exactly one postcode. The query `WHERE city = 'Lagos' AND postcode = '100000'` gets a wildly low row estimate. Write the `CREATE STATISTICS` statement that teaches the planner about the relationship, and name the command that must follow it before the new fact is used.

### Exercise 4 — Spot and fix an N+1 loop
This Python code fetches details for 500 customers. Identify the N+1 pattern, and rewrite it as one round trip. Which `pg_stat_statements` column would show the old loop as a single entry with a huge count?

```python
rows = []
with conn.cursor() as cur:
    for customer_id in range(1, 501):
        cur.execute("SELECT name FROM customers WHERE id = %s", (customer_id,))
        rows.append(cur.fetchone())
```

### Exercise 5 — Choose the partition type
Pick range, list or hash partitioning for each: (a) a 500-million-row event log queried mostly by date ranges, (b) a `shipments` table where support constantly asks "show me everything with `status = 'lost'`", and (c) a huge `sessions` table with no useful column to order by, where the goal is simply to keep every piece under a few gigabytes.

### Exercise 6 — Read a pruned plan
You query a table range-partitioned by month. The first `EXPLAIN` shows one `Seq Scan` on a single partition; after `SET enable_partition_pruning = off`, the same query shows an `Append` scanning all twelve. Which plan prunes, what caused the planner to skip partitions in the first plan, and roughly how much less disk should the pruned plan read?

### Exercise 7 — Workers or no workers
A heavy report's plan shows `Gather` with `Workers Launched: 2`. A colleague asks why every query does not use workers. Give two reasons smaller queries stay single-threaded, and name the setting that caps workers per query.

## Answer Key

### Exercise 1
**Answer:** The server must list `pg_stat_statements` in `shared_preload_libraries` in `postgresql.conf` and be restarted, so the counters exist before the first query runs. If you skip it, `CREATE EXTENSION` still succeeds, but the first *call* to the counters raises an error (`SQLSTATE 55000`) — the lesson catches it, prints a setup note, and every other step still works.

**Why:** the counters sit in shared memory allocated at startup; an extension loaded later could not have counted the queries that ran before it existed.

### Exercise 2
**Answer:** Run `ANALYZE orders`. The statistics on file still describe the table before the load, so the planner's estimate (table size × selectivity) is far too low and it picks a plan built for a small result — likely an index scan where a sequential scan is now cheaper. `ANALYZE` re-samples the table, the estimate jumps to the real count, and the plan flips back.

**Why:** estimates only refresh when someone samples the table: `ANALYZE` manually or autovacuum automatically. A 2-million-row load makes the old sample worthless.

### Exercise 3
**Answer:**

```sql
CREATE STATISTICS city_postcode (dependencies) ON city, postcode FROM deliveries;
ANALYZE deliveries;
```

**Why:** regular statistics describe each column alone, so the planner multiplies the two separate estimates as if the columns were independent. The `dependencies` statistics object records that each city always arrives with one postcode, and the next `ANALYZE` uses that fact — the estimate then lands close to the real count.

### Exercise 4
**Answer:** The loop runs one query per customer — 500 round trips for 500 rows. Batched version:

```python
ids = list(range(1, 501))
with conn.cursor() as cur:
    cur.execute("SELECT id, name FROM customers WHERE id = ANY(%s) ORDER BY id", (ids,))
    rows = cur.fetchall()
```

In `pg_stat_statements` the old loop appears as one entry with `calls = 500` (the `calls` column); the batch shows `calls = 1`.

**Why:** every round trip costs network latency plus planning time, so 500 small queries cost far more than one query carrying 500 ids — usually 10× to 100× on a real network.

### Exercise 5
**Answer:** (a) Range partitioning — dates are ordered, and queries name ranges the planner can prune. (b) List partitioning — one partition per status makes "everything lost" read exactly one partition. (c) Hash partitioning — hashing `id` (or another always-populated key) spreads rows evenly with no ordering assumption, which is the point when no column splits the data naturally.

**Why:** match the strategy to the query pattern: ordered keys → range, few known values → list, neither → hash for even piece sizes.

### Exercise 6
**Answer:** The first plan (one `Seq Scan`) prunes. The `WHERE` clause gives the month column a bounded range, so the planner works out that only one partition's range can hold matching rows and plans only that scan. The pruned plan reads roughly one partition's worth of pages — about 1/12 of the table here — instead of all twelve.

**Why:** pruning eliminates whole partitions before execution; with it off, the `Append` must open and filter every partition, paying the read cost on data the query cannot need.

### Exercise 7
**Answer:** Two reasons: (1) launching workers has a fixed setup cost, which only pays back when the scan is large and processor-heavy; (2) tiny queries spend their time elsewhere (round trip, parsing), so parallelism adds overhead without saving any. The cap is `max_parallel_workers_per_gather` (default 2); each worker's share also has to be worth `parallel_setup_cost` and `parallel_tuple_cost` before the planner chooses them.

**Why:** the planner compares the parallel plan's cost against the serial one — workers are a cost-based decision, not a default, which is why `Gather` appears on the heavy report and not on point lookups.
