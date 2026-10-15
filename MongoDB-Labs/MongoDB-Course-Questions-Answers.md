# MongoDB Course — Questions & Answers

## Q1. How does MongoDB choose between several possible indexes for one query?

The query planner finds every index that could serve the query and runs the candidate plans in a short trial. The plan that returns the most results while doing the least work wins, and that winning plan is stored in the plan cache for queries of the same shape, meaning the same filter, sort and projection structure but not the same values.

Two consequences matter in practice. A cached plan is dropped when indexes are added or removed, when the collection is dropped, or when the server restarts, and it can be re-planned when it starts to perform much worse than during its trial. And a plan that won on one value can be a poor choice for another value of the same shape (a very common value against a very rare one), which is why the same query can be fast on Monday and slow on Tuesday without any change in code. `explain("allPlansExecution")` shows the rejected plans and how far each got.

## Q2. A compound index `{course_id: 1, status: 1, enrolled_at: -1}` exists. Which of these queries can use it well?

Only the queries that use a **prefix** of the index fields, read from the left.

| Query filters / sorts on | Uses the index well? |
|--------------------------|----------------------|
| `course_id` | Yes (prefix) |
| `course_id` + `status` | Yes (prefix) |
| `course_id` + `status`, sort by `enrolled_at` desc | Yes, and no `SORT` stage |
| `course_id`, sort by `enrolled_at` (skipping `status`) | Partly: the index narrows to the course, but the sort needs a `SORT` stage |
| `status` alone | No (not a prefix; at best a full index scan) |
| `enrolled_at` alone | No |

The reason is that entries are ordered by `course_id` first, then `status` within it, then `enrolled_at`. Without the leading field, matching entries are scattered through the whole index. The same logic explains the ESR rule: the sort field must come after the equality fields, otherwise the order of the index and the order of the result do not line up.

## Q3. A query sorts 2 million documents without an index. What actually happens, and what are the limits?

The server reads the matching documents into memory and sorts them in a blocking `SORT` stage, which cannot return the first result until it has seen all of them. That stage has a memory limit of 100 MB. Older versions failed with an error above it unless `allowDiskUse` was set; from MongoDB 6.0 the default is to spill to disk, which works but is much slower.

The fix is an index whose order matches the sort, so documents arrive already ordered and the stage disappears. With a `limit`, even a blocking sort is cheaper than it sounds: the server keeps only the top *k* results while it streams, which is why `sort` followed by `limit` is much lighter than `sort` alone. In `explain`, look for the `SORT` stage, and for `hasSortStage`/`usedDisk` in the execution stats.

## Q4. Why does `skip(n)` pagination get slower on later pages, and what replaces it?

`skip(n)` cannot jump to the nth result. The server walks through the first *n* index entries (or documents) and throws them away, so page 5,000 costs about as much as reading 5,000 pages and showing one.

The replacement is **range-based (keyset) pagination**: remember the sort value of the last item on the page and ask for the next ones after it.

```python
page = db.enrollments.find(
    {"course_id": "CS101", "status": "active",
     "$or": [{"enrolled_at": {"$lt": last_date}},
             {"enrolled_at": last_date, "_id": {"$lt": last_id}}]}
).sort([("enrolled_at", -1), ("_id", -1)]).limit(10)
```

The `_id` tie-breaker is essential: many documents can share the same `enrolled_at`, and without a unique second key some would be skipped or shown twice between pages. The price is that users can only go "next" and "previous", not jump to page 400.

## Q5. When can a multikey index not cover a query, and what limits apply?

An index on an array field creates one entry per array element, so the index does not store the array as it exists in the document. A query that **returns** the array field therefore has to fetch the documents and is not covered. A query that only filters on the array field and returns other indexed fields can be covered, provided the index is compound, the query does not use `$elemMatch`, and the other covered-query rules are met.

Two more limits follow from the same design. A compound index can have **at most one** indexed array field per document, because indexing two arrays would need every combination of their elements. And a bound on an array field is trickier than it looks: `{tags: {$gt: 2, $lt: 5}}` can match a document whose array has a 1 and a 7, because different elements may satisfy each side of the range, unless you use `$elemMatch`.

