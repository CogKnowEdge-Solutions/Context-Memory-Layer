# Lab 3 — Sales Analytics Pipeline — Assignment

Test your understanding of aggregation pipelines, indexing, and query analysis by answering the following questions and completing the short code tasks.

---

## Exercises

### Exercise 1 — Concept Question
What is the difference between `$lookup` and embedding documents directly? When would you choose one approach over the other?

### Exercise 2 — Code Task
Write an aggregation pipeline that finds the **total quantity sold per category**. The output should show the category name and total units sold, sorted by total units descending.

### Exercise 3 — Concept Question
What does `$unwind` do in an aggregation pipeline? What happens if the array being unwound is empty?

### Exercise 4 — Code Task
Write a query using `.explain()` to check whether a query on `{"customer": "Alice"}` uses an index or performs a collection scan. Create an appropriate index first, then verify with `.explain()`.

### Exercise 5 — Concept Question
What is a compound index? Why is the order of fields in a compound index important?

### Exercise 6 — Code Task
Write an aggregation pipeline that calculates the **average order value** (quantity × price) for each region. Only include regions where the average order value exceeds $50.

### Exercise 7 — Applied Task
The company wants to know which products have never been ordered. Write a pipeline using `$lookup` and `$match` to find products that have zero matching orders.

---

## Answer Key

### Exercise 1
**Embedding** stores related data inside the same document — fast to read (single query) but can lead to duplication and large documents. **Referencing** (via `$lookup`) stores related data in separate collections and joins at query time — avoids duplication but requires an extra query stage. Choose embedding when data is accessed together and grows predictably (e.g., comments on a post). Choose referencing when data is shared across collections or grows unboundedly (e.g., products referenced by many orders).

### Exercise 2
```python
pipeline = [
    {"$lookup": {"from": "products", "localField": "product_id", "foreignField": "product_id", "as": "product"}},
    {"$unwind": "$product"},
    {"$group": {"_id": "$product.category", "total_units": {"$sum": "$quantity"}}},
    {"$sort": {"total_units": -1}}
]
results = orders.aggregate(pipeline)
for doc in results:
    print(f"{doc['_id']}: {doc['total_units']} units")
```

### Exercise 3
`$unwind` takes an array field and creates one output document per array element, copying all other fields into each. If the array is empty, the document is **dropped** by default (use `preserveNullAndEmptyArrays: true` to keep it).

### Exercise 4
```python
# Create the index first
orders.create_index("customer")

# Then explain the query
result = orders.find({"customer": "Alice"}).explain()
print(result["queryPlanner"]["winningPlan"]["stage"])
# Should print "IXSCAN" if the index is used
```

### Exercise 5
A **compound index** covers two or more fields (e.g., `{"region": 1, "date": 1}`). The field order matters because MongoDB can use the index for queries that filter/sort on a **prefix** of the indexed fields. An index on `(region, date)` supports queries filtering by `region` alone or by `region + date`, but NOT by `date` alone.

### Exercise 6
```python
pipeline = [
    {"$lookup": {"from": "products", "localField": "product_id", "foreignField": "product_id", "as": "product"}},
    {"$unwind": "$product"},
    {"$addFields": {"order_value": {"$multiply": ["$quantity", "$product.price"]}}},
    {"$group": {"_id": "$region", "avg_value": {"$avg": "$order_value"}}},
    {"$match": {"avg_value": {"$gt": 50}}},
    {"$sort": {"avg_value": -1}}
]
results = orders.aggregate(pipeline)
for doc in results:
    print(f"{doc['_id']}: ${doc['avg_value']:.2f}")
```

### Exercise 7
```python
pipeline = [
    {"$lookup": {
        "from": "orders",
        "localField": "product_id",
        "foreignField": "product_id",
        "as": "order_docs"
    }},
    {"$match": {"order_docs": {"$size": 0}}},
    {"$project": {"_id": 0, "product_id": 1, "name": 1}}
]
results = products.aggregate(pipeline)
for doc in results:
    print(f"Never ordered: {doc['name']} ({doc['product_id']})")
```
When `$lookup` finds no matching orders, the `order_docs` array is empty. Filtering with `{"$size": 0}` keeps only products with zero orders.
