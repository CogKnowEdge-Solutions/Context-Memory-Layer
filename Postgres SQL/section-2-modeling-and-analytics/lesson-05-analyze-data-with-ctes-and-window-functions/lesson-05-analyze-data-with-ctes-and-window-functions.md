# Analyze Data with CTEs and Window Functions
## 1. What are CTEs and Window Functions?

Common Table Expressions (CTEs) break complex queries into named, readable steps. Window functions perform calculations across a related set of rows without collapsing them into one group row.

- **CTEs:** WITH, recursive CTEs
- **Window basics:** OVER(), PARTITION BY, ORDER BY
- **Ranking:** ROW_NUMBER, RANK, DENSE_RANK
- **Offsets:** LAG, LEAD
- **Aggregates as windows:** SUM/AVG over windows
- **Frames:** ROWS/RANGE
- **Others:** FIRST_VALUE/LAST_VALUE/NTILE

**Everyday example:** Find the top salesperson per store without losing individual sale rows — window functions do this elegantly.

```mermaid
graph LR
  Q[Query] --> C[CTEs build steps]
  C --> W[Window functions compute over sets]
  W --> R[Results keep row detail]
  style Q fill:#e1f5ff,stroke:#0288d1,color:#01579b
  style C fill:#fff9c4,stroke:#f9a825,color:#7f6000
  style W fill:#ffe0b2,stroke:#ef6c00,color:#7f3f00
  style R fill:#c8e6c9,stroke:#2e7d32,color:#1b5e20
```

## 2. Problem Statement / Use Case Overview

You need to analyze sales: compute totals with CTEs, rank salespeople per region, get previous/next sale amounts, running totals, and find top performers. You also see recursive CTEs.

In this lesson you use CTEs and window functions on a small sales dataset.

## 3. Input

Tables: regions(region_id,name), sales(sale_id,region_id,salesperson,amount,sale_date) with sample rows.

## 4. Processing

```mermaid
flowchart LR
  A[Load data] --> B[CTEs basics + recursive]
  B --> C[Ranking windows]
  C --> D[PARTITION BY & aggregates]
  D --> E[LAG/LEAD & frames]
  E --> F[Other window funcs]
  F --> G[CTE + window showcase]
  style A fill:#e1f5ff,stroke:#0288d1,color:#01579b
  style G fill:#c8e6c9,stroke:#2e7d32,color:#1b5e20
```

## 5. Output

Top 2 performers per region (from CTE + window):

```\nregion | salesperson |  amount | rnk
-------+-------------+---------+----
North  | Alice       | 1500.00 |   1
North  | Alice       | 1000.00 |   2
South  | Carol       | 1200.00 |   1
South  | Carol       |  900.00 |   2
West   | Dave        | 2000.00 |   1
(5 rows)\n```

## 6. Tech Stack

| Tool | Version | Role |
|------|---------|------|
| PostgreSQL | 18 | Database |
| psycopg | 3.3.6 | Python driver |
| python-dotenv | 1.2.4 | Loads `.env` |
| Jupyter | any recent version | Runs the notebook |

**Compute and cost:** Laptop CPU, minimal memory, free.

## 7. Underlying Concepts

**CTEs (WITH).** Named subqueries improve readability and can be referenced multiple times. Recursive CTEs iterate. *Everyday example:* break a multi-step report into named steps.

**Window functions.** Compute over a window of rows without grouping collapse. OVER() defines window; PARTITION BY splits; ORDER BY orders within window. *Everyday example:* rank employees within department while showing each employee row.

**Ranking.** ROW_NUMBER gives unique numbers; RANK gives gaps on ties; DENSE_RANK gives no gaps. *Everyday example:* podium positions.

**Offsets and frames.** LAG/LEAD access previous/next; frames (ROWS/RANGE) control window bounds. *Everyday example:* month-over-month change.

**Practical use.** CTEs + windows solve "top N per group" cleanly. *Everyday example:* best seller per category.

