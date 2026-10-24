# Optimize Cost: Storage, Bloat and Right-Sizing — Assignment

The code exercises build their own small tables, so run them in a scratch file with a Python connection called `conn` (opened with `psycopg.connect(...)`) or in any Structured Query Language (SQL) window. Use PostgreSQL 18 (14 or newer works for everything here).

## Exercises

### Exercise 1 — Find what's taking space
Write the SQL to show, for every table in the `public` schema, its table size, indexes size, and total size, with sizes printed nicely. Which function gives the total including TOAST and indexes?

### Exercise 2 — Spot an unused index
Look at `pg_stat_user_indexes`. Write the SQL to list any index on schema `public` with `idx_scan = 0`, along with the table name and index size in human-readable form. When would you be *cautious* about dropping such an index?

### Exercise 3 — Bloat before and after vacuum
Explain the difference between `VACUUM` and `VACUUM FULL`. Why would you usually choose `VACUUM` over `VACUUM FULL` in production, and which one reclaims disk space to the operating system by rewriting the file?

### Exercise 4 — Pick better types
You need to store a two-letter country code, a product status (`'active'|'inactive'|'draft'`), and a price with cents. Compare `char(2)`, `varchar(2)`, `text` for the code/status, and `numeric` vs `integer` vs `bigint` for cents. Give a short recommendation for each.

### Exercise 5 — Cheaply retire old data
You have monthly partitions `logs_2025_09`, `logs_2025_10`, ... By the end of October you want to remove all of September's data. (a) If it's in a partition, write the single SQL statement that removes it fastest. (b) If it were a single heap table, why would `DELETE FROM logs WHERE log_time < '2025-10-01'` be a much worse idea for 50 million rows?

### Exercise 6 — TOAST and right-sizing
What is TOAST? Name one thing you can do to avoid pushing values into TOAST. Also give two settings you'd look at first when right-sizing memory for a PostgreSQL server and say what each one tells the planner/server.

### Exercise 7 — Connections and pooling
Why can too many direct client connections hurt a PostgreSQL server? Name the tool used to pool them and the difference between `transaction` and `session` pooling modes.

## Answer Key

### Exercise 1
**Answer:**

```sql
SELECT n.nspname,
       c.relname,
       pg_size_pretty(pg_table_size(c.oid))  AS table_size,
       pg_size_pretty(pg_indexes_size(c.oid)) AS indexes_size,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
ORDER BY pg_total_relation_size(c.oid) DESC;
```

`pg_total_relation_size(oid)` gives the total including TOAST tables and indexes.

**Why:** `pg_table_size` is just the main fork; to see real space used you need total relation size (and database size for the whole cluster/database).

### Exercise 2
**Answer:**

```sql
SELECT s.schemaname, s.relname, s.indexrelname,
       pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size
FROM pg_stat_user_indexes s
JOIN pg_index i ON i.indexrelid = s.indexrelid
WHERE s.schemaname = 'public' AND s.idx_scan = 0
ORDER BY pg_relation_size(s.indexrelid) DESC;
```

Be **cautious** if the index is used to enforce a constraint (a unique or primary key index is used by the constraint system even if scans look low in some contexts), if it's needed for `replica identity`, or if your workload is still warming up / the statistics haven't accumulated scans yet. Also check if queries might use it in certain plans.

**Why:** `idx_scan = 0` strongly suggests unused, but never drop blindly — verify constraints and real usage first.

### Exercise 3
**Answer:** `VACUUM` marks dead tuples as reusable and updates visibility; it does **not** usually shrink the table file back to the operating system. `VACUUM FULL` rewrites the entire table into a new file, reclaims space to disk, but requires an **access exclusive lock** and is expensive. Choose `VACUUM` (and tune autovacuum) for normal maintenance; use `VACUUM FULL` rarely, as a last resort or during planned downtime. `VACUUM FULL` reclaims disk space to the OS by rewriting the file.

**Why:** `VACUUM FULL` compacts by copying, so it returns free space to the filesystem; plain `VACUUM` keeps the file the same size and just reuses free space inside it.

### Exercise 4
**Answer:**
- **Two-letter country code:** use `char(2)` only if fixed and always present, else `text` (or `varchar(2)`). `char(n)` pads; `text` is flexible and efficient in PostgreSQL.
- **Status (`'active'|'inactive'|'draft'`):** use `text` with a `CHECK (status IN (...))` or a `ENUM` type. `text` is simple and easy to change; avoid `char(10)` (wasteful).
- **Price with cents:** store as **integer** cents (`integer` or `bigint`) for exact arithmetic and smallest size/speed. `numeric` is exact but larger/slower for simple money arithmetic; avoid floats.

**Why:** integers are exact, smallest, and fast; `text` is PostgreSQL's preferred flexible string type.

### Exercise 5
**Answer:** (a) If `logs_2025_09` is a partition: `DROP TABLE logs_2025_09;` (or detach then drop). (b) `DELETE FROM logs WHERE log_time < '2025-10-01'` deletes row by row: it generates a huge amount of WAL, bloats the table and indexes, can take hours, locks rows, and `VACUUM` will need to clean up all those dead tuples. Dropping a partition removes the whole file instantly with minimal overhead.

**Why:** partition drop is metadata+file removal; row delete is DML with full MVCC overhead.

### Exercise 6
**Answer:** **TOAST** (The Oversized-Attribute Storage Technique) stores large column values out of line in a separate TOAST table, compresses them, and stores only a pointer in the main row. To avoid TOAST, keep values small (don't store huge blobs unnecessarily, consider splitting, or compress at the application layer). Two memory settings: **`shared_buffers`** — how much memory PostgreSQL uses to cache data pages (tells it how much it can keep hot); **`effective_cache_size`** — an estimate of how much memory the OS has available for disk caching (helps the planner choose index scans vs sequential scans).

**Why:** TOAST prevents huge rows from bloating pages; right-sizing cache settings helps the planner make realistic cost estimates.

### Exercise 7
**Answer:** Each connection uses memory and has overhead in PostgreSQL; too many direct connections can exhaust RAM and cause contention. Use **PgBouncer** as a connection pooler. **Transaction pooling** returns the server connection to the pool after each transaction (best for most web apps), while **session pooling** keeps a server connection tied to a client for the entire session (less flexible but needed for features that depend on session state like prepared statements in some cases or temp tables).

**Why:** pooling multiplexes many clients onto a small number of backend connections, cutting memory usage and improving scalability.