## Q6. What is the difference between these two filters on an array of subdocuments?

```python
{"grades.subject": "DB", "grades.score": {"$gt": 90}}
{"grades": {"$elemMatch": {"subject": "DB", "score": {"$gt": 90}}}}
```

The first filter is satisfied if **some** element has `subject == "DB"` and **some, possibly different,** element has `score > 90`. A student with `{DB, 40}` and `{Maths, 95}` matches, which is almost never what the author meant. The second filter requires **one single element** to satisfy both conditions.

The rule to remember: conditions written with dotted paths are evaluated independently against the array, while `$elemMatch` evaluates them together against each element. This is one of the most common causes of a query that "works" in testing and returns wrong rows in production.

## Q7. A collection has a unique index on `email`. The second student without an email cannot be inserted. Why, and how do you fix it?

A missing field is indexed as `null`, and a unique index allows only one `null`. The first student without an email takes that slot; the second collides with it and raises a duplicate-key error on `null`.

The fix is a **partial** unique index that only covers documents that actually have the field:

```python
db.students.create_index(
    "email", unique=True,
    partialFilterExpression={"email": {"$exists": True}})
```

A sparse index (older option) behaves similarly for this case, but partial indexes are the more general tool. Note the catch: the query planner will use a partial index only when the query filter guarantees it can match nothing outside the index, so a query on `email` must include a condition that implies `email` exists.

## Q8. How does a TTL index delete data, and what can you not rely on?

A TTL index is a single-field index on a **date** field (or an array of dates) with `expireAfterSeconds`. A background task wakes up about every 60 seconds and removes expired documents.

You therefore cannot rely on it for exact timing: a document can be visible for a while after it expires, and a busy server may delete in batches. A query that must never return expired data should also filter on the date. Other points: it does not work on a field that is not a date (the document is simply never removed), it cannot be a compound index, and on a replica set the deletion happens on the primary and is replicated like any other delete.

## Q9. Why are single-document updates atomic, and why does that matter for the seat counter?

Every write to one document is atomic, including changes to several fields and to embedded arrays: other operations see either all of the change or none of it. So `find_one_and_update({"seats_available": {"$gt": 0}}, {"$inc": {"seats_available": -1}})` checks and decrements in one indivisible step, and two concurrent requests cannot both take the last seat.

A read followed by a write has a gap in which another request can act, which is the classic **lost update**. A transaction is not what makes the counter safe; the conditional atomic update is. The transaction is needed for the *other* half: tying the seat to the enrollment row, so that if the insert fails the seat comes back. The design rule is to model the data so that the invariant you care about lives in one document and can be protected by a single atomic operation, and to use a transaction only for relationships that span documents.

## Q10. What do `TransientTransactionError` and `UnknownTransactionCommitResult` tell you, and how should the code react?

They are error labels attached by the server and read by the driver.

`TransientTransactionError` means the transaction failed for a reason that may not repeat, such as a write conflict with another transaction or a failover, so the **whole transaction** can be retried from the start. `UnknownTransactionCommitResult` means the commit was sent but the outcome is not known (for example, the connection dropped), so only the **commit** should be retried, because retrying the whole body could apply the work twice.

PyMongo's `with_transaction` runs this logic for you, retrying the callback on transient errors and the commit on unknown results, for a limited time. Business errors (a duplicate key from the unique index, "course is full") carry neither label and must not be retried; they are the answer, not a glitch. Transactions are also limited in time (60 seconds by default), and keeping them short reduces conflicts.

## Q11. Two transactions both decrement the seats of the same course. What happens?

MongoDB transactions use snapshot isolation. When the second transaction tries to modify a document that the first one has already changed and not yet committed, it fails immediately with a **write conflict**, labelled `TransientTransactionError`. It does not wait for the first one to finish.

So under heavy load on one popular course, many transactions fail and retry, and the course document becomes a **hot spot**: throughput on it is limited by how fast conflicting transactions can be serialized. Ways to ease it are to keep the transaction short, to touch the hot document as late in the transaction as the logic allows (a transaction holds its changes until it commits, so an early write to a hot document lengthens the window in which others conflict), and, if one document truly cannot keep up, to split the counter into several documents (for example, one per room or per time slot) and sum them when reading.

