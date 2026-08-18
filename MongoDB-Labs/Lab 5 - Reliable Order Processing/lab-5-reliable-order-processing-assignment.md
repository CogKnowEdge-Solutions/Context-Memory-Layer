# Lab 5 — Reliable Order Processing System — Assignment

Test your understanding of atomic operations, change streams, and backup/restore by answering the following questions and completing the short code tasks.

---

## Exercises

### Exercise 1 — Concept Question
What are the four ACID properties? Explain each in one sentence and give an example of why each matters in an order processing system.

### Exercise 2 — Code Task
Write a function `place_order_safe(customer_id, product_id, qty)` that uses `find_one_and_update` to atomically decrement inventory and create an order. If stock is insufficient, return `None, "Insufficient stock"`. If the product doesn't exist, return `None, "Product not found"`.

### Exercise 3 — Concept Question
Why is `find_one_and_update` safer than doing a separate `find_one` followed by `update_one` for order placement? Describe the race condition that the separate approach allows.

### Exercise 4 — Code Task
Write a query that finds all orders placed by customer `alice` and joins with the `inventory` collection using `$lookup` to show the product name and total spent per order. Sort by date descending.

### Exercise 5 — Concept Question
What is a change stream, and what problem does it solve compared to polling the database periodically? Name two use cases where change streams are preferred over polling.

### Exercise 6 — Code Task
Write a function `cancel_order_safe(order_id)` that atomically restores inventory stock using `$inc` and deletes the order document. Handle the case where the order doesn't exist.

### Exercise 7 — Concept Question
Why does the backup/restore step use `drop()` before `insert_many()` instead of just inserting the backup data directly? What would happen if you skipped the `drop()` call?

### Exercise 8 — Applied Task
The platform wants to detect potential overselling. Write a query that finds any inventory items where `quantity` is negative. If the atomic guard is working correctly, this query should return zero results. Explain why.

### Exercise 9 — Code Task
Write an aggregation pipeline that computes the **average order value per customer**. Join orders with customers using `$lookup`, group by customer name, and compute the average `total` field. Sort by average descending.

---

## Answer Key

### Exercise 1
1. **Atomicity** — every operation completes fully or not at all. In order processing, this means inventory is decremented if and only if the order record is created; no partial states.
2. **Consistency** — the database always moves from one valid state to another. Stock quantities must never go negative, and every order must reference a valid product.
3. **Isolation** — concurrent operations don't interfere. Two customers buying the last unit simultaneously must not both succeed; one must be rejected.
4. **Durability** — once an order is confirmed, it survives crashes. The order and stock change are persisted and recoverable after a restart.

### Exercise 2
```python
from datetime import datetime

def place_order_safe(customer_id, product_id, qty):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    order_id = f"ORD-SAFE-{orders.count_documents({}) + 1}"

    updated = inventory.find_one_and_update(
        {"product_id": product_id, "quantity": {"$gte": qty}},
        {"$inc": {"quantity": -qty}},
    )

    if updated is None:
        item = inventory.find_one({"product_id": product_id}, {"_id": 0})
        if item and item["quantity"] < qty:
            return None, "Insufficient stock"
        return None, "Product not found"

    total = updated["price"] * qty
    orders.insert_one({
        "order_id": order_id, "customer_id": customer_id,
        "product_id": product_id, "quantity": qty,
        "total": total, "date": now, "status": "completed",
    })
    return order_id, f"${total:.2f}"
```

### Exercise 3
With separate `find_one` + `update_one`, another process could modify the inventory between the find and the update. For example:
1. Process A reads stock = 1 (via `find_one`)
2. Process B reads stock = 1 (via `find_one`)
3. Process A decrements to 0 (via `update_one`)
4. Process B decrements to -1 (via `update_one`)

Both processes saw sufficient stock, but the result is a negative quantity (overselling). `find_one_and_update` is atomic — the filter check and the decrement happen as a single indivisible operation, so no other process can interleave between them.

### Exercise 4
```python
pipeline = [
    {"$match": {"customer_id": "alice"}},
    {"$lookup": {
        "from": "inventory",
        "localField": "product_id",
        "foreignField": "product_id",
        "as": "product"
    }},
    {"$unwind": "$product"},
    {"$project": {"_id": 0, "order_id": 1, "product_name": "$product.name",
                  "total": 1, "date": 1}},
    {"$sort": {"date": -1}}
]
results = orders.aggregate(pipeline)
for doc in results:
    print(f"{doc['order_id']} | {doc['product_name']} | ${doc['total']} | {doc['date']}")
```

### Exercise 5
A **change stream** is a real-time feed of database changes (inserts, updates, deletes) that applications can subscribe to. Unlike polling, which repeatedly queries the database to check for new data (wasting resources and introducing latency), change streams push events to the listener as they happen.

Two use cases:
1. **Order notifications** — an admin dashboard that lights up instantly when a new order arrives, without polling every 5 seconds.
2. **Inventory alerts** — triggering a restock notification when a product's quantity drops below a threshold, detected via an update event.

### Exercise 6
```python
def cancel_order_safe(order_id):
    order = orders.find_one({"order_id": order_id})
    if not order:
        return False, "Order not found"

    inventory.update_one(
        {"product_id": order["product_id"]},
        {"$inc": {"quantity": order["quantity"]}}
    )
    orders.delete_one({"order_id": order_id})
    return True, f"Restored {order['quantity']} unit(s)"
```

### Exercise 7
`drop()` removes all existing documents from the collection before re-inserting the backup data. If you skipped `drop()`, the `insert_many()` would **add** the backup documents alongside the existing ones, resulting in duplicates. The collection would contain both the current data and the restored data, effectively doubling every record.

### Exercise 8
```python
negative_stock = list(inventory.find({"quantity": {"$lt": 0}}))
print(f"Items with negative stock: {len(negative_stock)}")
```
This should return zero results because the atomic guard `{"$gte": qty}` in `find_one_and_update` prevents the decrement from executing when stock is insufficient. If stock is 5 and the order is for 10, the filter fails and nothing changes — the quantity never goes negative. This is the entire purpose of the atomic guard pattern.

### Exercise 9
```python
pipeline = [
    {"$lookup": {
        "from": "customers",
        "localField": "customer_id",
        "foreignField": "customer_id",
        "as": "customer"
    }},
    {"$unwind": "$customer"},
    {"$group": {
        "_id": "$customer.name",
        "avg_total": {"$avg": "$total"},
        "order_count": {"$sum": 1}
    }},
    {"$sort": {"avg_total": -1}},
    {"$project": {"_id": 0, "customer": "$_id",
                  "avg_total": {"$round": ["$avg_total", 2]}, "order_count": 1}}
]
results = orders.aggregate(pipeline)
for doc in results:
    print(f"{doc['customer']:<18} | avg ${doc['avg_total']} | {doc['order_count']} orders")
```
