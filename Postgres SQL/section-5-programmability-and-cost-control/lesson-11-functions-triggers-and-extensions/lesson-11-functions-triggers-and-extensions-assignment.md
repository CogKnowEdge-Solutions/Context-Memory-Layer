# Functions, Triggers and Extensions — Assignment

The code exercises build their own small tables, so run them in a scratch file with a Python connection called `conn` (opened with `psycopg.connect(...)`) or in any Structured Query Language (SQL) window. Use PostgreSQL 18 (14 or newer works for everything here).

## Exercises

### Exercise 1 — Function or procedure?
A team wants to (a) format a price for display in `SELECT`, and (b) copy 50,000 expired orders to an archive table and delete them, committing every 1,000 rows so the transaction log stays manageable. Should each be a function or a procedure, and why?

### Exercise 2 — Mark volatility correctly
You write `CREATE FUNCTION tax(cents int) RETURNS int LANGUAGE sql AS $$ SELECT (cents * 7) / 100; $$`. If this function always returns the same result for the same input and has no side effects, what `VOLATILE` setting would let the planner inline it more aggressively? Write the corrected `CREATE FUNCTION` line for that setting.

### Exercise 3 — Audit with a BEFORE trigger
Write a `BEFORE INSERT` trigger function and trigger on a table called `notes(id serial primary key, body text, author text, created_at timestamptz)`. On every insert, if `author` is `NULL`, set it to `'anonymous'`. Use `NEW`, `TG_OP`, and make sure the trigger still inserts the row.

### Exercise 4 — Log the schema
Write an event trigger function and event trigger that logs every `DROP TABLE` to a table `drop_log(dropped_at timestamptz default now(), command text)`. Show the two `CREATE` statements and say what catalog/variable gives you the command text.

### Exercise 5 — Notify a worker
An application wants to wake a background worker whenever a row is inserted into `orders`. Write the `pg_notify` call inside an `AFTER INSERT` trigger function (show the function body), and write the SQL the worker runs to subscribe and receive one message with a 3-second timeout.

### Exercise 6 — Hash a password safely
Using `pgcrypto`, write the SQL to (a) create the extension if needed, (b) generate a blowfish salt and hash the password `'s3cr3t'`, (c) check whether `'s3cr3t'` matches that stored hash. Name the two functions you use for hashing and the one you use to check.

## Answer Key

### Exercise 1
**Answer:** (a) **Function.** Formatting/calculations belong in a function so they can be used in `SELECT`/`WHERE`/expressions and the planner can treat them normally. (b) **Procedure, called with `CALL`.** Moving and deleting tens of thousands of rows is a multi-step job; a procedure can `COMMIT` in batches (or commit once) and is the right tool for operations that change large amounts of data on a schedule.

**Why:** Functions are expression-oriented; procedures are job-oriented and are allowed to manage transactions.

### Exercise 2
**Answer:**

```sql
CREATE FUNCTION tax(cents int) RETURNS int
LANGUAGE sql IMMUTABLE
AS $$ SELECT (cents * 7) / 100; $$;
```

Use `IMMUTABLE` because the result never changes for the same inputs and there are no side effects. The planner can inline and reuse results more aggressively for immutable functions.

**Why:** Volatility annotations tell the optimizer what it can cache/reorder; mislabeling (`VOLATILE` when `IMMUTABLE` is true) wastes opportunities, while the reverse can be wrong.

### Exercise 3
**Answer:**

```sql
CREATE OR REPLACE FUNCTION set_default_author()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.author IS NULL THEN
        NEW.author := 'anonymous';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER notes_default_author
BEFORE INSERT ON notes
FOR EACH ROW EXECUTE FUNCTION set_default_author();
```

**Why:** In a `BEFORE` row trigger you can modify `NEW` and return it to change what gets inserted. Returning `NULL` would skip the row; returning `NEW` lets the insert proceed.

### Exercise 4
**Answer:**

```sql
CREATE TABLE drop_log(
    dropped_at timestamptz DEFAULT now(),
    command text
);

CREATE OR REPLACE FUNCTION log_drop_table()
RETURNS event_trigger
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO drop_log(command) VALUES (current_query());
END;
$$;

CREATE EVENT TRIGGER log_drop_table
ON ddl_command_end
WHEN TAG IN ('DROP TABLE')
EXECUTE FUNCTION log_drop_table();
```

Use `current_query()` to capture the command text; `TG_TAG` tells you the DDL tag (here filtered to `DROP TABLE`). Event triggers run for DDL events, not per row.

**Why:** `current_query()` returns the statement that fired the event trigger; it's the right way to log exactly what ran.

### Exercise 5
**Answer:**

```sql
CREATE OR REPLACE FUNCTION notify_new_order()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM pg_notify('order_events', TG_OP || ':' || NEW.order_id::text);
    RETURN NEW;
END;
$$;

CREATE TRIGGER orders_notify
AFTER INSERT ON orders
FOR EACH ROW EXECUTE FUNCTION notify_new_order();
```

Worker side:

```sql
LISTEN order_events;
-- in an app, wait for messages; in psql use:
-- (or call PQconsumeInput/receive in a driver)
```

In psycopg: `conn.execute("LISTEN order_events")` and poll `conn.notifies(timeout=3)`. The message comes as the channel and payload string after the transaction that did `NOTIFY` commits.

**Why:** `pg_notify` is fire-and-forget and delivered at commit; `LISTEN` subscribes a session to that channel so it can receive notifications.

### Exercise 6
**Answer:**

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Hash with a blowfish salt
SELECT crypt('s3cr3t', gen_salt('bf')) AS stored_hash;

-- Check a plain password against the stored hash
SELECT crypt('s3cr3t', '$2a$06$...') = '$2a$06$...' AS matches;
```

Use `gen_salt('bf')` to generate the salt, `crypt(plain, salt_or_stored_hash)` to hash/check, and compare the result to the stored hash (`crypt(plain, stored_hash) = stored_hash`). Never store the plain password.

**Why:** `crypt` with a per-password salt from `gen_salt` produces a standard string hash that embeds its algorithm and salt, so verifying with `crypt(plain, stored_hash)` is correct and safe.
