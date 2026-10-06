# Capstone: Reference Answers to the Post-Capstone Assignment

This is the instructor answer key for Section 10 of the capstone spec. Every answer follows the design fixed in Sections 6 and 7: one tool per attempt, `max_attempts = 3` counting the first try, attempt 1 = routed tool, attempt 2 = swap (same question), attempt 3 = rewrite (swapped tool). Question text, chunk ids and facts in the worked examples are illustrative, not real output.

---

## Question 1: Trace a run that starts on `sparse`, gets `NO`, and recovers on `graph`

**Question used:** "Which concept is affected two steps away from the tide gate?" (a connection question that keyword search handles poorly).

| Step | Loop stage | Keys that change | Values after the step |
|------|------------|------------------|-----------------------|
| 0 | start, `new_state(question)` | all keys created | `original_question` = the question above; `question` = same text; `route` = ""; `attempts` = 0; `retrieved` = []; `grade` = ""; `answer` = ""; `trace` = [] |
| 1 | **route** | `route`, `trace` | `route` = `sparse`; trace gets one `route` entry with the router's rationale |
| 2 | **retrieve** (attempt 1) | `retrieved`, `attempts`, `trace` | `retrieved` = BM25 chunks that mention "tide gate" but not what it affects; `attempts` = 1 |
| 3 | **grade** | `grade`, `trace` | `grade` = `NO` |
| 4 | **correct: swap** | `route`, `retrieved`, `grade`, `trace` | `route` = `graph` (the table in 7.2: sparse goes to graph); `retrieved` = []; `grade` = ""; trace records "swap sparse to graph". `question` and `attempts` do not change |
| 5 | **retrieve** (attempt 2) | `retrieved`, `attempts`, `trace` | `retrieved` = facts within 2 hops of "tide gate", for example `Tide gate --[BLOCKS]--> Tidal exchange` and `Tidal exchange --[CARRIES]--> Sediment`; `attempts` = 2 |
| 6 | **grade** | `grade`, `trace` | `grade` = `YES` |

After the loop, `synthesize` sets `answer` (grounded in the two facts) and `finalize` prints the blocks. Neither is one of the four loop stages.

**Pattern to check in a student's answer.**

- `original_question` never changes.
- `attempts` goes up only at retrieve.
- `question` is untouched on a swap, because the rewrite happens only on the second `NO`.
- A correction always clears `retrieved` and `grade`, so the next grade cannot read stale data.

---

## Question 2: Why must `synthesize` read only `retrieved`?

Without the retrieved evidence the model answers from its training memory. That is the ungrounded guessing RAG exists to prevent, and the answer could no longer be checked against a source: the explainability trace would cite chunks that were not actually used. If the run fails to find evidence, the correct behaviour is the "insufficient evidence" message, not a fluent guess.

**Which lab first established the rule:** Lab 1, which instructs the model to answer using only the retrieved context and to say it does not know otherwise. Labs 9 and 10 carry the same rule into the agent loop.

`synthesize` still reads `original_question`, because it has to know what to answer. It never reads the rewritten `question`, which exists only for retrieval.

---

## Question 3: A question that ends in "insufficient evidence"

**Question:** "Who won the 1998 FIFA World Cup?" The corpus is a guide to coastal wetland restoration, so no tool can find an answer.