## Q12. A write was acknowledged but disappeared after a failover. How is that possible?

With a write concern of `w: 1`, the primary acknowledges as soon as **it** has the write, before any secondary has copied it. If the primary fails right after that and a secondary that had not received the write is elected, the old primary comes back, finds writes the rest of the set never saw, and **rolls them back**; they are saved aside in a rollback file but are no longer in the data.

`w: "majority"` closes the gap: the write is acknowledged only after most members have it, so any member that can be elected has it too. Since MongoDB 5.0 the default write concern is majority (the exception is a set whose arbiters leave too few data-bearing voting members, where it is `w: 1`), and Atlas connection strings set `w=majority`, but a client or a script that overrides it with `w=1` or `w=0` brings the risk back. The price of majority is a little more latency per write. For reads, `readConcern: "majority"` is the matching rule: it returns only data that cannot be rolled back.

## Q13. When is reading from a secondary a mistake?

Secondaries apply writes after the primary, so they can be a little behind (replication lag). A read from a secondary can return data that is older than what the same client just wrote.

A request that writes an enrollment and then immediately reads "my enrollments" from a secondary may not see its own write. Reading from a secondary is reasonable for reports, dashboards and analytics that can tolerate slightly stale data and should not load the primary. It is a mistake for read-your-own-writes flows and for any decision based on current state, such as checking available seats. If you need to read from secondaries and still see your own writes, use **causally consistent sessions** with majority read and write concerns. Also remember that a read preference of `secondary` fails when no secondary is available, whereas `secondaryPreferred` falls back to the primary.

## Q14. How many members does a replica set need to survive failures, and why is two a bad number?

An election needs a **majority of the voting members**. With three members, two form a majority, so the set survives the loss of one. With two members the majority is also two, so losing either member leaves the survivor unable to elect a primary and it becomes read-only. A two-member set therefore tolerates no failures, and it costs more than a single server. With five members the set survives two failures.

This is why a free Atlas M0 cluster has three members: it is the smallest set that can lose one member and keep accepting writes. Adding a fourth member does not help, because the majority becomes three and the set still tolerates only one failure.

## Q15. What do `totalKeysExamined`, `totalDocsExamined` and `nReturned` tell you together?

They show how much work the server did compared with how much it returned.

| Pattern | Meaning |
|---------|---------|
| `totalDocsExamined` ≈ `nReturned` ≈ `totalKeysExamined` | An efficient indexed query: it touched about what it returned |
| `totalKeysExamined` much larger than `nReturned` | The index is not selective enough, or its field order is wrong (an ESR problem) |
| `totalDocsExamined` much larger than `nReturned` | Many documents were fetched and then rejected; a missing or partial index |
| `totalKeysExamined` = 0, `totalDocsExamined` = collection size | A `COLLSCAN` |
| `totalDocsExamined` = 0 with `nReturned` > 0 | A covered query |

The time reported (`executionTimeMillis`) alone is misleading, because a warm cache hides a bad plan; the **ratio of work to results** does not. This is the figure the capstone's before-and-after comparison relies on (about 30,003 documents examined before, about 10 after).

## Q16. Why does the position of `$match`, `$sort` and `$limit` in a pipeline change the cost so much?

The server optimizes a pipeline, but only some orderings can use indexes. A `$match` at the start can use an index; a `$match` after a `$group` or `$project` that changed the fields cannot. A `$sort` at the start can use an index; after a `$group` it must sort in memory. A `$sort` immediately followed by a `$limit` is merged into a top-*k* sort, which keeps only *k* documents in memory.

For `$lookup`, the joined collection needs an index on the `foreignField`; without one, every input document triggers a scan of the other collection, so the cost is the product of the two sizes. Reducing the input first (`$match`, then `$project` to keep only needed fields) before an expensive stage is nearly always the right order. `explain` on an aggregation shows what was pushed down to the query layer and what was left in the pipeline.