## 8. Prerequisites

- Joins and aggregates from lessons 1–4.
- Running PostgreSQL 18 and `.env` at course root.

## 9. Environment / Dependencies Setup

Load `.env` via `load_dotenv("../../.env")` from inside lesson folder. Install:
```
pip install "psycopg[binary]==3.3.6" "python-dotenv==1.2.4"
```

## 10. Step-wise Development Instructions

### Setup

```python
!pip install "psycopg[binary]==3.3.6" "python-dotenv==1.2.4"
```

Installs pinned packages.

```python
# Imports
import os
from decimal import Decimal
import psycopg
from psycopg import sql
from dotenv import load_dotenv
```

Imports and helpers setup.

```python
# Load env
load_dotenv("../../.env")
PGHOST=os.getenv("PGHOST","localhost"); PGPORT=os.getenv("PGPORT","5432")
PGUSER=os.getenv("PGUSER","postgres"); PGPASSWORD=os.getenv("PGPASSWORD") or None
PGDATABASE=os.getenv("PGDATABASE","university"); PGSSLMODE=os.getenv("PGSSLMODE","prefer")
```

Loads env.

```python
# Ensure DB
conn_args=dict(host=PGHOST,port=PGPORT,user=PGUSER,password=PGPASSWORD,sslmode=PGSSLMODE)
with psycopg.connect(dbname="postgres",autocommit=True,**conn_args) as admin:
    if not admin.execute("SELECT 1 FROM pg_database WHERE datname=%s",(PGDATABASE,)).fetchone():
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(PGDATABASE)))
```

Ensures DB exists.

```python
# Connect
conn=psycopg.connect(dbname=PGDATABASE,**conn_args)
print("connected")
```

Connects.

**Output:**

```
connected
```

```python
# show helper
def show(q,params=None):
    with conn.cursor() as cur:
        cur.execute(q,params)
        if cur.description is None:
            print(cur.statusmessage); return
        cols=[d.name for d in cur.description]; rows=cur.fetchall()
    fmt=lambda v:"NULL" if v is None else str(v)
    cells=[[fmt(v) for v in r] for r in rows]
    numeric=[bool(rows) and all(isinstance(v,(int,float,Decimal)) and not isinstance(v,bool) for v in col) for col in zip(*rows)] or [False]*len(cols)
    widths=[max([len(c)]+[len(r[i]) for r in cells]) for i,c in enumerate(cols)]
    print(" | ".join(c.center(w) for c,w in zip(cols,widths)))
    print("-+-".join("-"*w for w in widths))
    for r in cells:
        print(" | ".join((v.rjust(w) if numeric[i] else v.ljust(w)) for i,(v,w) in enumerate(zip(r,widths))))
    print(f"({len(rows)} rows)")
```

Helper for output.

### Step 1 — Load data

```python
# Step 1: Load data
conn.execute("DROP TABLE IF EXISTS sales")
conn.execute("DROP TABLE IF EXISTS regions")
conn.execute("""CREATE TABLE regions(region_id INTEGER PRIMARY KEY, name TEXT NOT NULL)""")
conn.execute("""CREATE TABLE sales(sale_id INTEGER PRIMARY KEY, region_id INTEGER REFERENCES regions(region_id), salesperson TEXT NOT NULL, amount NUMERIC(10,2) NOT NULL, sale_date DATE NOT NULL)""")
conn.execute("INSERT INTO regions VALUES (1,'North'),(2,'South'),(3,'West')")
conn.execute("INSERT INTO sales VALUES (1,1,'Alice',1000,'2025-10-01'),(2,1,'Alice',1500,'2025-10-05'),(3,1,'Bob',800,'2025-10-03'),(4,2,'Carol',1200,'2025-10-02'),(5,2,'Carol',900,'2025-10-10'),(6,3,'Dave',2000,'2025-10-04')")
conn.commit()
show("SELECT * FROM sales ORDER BY sale_id")
```

