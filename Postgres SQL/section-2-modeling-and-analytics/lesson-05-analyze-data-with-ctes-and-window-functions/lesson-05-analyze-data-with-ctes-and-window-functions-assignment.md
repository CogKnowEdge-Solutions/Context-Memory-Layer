# Analyze Data with CTEs and Window Functions — Assignment

## Exercises

### Exercise 1 — Simple CTE
Write a CTE that computes total amount per salesperson (sum of amount), then select those with total > 1000.

### Exercise 2 — ROW_NUMBER vs RANK
Explain the difference between ROW_NUMBER(), RANK(), and DENSE_RANK() when there are ties in the ordering.

### Exercise 3 — PARTITION BY
Write a query showing salesperson, region, amount, and the region total (using SUM() OVER with PARTITION BY region).

### Exercise 4 — LAG/LEAD
Using sales ordered by sale_date, show sale_id, amount, previous amount (LAG), and next amount (LEAD).

### Exercise 5 — Recursive CTE
Write a recursive CTE that generates numbers from 1 to 3.

### Exercise 6 — Top N per group
Using a CTE + RANK(), find the top 1 sale (highest amount) per region.

## Answer Key

### Exercise 1
```sql
WITH totals AS (
  SELECT salesperson, SUM(amount) AS total
  FROM sales
  GROUP BY salesperson
)
SELECT * FROM totals WHERE total > 1000 ORDER BY total DESC;
```

### Exercise 2
**Answer:** ROW_NUMBER() assigns unique sequential numbers (ties get different numbers arbitrarily). RANK() gives same rank for ties but skips subsequent ranks (gaps). DENSE_RANK() gives same rank for ties with no gaps.

### Exercise 3
```sql
SELECT s.salesperson, r.name AS region, s.amount,
       SUM(s.amount) OVER (PARTITION BY r.name) AS region_total
FROM sales s
JOIN regions r ON r.region_id=s.region_id
ORDER BY r.name, s.amount DESC;
```

### Exercise 4
```sql
SELECT sale_id, amount, sale_date,
       LAG(amount) OVER (ORDER BY sale_date) AS prev_amount,
       LEAD(amount) OVER (ORDER BY sale_date) AS next_amount
FROM sales
ORDER BY sale_date;
```

### Exercise 5
```sql
WITH RECURSIVE nums AS (
  SELECT 1 AS n
  UNION ALL
  SELECT n+1 FROM nums WHERE n < 3
)
SELECT * FROM nums;
```

### Exercise 6
```sql
WITH ranked AS (
  SELECT r.name AS region, s.sale_id, s.salesperson, s.amount,
         RANK() OVER (PARTITION BY r.name ORDER BY s.amount DESC) AS rnk
  FROM sales s JOIN regions r ON r.region_id=s.region_id
)
SELECT region, salesperson, amount FROM ranked WHERE rnk = 1 ORDER BY region;
```
