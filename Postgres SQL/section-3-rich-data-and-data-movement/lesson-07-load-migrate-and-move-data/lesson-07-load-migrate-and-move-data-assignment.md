# Load, Migrate and Move Data — Assignment

Exercises that need a database use a Python connection called `conn`, opened with `psycopg.connect(...)` and your own server settings, in a scratch file. Use PostgreSQL 16 or newer.

## Exercises

### Exercise 1 — All or nothing
A plain `COPY` of 10,000 Comma-Separated Values (CSV) rows fails on row 9,000 because of a bad date. How many rows are in the table afterwards, and why? See Section 7.

### Exercise 2 — Land first, then clean
This CSV text has one bad score:

```python
data = "id,score\n1,10\n2,x\n3,30\n"
```

Create a text-only table `scores_staging(id TEXT, score TEXT)` and a typed table `scores(id INTEGER PRIMARY KEY, score INTEGER)`. Load the text into staging with `COPY`, then move only the rows whose score is whole digits into `scores`. Show the table.

### Exercise 3 — Skip bad rows while loading
Which `COPY` option (available from PostgreSQL 17) skips rows that cannot be converted to the column type instead of cancelling the whole load? Name one kind of problem it will *not* skip.

### Exercise 4 — Put the recipe in order
Put these bulk-load steps in the best order: (a) `ANALYZE`, (b) `COPY` the rows in, (c) create the table, (d) build the indexes.

### Exercise 5 — Count with an upsert
Create `counts(word TEXT PRIMARY KEY, n INTEGER NOT NULL)`. Write one `INSERT` statement that adds a word with `n = 1`, or adds 1 to `n` if the word is already there. Run it for `a`, `b`, `a` and show the table.

### Exercise 6 — Export
Write the Python that uses `COPY` to export `SELECT word, n FROM counts ORDER BY word` as CSV text (with a header line) into a string, then prints it.

### Exercise 7 — What does the runner do?
A migration list has versions 1, 2 and 3. A server's `schema_migrations` table already records versions 1 and 2. Which migrations does the runner apply, and what would be the risk if it did not record versions?

## Answer Key

### Exercise 1
**Answer:** Zero rows.

**Why:** `COPY` is all-or-nothing by default. One failure cancels the whole command, so the table is left as it was before.

### Exercise 2
**Answer:**

```python
conn.execute("DROP TABLE IF EXISTS scores_staging, scores")
conn.execute("CREATE TABLE scores_staging (id TEXT, score TEXT)")
conn.execute("CREATE TABLE scores (id INTEGER PRIMARY KEY, score INTEGER)")
with conn.cursor() as cur:
    with cur.copy("COPY scores_staging FROM STDIN WITH (FORMAT csv, HEADER)") as copy:
        copy.write(data)
conn.execute("INSERT INTO scores SELECT id::int, score::int FROM scores_staging WHERE score ~ '^[0-9]+$'")
conn.commit()
print(conn.execute("SELECT * FROM scores ORDER BY id").fetchall())   # [(1, 10), (3, 30)]
```

**Why:** the text table accepts anything, and the pattern check keeps `x` out of the typed table.

### Exercise 3
**Answer:** `ON_ERROR ignore`, as in `COPY t FROM STDIN WITH (FORMAT csv, HEADER, ON_ERROR ignore)`. It will not skip a row that breaks a unique rule, a `NOT NULL` rule or a foreign key.

**Why:** the option only covers rows whose values cannot be converted to the column type. Rule violations still stop the load.

### Exercise 4
**Answer:** (c), (b), (d), (a): create the table, `COPY` the rows in, build the indexes, then `ANALYZE`.

**Why:** building an index once over finished data is cheaper than updating it for every row during the load, and `ANALYZE` should see the final data.

### Exercise 5
**Answer:**

```python
conn.execute("DROP TABLE IF EXISTS counts")
conn.execute("CREATE TABLE counts (word TEXT PRIMARY KEY, n INTEGER NOT NULL)")
for w in ("a", "b", "a"):
    conn.execute("INSERT INTO counts (word, n) VALUES (%s, 1) ON CONFLICT (word) DO UPDATE SET n = counts.n + 1", (w,))
conn.commit()
print(conn.execute("SELECT * FROM counts ORDER BY word").fetchall())   # [('a', 2), ('b', 1)]
```

**Why:** `ON CONFLICT ... DO UPDATE` runs when the word already exists, and `counts.n` is the old value.

### Exercise 6
**Answer:**

```python
with conn.cursor() as cur:
    with cur.copy("COPY (SELECT word, n FROM counts ORDER BY word) TO STDOUT WITH (FORMAT csv, HEADER)") as copy:
        text = "".join(bytes(chunk).decode() for chunk in copy)
print(text)
```

**Why:** `COPY (query) TO STDOUT` streams the result to Python in chunks, which we join into one string.

### Exercise 7
**Answer:** Only version 3. Without recorded versions the runner could not tell what was already done, so it would run versions 1 and 2 again and fail (for example, "column already exists") or change data twice.

**Why:** the `schema_migrations` table is the runner's memory, which makes running the list repeatedly safe.