Creates sales data for CTEs and window functions.

**Output:**

```
sale_id | region_id | salesperson |  amount | sale_date 
--------+-----------+-------------+---------+-----------
      1 |         1 | Alice       | 1000.00 | 2025-10-01
      2 |         1 | Alice       | 1500.00 | 2025-10-05
      3 |         1 | Bob         |  800.00 | 2025-10-03
      4 |         2 | Carol       | 1200.00 | 2025-10-02
      5 |         2 | Carol       |  900.00 | 2025-10-10
      6 |         3 | Dave        | 2000.00 | 2025-10-04
(6 rows)
```

### Step 2 — Simple CTE (WITH)

```python
# Step 2: Simple CTE
show("""
  WITH totals AS (
    SELECT salesperson, SUM(amount) AS total
    FROM sales
    GROUP BY salesperson
  )
  SELECT * FROM totals ORDER BY total DESC
""")
```

Common Table Expressions (CTEs) make complex queries readable.

**Output:**

```
salesperson |  total 
------------+--------
Alice       | 2500.00
Carol       | 2100.00
Dave        | 2000.00
Bob         |  800.00
(4 rows)
```

### Step 3 — Recursive CTE

```python
# Step 3: Recursive CTE
show("""
  WITH RECURSIVE nums AS (
    SELECT 1 AS n
    UNION ALL
    SELECT n+1 FROM nums WHERE n < 5
  )
  SELECT * FROM nums
""")
```

Recursive CTEs traverse hierarchies or generate series of rows.

**Output:**

```
n
-
1
2
3
4
5
(5 rows)
```

### Step 4 — Window functions: ranking

```python
# Step 4: Window functions - ROW_NUMBER, RANK, DENSE_RANK
show("""
  SELECT salesperson, amount, sale_date,
         ROW_NUMBER() OVER (ORDER BY amount DESC) AS rn,
         RANK() OVER (ORDER BY amount DESC) AS rnk,
         DENSE_RANK() OVER (ORDER BY amount DESC) AS drnk
  FROM sales
  ORDER BY amount DESC
""")
```

Window functions compute values across a set of rows related to current row (no collapse).

**Output:**

```
salesperson |  amount | sale_date  | rn | rnk | drnk
------------+---------+------------+----+-----+-----
Dave        | 2000.00 | 2025-10-04 |  1 |   1 |    1
Alice       | 1500.00 | 2025-10-05 |  2 |   2 |    2
Carol       | 1200.00 | 2025-10-02 |  3 |   3 |    3
Alice       | 1000.00 | 2025-10-01 |  4 |   4 |    4
Carol       |  900.00 | 2025-10-10 |  5 |   5 |    5
Bob         |  800.00 | 2025-10-03 |  6 |   6 |    6
(6 rows)
```

### Step 5 — PARTITION BY and running totals

```python
# Step 5: PARTITION BY
show("""
  SELECT r.name AS region, s.salesperson, s.amount,
         SUM(s.amount) OVER (PARTITION BY r.name) AS region_total,
         ROUND(s.amount * 100.0 / SUM(s.amount) OVER (PARTITION BY r.name),1) AS pct
  FROM sales s
  JOIN regions r ON r.region_id=s.region_id
  ORDER BY r.name, s.amount DESC
""")
```

PARTITION BY creates windows per group.

**Output:**

```
region | salesperson |  amount | region_total |  pct 
-------+-------------+---------+--------------+------
North  | Alice       | 1500.00 |      3300.00 |  45.5
North  | Alice       | 1000.00 |      3300.00 |  30.3
North  | Bob         |  800.00 |      3300.00 |  24.2
South  | Carol       | 1200.00 |      2100.00 |  57.1
South  | Carol       |  900.00 |      2100.00 |  42.9
West   | Dave        | 2000.00 |      2000.00 | 100.0
(6 rows)
```

### Step 6 — LAG/LEAD and window frames