## Q17. Why does a hand-made `$regex` search not replace a text or Atlas Search index?

An unanchored regex such as `/programming/i` cannot use an ordinary index efficiently, because it has to inspect every value; only a case-sensitive regex anchored at the start of the string (`/^prog/`) can use index bounds well. It also has no notion of relevance, stemming, typos or multiple words.

A classic text index adds word-based search and scoring but is limited: one per collection, no fuzzy matching, and weak language handling. **Atlas Search** runs a separate Lucene-based search engine alongside the database, with fuzzy matching, filters, autocomplete and relevance scoring, queried with the `$search` stage. The trade-off to remember is **consistency**: a search index is updated asynchronously from the collection, so a document just inserted may not appear in search results for a short moment. For that reason the application should not use a search result as proof that a document exists or not.

## Q18. What makes vector search approximate, and which setting trades recall against speed?

Comparing a query vector with millions of stored vectors one by one is too slow, so Atlas Vector Search builds an **approximate nearest neighbour** index (a graph, HNSW) that finds close vectors without comparing them all. It can therefore miss the true closest vector, which is the price of speed.

The setting that moves this trade-off is `numCandidates`: how many candidates the search examines before returning the top `limit`. A larger value gives better recall and more latency; a common guideline is 10 to 20 times the `limit`. For small collections or when exact results are required, an exact search (`exact: true`) compares against everything. Two more rules: the index dimension must equal the model's output (384 for `BAAI/bge-small-en-v1.5`), and a `filter` inside `$vectorSearch` only works on fields declared as filter fields in the index definition, so filtering after the search instead can leave you with fewer than `limit` results.

## Q19. How does Reciprocal Rank Fusion combine keyword and vector results, and why not add the scores?

A keyword search returns scores on one scale and a vector search returns similarity values on another, so adding them mixes numbers that mean different things. RRF ignores the scores and uses only the **rank** in each list: a document earns `1 / (k + rank)` from every list it appears in, with *k* commonly 60, and the sum decides the final order.

A document that is third in both lists beats one that is first in only one of them, which is the point: agreement between two different retrievers is strong evidence. The constant *k* softens the advantage of the very top ranks. It needs no tuning of weights, but it also cannot express "trust vector search twice as much" unless you weight each list's contribution.

## Q20. How do change streams work, and what can break a consumer?

A change stream is a cursor over the replica set's **oplog** (the log of operations) that returns insert, update, delete and similar events as they happen. It requires a replica set, which an Atlas free cluster provides. Each event carries a **resume token**; storing it lets a consumer that restarts continue exactly after the last event it processed.

Things that break a consumer: a resume token that is older than the **oplog window** (the oplog is a fixed-size log and old entries are overwritten), in which case the stream cannot be resumed and the consumer must rebuild its state another way; an update event that by default carries only the changed fields, not the whole document (ask for `fullDocument: "updateLookup"` and accept that it is the document as it is now, not at the time of the change); and processing that is slower than the arrival of events. Handle the same event twice safely, because after a failure a consumer may see some events again.

## Q21. What does `retryWrites=true` protect you from, and what does it not?

With retryable writes the driver attaches a transaction number to each write and, when a write fails with a network error or a failover, retries it **once**. The server remembers the numbers, so if the first attempt had in fact succeeded it returns that result instead of applying the write twice. This makes `$inc` and inserts safe across a short failover.

It does not retry errors that are the server's answer rather than a transient failure, such as a duplicate key or a validation error, and it does not cover every operation (for example `update_many` and `delete_many` are not retryable writes). It is also not a replacement for idempotent design: a request that your own application repeats after a timeout creates a **new** write with a new number, so a unique index (such as `uniq_student_course`) is still what stops double enrollment.

## Q22. How do `validationLevel` and `validationAction` change what a schema validator does?

A `$jsonSchema` validator lets a flexible collection enforce a few rules. `validationAction` decides what happens to a document that breaks them: `error` rejects the write, `warn` accepts it and writes a log entry. `validationLevel` decides which writes are checked: `strict` checks every insert and update, while `moderate` checks inserts and updates only for documents that **already** satisfy the rules, so old non-conforming documents can still be updated without being rejected.

