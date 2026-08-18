# Lab 4 — Multi-Tenant Blog Backend — Assignment

Test your understanding of schema design patterns, `$lookup`, and keyword search by answering the following questions and completing the short code tasks.

---

## Exercises

### Exercise 1 — Concept Question
A social media app stores user profiles and their posts. Posts have a fixed set of 3–5 hashtags. Should hashtags be embedded inside each post document or stored in a separate collection? Justify your choice.

### Exercise 2 — Code Task
Write an aggregation pipeline that finds all **comments for post P001** by joining the `comments` collection with the `posts` collection. The output should show the post title and each comment's author and text.

### Exercise 3 — Concept Question
What is the difference between `$lookup` and embedding documents directly? When would you choose `$lookup` over embedding?

### Exercise 4 — Code Task
Write a query using regex to find all posts where the `body` field contains the word "data" (case-insensitive). Print each matching post's title and tags.

### Exercise 5 — Concept Question
Why are comments typically referenced (in a separate collection) rather than embedded inside each post document? Name two reasons.

### Exercise 6 — Code Task
Write an aggregation pipeline that counts the **total number of tags used across all posts** by unwinding the `tags` array and grouping by tag name. Sort by count descending.

### Exercise 7 — Applied Task
The platform wants to find tenants who have **never had a comment** on any of their posts. Write a pipeline using `$lookup` and `$match` to identify such tenants.

---

## Answer Key

### Exercise 1
**Embed** the hashtags inside each post document. Hashtags are small (a few short strings), always fetched together with the post, and grow predictably (3–5 per post). Embedding means a single query retrieves both the post content and its hashtags — no join needed. A separate collection would be overkill and would require a `$lookup` just to display hashtags.

### Exercise 2
```python
pipeline = [
    {"$lookup": {
        "from": "posts",
        "localField": "post_id",
        "foreignField": "post_id",
        "as": "post"
    }},
    {"$unwind": "$post"},
    {"$match": {"post.post_id": "P001"}},
    {"$project": {"_id": 0, "post_title": "$post.title", "author": 1, "text": 1}}
]
results = comments.aggregate(pipeline)
for doc in results:
    print(f"{doc['post_title']} — {doc['author']}: {doc['text']}")
```

### Exercise 3
`$lookup` joins data across collections at query time — keeps documents small and avoids duplication but requires an extra pipeline stage. Embedding stores related data inside the same document — fast to read (single query) but can lead to large documents and data duplication. Choose `$lookup` when data is shared across many documents or grows unboundedly (e.g., comments on posts). Choose embedding when data is always accessed together and grows predictably (e.g., tags on a post).

### Exercise 4
```python
import re

pattern = re.compile("data", re.IGNORECASE)
matching = list(posts.find({
    "$or": [
        {"title": {"$regex": pattern}},
        {"body": {"$regex": pattern}}
    ]
}, {"_id": 0, "title": 1, "tags": 1}))

for doc in matching:
    print(f"{doc['title']} | Tags: {doc['tags']}")
```

### Exercise 5
1. **Unbounded growth** — a post can accumulate thousands of comments over time, making the document too large to store or retrieve efficiently.
2. **Independent lifecycle** — comments need their own queries (e.g., "show me all comments by Eve") and updates (e.g., edit a comment), which are harder when they are embedded inside a post document.

### Exercise 6
```python
pipeline = [
    {"$unwind": "$tags"},
    {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}}
]
results = posts.aggregate(pipeline)
for doc in results:
    print(f"{doc['_id']}: {doc['count']}")
```

### Exercise 7
```python
pipeline = [
    {"$lookup": {
        "from": "posts",
        "localField": "tenant_id",
        "foreignField": "tenant_id",
        "as": "tenant_posts"
    }},
    {"$unwind": "$tenant_posts"},
    {"$lookup": {
        "from": "comments",
        "localField": "tenant_posts.post_id",
        "foreignField": "post_id",
        "as": "post_comments"
    }},
    {"$group": {
        "_id": "$blog_title",
        "has_comments": {"$max": {"$gt": [{"$size": "$post_comments"}, 0]}}
    }},
    {"$match": {"has_comments": False}},
    {"$project": {"_id": 1}}
]
results = tenants.aggregate(pipeline)
for doc in results:
    print(f"Tenant with no comments: {doc['_id']}")
```
This pipeline joins tenants to their posts, then joins each post to its comments. The `$group` with `$max` checks if any post in the tenant has comments. `$match` with `False` keeps only tenants where no post received any comments.