| Attempt | Tool | Question text used | Grade |
|---------|------|--------------------|-------|
| 1 | `dense` (the router's choice; a plain factual question has no connection or keyword cue) | "Who won the 1998 FIFA World Cup?" | `NO` (the nearest chunks are about wetlands, so cosine scores are low) |
| 2 | `graph` (swap table: dense goes to graph) | "Who won the 1998 FIFA World Cup?" (unchanged) | `NO` (no entity in the graph matches, so there are no facts) |
| 3 | `graph` (same tool as attempt 2) | The rewritten question, for example "1998 FIFA World Cup winning national team" | `NO` (still no matching entity) |

After the grade on attempt 3, `attempts == max_attempts == 3`, so no correction runs. `synthesize` returns the explicit "insufficient evidence" message, and the explainability trace lists all three attempts with their tool, question text and verdict.

**Accept any similar answer** if it (a) uses a question the corpus cannot answer, (b) follows the fixed positions: routed tool with the original question, then the swapped tool with the original question, then the swapped tool with the rewritten question, and (c) does not run the third tool. If the router picks `sparse` the sequence is the same except attempt 1.

---

## Question 4: Where does the reranker go?

**Default design (one tool per attempt).** Insert one `rerank` step between `retrieve` and `grade`, operating on `state["retrieved"]`. It runs once per attempt, on whatever the tool returned.

**Why not inside each tool.**

- **Duplication:** the same reranking code would be written and tested three times.
- **Coupling:** every tool would depend on the reranker model, which breaks the idea of a tool that only retrieves.
- **Different outputs:** the graph tool returns facts, not scored text chunks, so a text reranker does not apply to it in the same way. A single step after retrieval can decide per tool whether to rerank, in one place.
- **Contract:** every tool already returns the same `{chunks, meta}` shape, which is exactly what makes a single shared step possible.

**Under the multi-tool extension (7.3).** The reranker moves after **fusion**: tools run, fusion merges their lists into one, rerank reorders the merged list once, then grading sees it. Reranking before fusion would reorder lists whose scores are not comparable and then discard that work when the lists are merged.

---

## Question 5: Dense and graph results disagree (multi-tool extension)

**Combining results.**

1. Convert both outputs to the common `{chunks, meta}` shape. Graph facts become short text chunks that carry their source relation.
2. Merge with rank-based fusion (Lab 2): each item earns `1 / (k + rank)` from every list it appears in, and the sums decide the order. Rank-based scores avoid comparing cosine values to graph scores, which are not on the same scale.
3. Keep provenance on every merged item: which tool produced it and its rank there. Lab 8 does the same kind of combining, with vector similarity choosing the starting entities and graph expansion adding the connected facts.
4. Rerank once, then grade.

**What counts as disagreement.** Two cases: the lists have little or no overlap (they point to different evidence), or the grader or synthesizer finds statements that contradict each other.

**Reporting a conflict in the trace.**

- Record each tool's returned items and ranks separately, plus the fused order.
- Record a `conflict` entry that names the two tools and the claims that clash, with chunk ids and graph facts.
- In the `EXPLAINABILITY` block, state it plainly: "dense and graph evidence disagree on X", show both sources, and say which one the answer used and why.
- If the conflict cannot be resolved from the evidence, the answer should say the sources conflict instead of picking one silently.

---

## Question 6: One adapter contract for a cloud backend

**Backend chosen:** Qdrant (a replacement for the local dense tool).

The adapter is a function `retrieve_qdrant(state)`. It must obey the single contract every tool obeys:

- **Input:** `state`. It reads `state["question"]` (the current, possibly rewritten question), never `original_question`, and nothing else.
- **Output:** `{chunks, meta}`.
  - `chunks`: a list of items with the same fields as the local tools, for example `{id, text, score, source}`, ordered best first.
  - `meta`: at least `{tool: "dense", backend: "qdrant", question: <text used>, top_k: <n>}`, so the trace can report which tool and backend ran.
- **Behaviour:** embed the question with the same model the collection was built with (otherwise vectors are not comparable), query the collection, and translate each hit into the chunk shape. It does not change `state`; the loop alone updates `attempts`, `retrieved` and `trace`.
- **Failure:** if the backend is unreachable or returns nothing, return empty `chunks` with an `error` note in `meta`. It must not raise, so the loop can grade `NO` and apply its normal swap and rewrite rules.

Because `route` names the tool (`dense`) rather than the backend, switching from the local FAISS tool to Qdrant is a registration change in one place. The loop, grader, rewriter, synthesizer and finalizer do not change.

The same contract applies to Neo4j (a `graph` adapter that returns facts as chunks) and PageIndex (a tree search that returns section text as chunks).