```python
# Step 6: ROWS/RANGE frames and LAG/LEAD
show("""
  SELECT salesperson, amount, sale_date,
         LAG(amount) OVER (ORDER BY sale_date) AS prev_amount,
         LEAD(amount) OVER (ORDER BY sale_date) AS next_amount
  FROM sales
  ORDER BY sale_date
""")
show("""
  SELECT sale_date, amount,
         SUM(amount) OVER (ORDER BY sale_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_sum
  FROM sales
  ORDER BY sale_date
""")
```

LAG/LEAD look at previous/next rows; window frames define which rows are included.

**Output:**

```
salesperson |  amount | sale_date  | prev_amount | next_amount
------------+---------+------------+-------------+------------
Alice       | 1000.00 | 2025-10-01 | NULL        | 1200.00    
Carol       | 1200.00 | 2025-10-02 | 1000.00     | 800.00     
Bob         |  800.00 | 2025-10-03 | 1200.00     | 2000.00    
Dave        | 2000.00 | 2025-10-04 | 800.00      | 1500.00    
Alice       | 1500.00 | 2025-10-05 | 2000.00     | 900.00     
Carol       |  900.00 | 2025-10-10 | 1500.00     | NULL       
(6 rows)
sale_date  |  amount | running_sum
-----------+---------+------------
2025-10-01 | 1000.00 |     1000.00
2025-10-02 | 1200.00 |     2200.00
2025-10-03 |  800.00 |     3000.00
2025-10-04 | 2000.00 |     5000.00
2025-10-05 | 1500.00 |     6500.00
2025-10-10 |  900.00 |     7400.00
(6 rows)
```

### Step 7 — FIRST_VALUE and NTILE

```python
# Step 7: FIRST_VALUE/LAST_VALUE/NTILE
show("""
  SELECT salesperson, amount,
         FIRST_VALUE(amount) OVER (ORDER BY amount DESC) AS top_amount,
         NTILE(2) OVER (ORDER BY amount DESC) AS half
  FROM sales
  ORDER BY amount DESC
""")
```

More window functions for comparative analysis.

**Output:**

```
salesperson |  amount | top_amount | half
------------+---------+------------+-----
Dave        | 2000.00 |    2000.00 |    1
Alice       | 1500.00 |    2000.00 |    1
Carol       | 1200.00 |    2000.00 |    1
Alice       | 1000.00 |    2000.00 |    2
Carol       |  900.00 |    2000.00 |    2
Bob         |  800.00 |    2000.00 |    2
(6 rows)
```

### Step 8 — Showcase: top 2 per region

```python
# Step 8: Showcase
show("""
  WITH ranked AS (
    SELECT r.name AS region, s.salesperson, s.amount,
           RANK() OVER (PARTITION BY r.name ORDER BY s.amount DESC) AS rnk
    FROM sales s JOIN regions r ON r.region_id=s.region_id
  )
  SELECT * FROM ranked WHERE rnk <= 2 ORDER BY region, rnk
""")
```

Combine CTEs and window functions to find top performers per region.

**Output:**

```
region | salesperson |  amount | rnk
-------+-------------+---------+----
North  | Alice       | 1500.00 |   1
North  | Alice       | 1000.00 |   2
South  | Carol       | 1200.00 |   1
South  | Carol       |  900.00 |   2
West   | Dave        | 2000.00 |   1
(5 rows)
```

### Cleanup — Close the connection

```python
# Cleanup
conn.close()
print("connection closed")
```

Closes connection.

**Output:**

```
connection closed
```

## 11. What We Learnt

- **CTEs:** Readable multi-step queries; recursive CTEs for iteration.
- **Windows:** Compute across related rows without collapsing.
- **Ranking:** ROW_NUMBER/RANK/DENSE_RANK for ordering.
- **Analytics:** LAG/LEAD, running sums, partitions, frames.
- **Pragmatic:** CTE + window finds top N per group elegantly.
