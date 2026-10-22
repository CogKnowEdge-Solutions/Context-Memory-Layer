# Speed Up Queries with Indexes and EXPLAIN — Assignment

The code exercises build their own small tables, so run them in a scratch file with a Python connection called `conn` (opened with `psycopg.connect(...)`) or in any Structured Query Language (SQL) window. Use PostgreSQL 18 (16 or newer works for all but the skip-scan question).

## Exercises

### Exercise 1 — Is a Seq Scan bad?
What does `Seq Scan` mean in a plan, and name one situation where it is the right choice. See Section 7.

### Exercise 2 — Column order
Create this table and index, then run `EXPLAIN` on the three queries. Which of them can use the index well, and why?

```sql
CREATE TABLE t AS SELECT g AS a, g % 10 AS b FROM generate_series(1, 20000) AS g;
CREATE INDEX t_a_b ON t (a, b);
ANALYZE t;
-- Query 1: SELECT * FROM t WHERE a = 5;
-- Query 2: SELECT * FROM t WHERE b = 5;
-- Query 3: SELECT * FROM t WHERE a = 5 AND b = 5;
```

### Exercise 3 — A tiny index for a queue
A `jobs` table has 100,000 rows, and only about 100 of them have `state = 'queued'`. Workers repeatedly ask for the oldest queued jobs. Write the index and the query, and check with `EXPLAIN` that the index is used.

### Exercise 4 — Case-insensitive search
A `people(name TEXT)` table is searched with `WHERE lower(name) = 'ana'`. Create an index that helps this query. Will it also help `WHERE name = 'Ana'`?

### Exercise 5 — Choose the index type
Pick balanced tree (B-tree), Generalized Inverted Index (GIN) or Block Range Index (BRIN) for each: (a) equality lookups on an email column, (b) a 500-million-row log table queried by time range, and (c) searching rows whose `tags` array contains a word.

### Exercise 6 — Fix a slow page
This query gets slower on deep pages. Rewrite it with keyset pagination, given that the last `id` on the previous page was 40000:

```sql
SELECT id, title FROM posts ORDER BY id OFFSET 40000 LIMIT 10;
```

### Exercise 7 — A plan suddenly got worse
After loading millions of new rows, a query that was fast now takes minutes and `EXPLAIN` shows a `Seq Scan`. What is the first thing to try, and why?

## Answer Key

### Exercise 1
**Answer:** `Seq Scan` (sequential scan) means PostgreSQL read every row of the table. It is the right choice for a small table, or when the query needs a large share of the rows anyway.

**Why:** an index lookup has its own cost, so for tiny tables or "give me most of the table" queries, reading straight through is cheaper.

### Exercise 2
**Answer:** Queries 1 and 3 use the index well. Query 2 (`WHERE b = 5`) falls back to a `Seq Scan`.

**Why:** the index is sorted by `a` first, then `b`. Query 1 and 3 start with `a`. Query 2 skips `a`, and PostgreSQL 18 could only help with a skip scan if `a` had few different values, but it has 20,000, so reading the table is cheaper.

### Exercise 3
**Answer:**

```sql
CREATE TABLE jobs AS
  SELECT g AS id, CASE WHEN g % 1000 = 0 THEN 'queued' ELSE 'done' END AS state, TIMESTAMP '2026-01-01' + g * INTERVAL '1 minute' AS created_at
  FROM generate_series(1, 100000) AS g;
CREATE INDEX jobs_queued ON jobs (created_at) WHERE state = 'queued';
ANALYZE jobs;
EXPLAIN SELECT id FROM jobs WHERE state = 'queued' ORDER BY created_at LIMIT 5;
```

The plan shows an index scan on `jobs_queued`.

**Why:** a partial index holds only the queued rows, so it is tiny, and the query repeats `state = 'queued'` so PostgreSQL knows the index applies.

### Exercise 4
**Answer:**

```sql
CREATE TABLE people AS SELECT 'Name' || g AS name FROM generate_series(1, 20000) AS g;
CREATE INDEX people_lower_name ON people (lower(name));
ANALYZE people;
EXPLAIN SELECT * FROM people WHERE lower(name) = 'name42';
```

It will not help `WHERE name = 'Ana'`.

**Why:** an expression index stores the result of `lower(name)`, so only queries that use the same expression can use it.

### Exercise 5
**Answer:** (a) B-tree, (b) BRIN, (c) GIN.

**Why:** B-tree is the default and handles equality. BRIN is tiny and works when the column's order follows the table's physical order, as time does in a log. GIN indexes the items inside a value, which suits arrays.

### Exercise 6
**Answer:**

```sql
SELECT id, title FROM posts WHERE id > 40000 ORDER BY id LIMIT 10;
```

**Why:** the query starts at the last `id` seen instead of counting and discarding 40,000 rows. You can step to the next page but cannot jump to an arbitrary page number.

### Exercise 7
**Answer:** Run `ANALYZE` on the table.

**Why:** the planner chooses plans from statistics, and after a huge load the old statistics describe a much smaller table. `ANALYZE` refreshes them, and the planner usually picks a good plan again.
