# JSONB, Arrays, Ranges and Generated Columns — Assignment

These exercises use small inline values, so you can run them in a scratch file or in any Structured Query Language (SQL) window connected to your PostgreSQL server. Use PostgreSQL 17 or newer (18 recommended).

## Exercises

### Exercise 1 — Two arrows
In your own words, what is the difference between `->` and `->>` on a JavaScript Object Notation in binary form (JSONB) value, and when would you pick each? See Section 7.

### Exercise 2 — Dig into a document
Given this document, write one query that returns the city as text and the second language as text:

```sql
SELECT '{"name":"Ana","address":{"city":"Oslo"},"langs":["en","no"]}'::jsonb AS doc;
```

### Exercise 3 — Filter by contents
Three people are stored as JSONB values. Write a query that returns only the people whose document contains `{"role":"admin"}`.

```sql
SELECT * FROM (VALUES
  ('{"name":"Ana","role":"admin"}'::jsonb),
  ('{"name":"Ben","role":"user"}'::jsonb),
  ('{"name":"Cy","role":"admin","active":true}'::jsonb)
) AS people(doc);
```

### Exercise 4 — Unpack a list
Use `JSON_TABLE` to turn this order into one row per item with the columns `sku` and `qty`, then add a query that sums the quantities.

```sql
SELECT '{"items":[{"sku":"A","qty":2},{"sku":"B","qty":5}]}'::jsonb AS doc;
```

### Exercise 5 — Arrays: contains or overlaps?
Without running them first, predict the result (`true` or `false`) of each query, then run them to check:

```sql
SELECT ARRAY['red','blue'] && ARRAY['blue','green'];
SELECT ARRAY['red'] @> ARRAY['red','blue'];
SELECT ARRAY['red','blue'] @> ARRAY['blue'];
```

### Exercise 6 — Ranges: do the bookings clash?
A room is booked from 1 June up to but not including 5 June, and another booking runs from 5 June up to but not including 8 June. Write one query that tells you whether the two bookings overlap.

### Exercise 7 — A formula column
Create a table `rect` with whole-number columns `w` and `h`, plus a column `area` that PostgreSQL calculates as `w * h` and saves. Insert one row with `w = 3` and `h = 4`, show it, then try to insert a row that sets `area` yourself. What happens, and which kind of generated column (stored or virtual) can have an index?

### Exercise 8 — Column or JSONB?
A teammate wants to put `price` inside the JSONB `specs` column next to brand and colors, because "it is all product info". Do you agree? Give one reason for and one against.

## Answer Key

### Exercise 1
**Answer:** `->` returns the piece as JSONB and `->>` returns it as plain text.

**Why:** Use `->` while you are still digging into the document (for example `specs -> 'dims' ->> 'h'`), and `->>` on the last step when you want an ordinary value to compare, sort or cast.

### Exercise 2
**Answer:**

```sql
SELECT doc #>> '{address,city}' AS city,
       doc -> 'langs' ->> 1     AS second_language
FROM (SELECT '{"name":"Ana","address":{"city":"Oslo"},"langs":["en","no"]}'::jsonb AS doc) d;
```

The result is `Oslo` and `no`.

**Why:** `#>>` follows a path of keys and returns text. List positions start at 0, so position 1 is the second item.

### Exercise 3
**Answer:**

```sql
SELECT * FROM (VALUES
  ('{"name":"Ana","role":"admin"}'::jsonb),
  ('{"name":"Ben","role":"user"}'::jsonb),
  ('{"name":"Cy","role":"admin","active":true}'::jsonb)
) AS people(doc)
WHERE doc @> '{"role":"admin"}';
```

You get Ana and Cy.

**Why:** `@>` means "contains". Extra keys such as `active` do not matter, because the left side only has to contain everything on the right.

### Exercise 4
**Answer:**

```sql
SELECT sku, qty
FROM JSON_TABLE('{"items":[{"sku":"A","qty":2},{"sku":"B","qty":5}]}'::jsonb, '$.items[*]'
                COLUMNS (sku TEXT PATH '$.sku', qty INTEGER PATH '$.qty'));

SELECT sum(qty) AS total_qty
FROM JSON_TABLE('{"items":[{"sku":"A","qty":2},{"sku":"B","qty":5}]}'::jsonb, '$.items[*]'
                COLUMNS (qty INTEGER PATH '$.qty'));
```

The rows are `A, 2` and `B, 5`, and the total is 7.

**Why:** the path `$.items[*]` creates one row per list item, and `COLUMNS` says which value goes into which column. Once the data is in rows, normal aggregates work.

### Exercise 5
**Answer:** `true`, `false`, `true`.

**Why:** `&&` means "shares at least one item" (`blue` is shared). `@>` means "has all of these": `['red']` does not contain `blue`, but `['red','blue']` does contain `['blue']`.

### Exercise 6
**Answer:**

```sql
SELECT daterange('2026-06-01', '2026-06-05') && daterange('2026-06-05', '2026-06-08') AS clash;
```

The result is `false`.

**Why:** `daterange(a, b)` includes `a` and leaves out `b`, so the first booking ends before 5 June starts and the second begins on it. No day belongs to both.

### Exercise 7
**Answer:**

```sql
CREATE TABLE rect (
    w    INTEGER,
    h    INTEGER,
    area INTEGER GENERATED ALWAYS AS (w * h) STORED
);
INSERT INTO rect (w, h) VALUES (3, 4);
SELECT * FROM rect;                              -- 3 | 4 | 12
INSERT INTO rect (w, h, area) VALUES (2, 2, 99); -- error
```

The last statement fails with "cannot insert a non-DEFAULT value into column "area"". A `STORED` generated column can be indexed; a `VIRTUAL` one cannot.

**Why:** the database owns the value, so it can never disagree with `w` and `h`. Only stored columns exist on disk, which is what an index needs.

### Exercise 8
**Answer:** Mostly no. For: it keeps all product facts in one place, and new kinds of products need no table change. Against: JSONB does not enforce a type or a required value, PostgreSQL keeps fewer statistics about values inside it, and price is something you filter, sort and join on constantly.

**Why:** put the facts every row has and every query uses (price) in normal columns, and keep the varying details (colors, dimensions) in JSONB.
