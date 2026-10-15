# Assignment Answers - How to Search by Keywords and by Meaning

Sample answers for the tasks. Your wording and code may differ; what matters is that the result is right.

---

## Task 1

```python
print(catalog.count_documents({}))
print(catalog.find_one({}, {"_id": 0, "embedding": 0}))
```

## Task 2

```python
show(list(catalog.aggregate(text_pipeline("databases"))))
```

## Task 3

```python
show(list(catalog.aggregate(text_pipeline("databses", fuzzy=False))))
show(list(catalog.aggregate(text_pipeline("databses", fuzzy=True))))
```
Only the fuzzy search finds courses: it accepts one wrong letter, so `databses` still matches `databases`. The plain search looks for the exact word, which no course contains.

## Task 4

```python
show(list(catalog.aggregate(text_pipeline("data", level="advanced"))))
```
The level is applied as a filter, so only advanced courses can appear.

## Task 5

```python
vec = embed_text("make my chatbot remember what customers said")
print(len(vec))
```
The answer is 384: the embedding model turns any text into 384 numbers that represent its meaning.

## Task 6

```python
show(list(catalog.aggregate(vector_pipeline(vec, limit=5))))
```
The results are courses about conversation memory and state, even though they do not contain your words. That is the point of searching by meaning.

## Task 7

```python
show(list(catalog.aggregate(vector_pipeline(vec, limit=5, level="intermediate"))))
```

## Task 8

```python
show(hybrid_search("databses for storing chat history"))
```
The keyword half tolerates the typo and the vector half understands the idea, and the two rankings are merged.

## Task 9

Course A is rank 2 in the first list and rank 1 in the second: 1/62 + 1/61 = 0.0325. Course C is rank 1 and rank 3: 1/61 + 1/63 = 0.0323. Course B appears only once, at rank 2: 1/62 = 0.0161. Course D appears only once, at rank 3: 1/63 = 0.0159. The order is A, C, B, D.

```python
print(rrf_fuse([["C", "A", "D"], ["A", "B", "C"]]))
```
