# MongoDB Intermediate: How to Search by Keywords and by Meaning

## Atlas Search and Vector Search — Assignment

Test your understanding of keyword search, embeddings, vector search and hybrid ranking. Exercises 2, 4 and 6 are code tasks (they assume the `catalog` collection and index names from the lab). Exercise 5 can be answered without a cluster.

---

## Exercises

### Exercise 1 — Concept Question
Explain the difference between how `$search` and `$vectorSearch` decide that a document is relevant. Give one query type where each is stronger.

### Exercise 2 — Code Task
Write a `$search` pipeline that finds courses matching the words `"cloud containers"` in `title` or `description`, tolerates one typo, and returns the top 3 with title and score.

### Exercise 3 — Concept Question
In a `compound` query, what is the difference between a `must` clause and a `filter` clause? When would you choose `filter`?

### Exercise 4 — Code Task
Write the `SearchIndexModel` definition for a vector index on a field called `embedding` with 384 dimensions, cosine similarity, and a filter field `topic`. Then write a `$vectorSearch` stage that returns the best 5 matches among documents whose `topic` is `"ai"`.

### Exercise 5 — Applied Task
Reciprocal Rank Fusion with `k = 60` is applied to two lists. List A (keyword): `["C", "A", "D"]`. List B (vector): `["A", "B", "C"]`. Compute the fused score of each course to 4 decimal places and give the final ranking.

### Exercise 6 — Code Task
Write the Python function `rrf_fuse(rankings, k=60)` that takes a list of ranked id lists and returns `(id, score)` pairs sorted by score descending.

### Exercise 7 — Concept Question
A teammate embeds the documents with one model and embeds user questions with a different model "because it is faster". Explain why this breaks vector search. Also state what happens if `numDimensions` in the index does not match the vectors.

### Exercise 8 — Concept Question
A search for `"SKU-48213"` (a product code) should return exactly one product, and a search for "something to keep my feet dry in a storm" should return rain boots. Which search type would you rely on for each, and why does one system often use both?

---

## Answer Key

### Exercise 1
`$search` (Atlas Search, Lucene) relevance comes from **matching analyzed words**: documents containing the query terms rank higher, with rarer terms and denser matches scoring more. It is stronger for exact names, codes, rare terms and typo-tolerant lookups. `$vectorSearch` relevance comes from **distance between embeddings**: documents whose meaning is close to the question's meaning rank higher even with no shared words. It is stronger for paraphrased, conversational or concept-level questions.

### Exercise 2
```python
pipeline = [
    {"$search": {
        "index": "course_text_index",
        "text": {
            "query": "cloud containers",
            "path": ["title", "description"],
            "fuzzy": {"maxEdits": 1},
        },
    }},
    {"$limit": 3},
    {"$project": {"_id": 0, "title": 1, "score": {"$meta": "searchScore"}}},
]
results = list(catalog.aggregate(pipeline))
```
`$search` must be the first stage. `fuzzy.maxEdits: 1` allows one character change per word. The `$meta: "searchScore"` expression exposes the relevance score.

### Exercise 3
A `must` clause is **required and contributes to the relevance score**. A `filter` clause is **required but does not affect the score**. Use `filter` for hard constraints that should include or exclude results without changing their ranking: a level, category, date range, availability or tenant id. (`should` clauses are optional and boost the score when they match.)

### Exercise 4
```python
vector_model = SearchIndexModel(
    definition={
        "fields": [
            {"type": "vector", "path": "embedding", "numDimensions": 384, "similarity": "cosine"},
            {"type": "filter", "path": "topic"},
        ]
    },
    name="topic_vector_index",
    type="vectorSearch",
)
catalog.create_search_index(model=vector_model)

stage = {"$vectorSearch": {
    "index": "topic_vector_index",
    "path": "embedding",
    "queryVector": query_vector,
    "numCandidates": 100,
    "limit": 5,
    "filter": {"topic": "ai"},
}}
```
The `topic` field must be declared as a `filter` field in the index for the `filter` option to work.

### Exercise 5
Scores with `k = 60`:

- A: rank 2 in list A and rank 1 in list B: 1/62 + 1/61 = 0.016129 + 0.016393 = **0.0325**
- C: rank 1 in list A and rank 3 in list B: 1/61 + 1/63 = 0.016393 + 0.015873 = **0.0323**
- B: rank 2 in list B only: 1/62 = **0.0161**
- D: rank 3 in list A only: 1/63 = **0.0159**

Final ranking: **A, C, B, D**. Courses appearing in both lists (A and C) outrank those appearing in only one.

### Exercise 6
```python
def rrf_fuse(rankings, k=60):
    scores = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
```
`enumerate(..., start=1)` makes the first item rank 1. Every list adds its own `1/(k + rank)` term, so items found by several lists accumulate higher scores.

### Exercise 7
Each embedding model defines its own vector space: the same sentence produces different numbers, and even the vector sizes may differ. Distances between vectors from different models are therefore meaningless, so nearest-neighbour results would be essentially random. Questions and documents must be embedded by the same model (and same version). If `numDimensions` in the index does not match the stored vectors, indexing or querying fails (documents with the wrong length are not indexed, and a query vector of the wrong length is rejected).

### Exercise 8
The product code `"SKU-48213"` needs **keyword search**: it is an exact, rare string, and an embedding would blur it with similar-looking codes. The "keep my feet dry in a storm" request needs **vector search**: no product title contains those words, but the meaning matches rain boots. Real users type both kinds of queries, so many systems run both searches and merge the lists (for example with Reciprocal Rank Fusion), getting exact precision and semantic recall in one result.