That makes `moderate` the practical tool for tightening a collection that already contains messy data, and `warn` a safe first step to see how many writes would be rejected before turning on `error`. Validation does not rewrite or fix existing data, and it is not a replacement for application checks of rules that span documents.

## Q23. How would you choose a shard key, and what makes a bad one?

A shard key decides which shard stores each document, and it is hard to change, so the choice matters. A good key has **high cardinality** (many distinct values, so data can be split into many chunks), **even frequency** (no value holds a large share of the documents), and **no monotonic growth** (so new writes do not all land on one shard). Queries should also include the key so they go to one shard rather than all of them.

Bad keys: a boolean or status field (two values, so at most two chunks); a timestamp or an `ObjectId` used directly (always increasing, so every new insert goes to the last chunk, one shard takes all the writes); and a field where one value, such as one very popular course, owns a huge share of the data. A **hashed** key spreads writes evenly at the price of range queries needing every shard. The free Atlas tier cannot shard, so the course treats this conceptually: it is a design decision to be made before the data is large.

## Q24. What would you check before calling the registration database production-ready?

Check correctness under concurrency: run many parallel enrollments for the last seat and confirm exactly one succeeds, the seat count never goes below zero, and a duplicate enrollment leaves the count unchanged. Check performance with real volumes: compare `explain` before and after each index and keep the ratio of examined to returned documents close to 1. Check that every index earns its place by looking for unused ones, because each one slows writes.

Check durability and failure behaviour: use majority write concern, confirm the application survives a primary change, and test the transaction retry paths. Check security: a user with only the roles it needs, an IP access list narrower than 0.0.0.0/0, TLS on, and the connection string kept in the environment and never in code. Finally, have a restore plan that has been practised, and monitoring that alerts on slow queries and replication lag.

## References

- MongoDB Manual, Query plans and the plan cache: https://www.mongodb.com/docs/manual/core/query-plans/
- MongoDB Manual, The ESR (Equality, Sort, Range) guideline: https://www.mongodb.com/docs/manual/tutorial/equality-sort-range-guideline/
- MongoDB Manual, Multikey indexes: https://www.mongodb.com/docs/manual/core/indexes/index-types/index-multikey/
- MongoDB Manual, Partial indexes: https://www.mongodb.com/docs/manual/core/index-partial/
- MongoDB Manual, TTL indexes: https://www.mongodb.com/docs/manual/core/index-ttl/
- MongoDB Manual, Aggregation pipeline optimization: https://www.mongodb.com/docs/manual/core/aggregation-pipeline-optimization/
- MongoDB Manual, Transactions: https://www.mongodb.com/docs/manual/core/transactions/
- MongoDB Manual, Production considerations for transactions: https://www.mongodb.com/docs/manual/core/transactions-production-consideration/
- MongoDB Manual, Write concern: https://www.mongodb.com/docs/manual/reference/write-concern/
- MongoDB Manual, Rollbacks during replica set failover: https://www.mongodb.com/docs/manual/core/replica-set-rollbacks/
- MongoDB Manual, Replica set elections: https://www.mongodb.com/docs/manual/core/replica-set-elections/
- MongoDB Manual, Causal consistency: https://www.mongodb.com/docs/manual/core/causal-consistency-read-write-concerns/
- MongoDB Manual, Change streams: https://www.mongodb.com/docs/manual/changeStreams/
- MongoDB Manual, Retryable writes: https://www.mongodb.com/docs/manual/core/retryable-writes/
- MongoDB Manual, Schema validation: https://www.mongodb.com/docs/manual/core/schema-validation/
- MongoDB Manual, Shard keys: https://www.mongodb.com/docs/manual/core/sharding-shard-key/
- MongoDB Atlas Search: https://www.mongodb.com/docs/atlas/atlas-search/
- MongoDB Atlas Vector Search: https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-overview/
- Cormack et al., Reciprocal Rank Fusion (SIGIR 2009): https://dl.acm.org/doi/10.1145/1571941.1572114
- MongoDB Atlas free cluster limits: https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/
