# Summarize Data with Aggregates and Subqueries — Assignment

## Exercises

### Exercise 1 — Aggregates
Write a query to find the total quantity sold and average quantity per order item across all order_items.

### Exercise 2 — GROUP BY with HAVING
Find regions where total items sold > 5, showing region and total items.

### Exercise 3 — FILTER
Using products, show count of products total and count of products with price > 100 per category, using `FILTER`.

### Exercise 4 — Subquery
Find products whose price is above the average price of all products, showing name and price.

### Exercise 5 — EXISTS
Find customers who have placed at least one order on or after '2025-10-12' using `EXISTS`.

### Exercise 6 — Rollups
Explain what `GROUPING SETS ((region), (category), ())` produces compared to a single `GROUP BY region, category`.

## Answer Key

### Exercise 1
```sql
SELECT COUNT(*) AS order_items, SUM(quantity) AS total_items, AVG(quantity) AS avg_qty
FROM order_items;
```
**Why:** Aggregates collapse all rows into summary values.

### Exercise 2
```sql
SELECT c.region, SUM(oi.quantity) AS total_items
FROM customers c
JOIN orders o ON o.customer_id=c.customer_id
JOIN order_items oi ON oi.order_id=o.order_id
GROUP BY c.region
HAVING SUM(oi.quantity) > 5
ORDER BY c.region;
```
**Why:** `HAVING` filters groups after aggregation.

### Exercise 3
```sql
SELECT category,
       COUNT(*) AS products,
       COUNT(*) FILTER (WHERE price > 100) AS pricey
FROM products
GROUP BY category;
```
**Why:** `FILTER` applies condition per aggregate.

### Exercise 4
```sql
SELECT name, price
FROM products
WHERE price > (SELECT AVG(price) FROM products)
ORDER BY price DESC;
```
**Why:** Scalar subquery returns average for comparison.

### Exercise 5
```sql
SELECT c.customer_id, c.name
FROM customers c
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id=c.customer_id AND o.order_date >= '2025-10-12')
ORDER BY c.customer_id;
```
**Why:** `EXISTS` checks for related rows.

### Exercise 6
**Answer:** `GROUPING SETS ((region), (category), ())` produces three result sets combined: subtotals by region, subtotals by category, and a grand total. A single `GROUP BY region, category` produces only combinations of (region,category).
**Why:** GROUPING SETS gives multiple grouping levels in one query without UNIONs.
