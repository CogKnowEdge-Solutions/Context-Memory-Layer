# RAG Course — Questions & Answers

## Q1. What is Retrieval-Augmented Generation, and why use it instead of just asking an LLM?

An LLM answers from what it memorized during training, so it cannot know your private documents or anything newer than its training data, and when it does not know it tends to produce a fluent guess. RAG fixes this by searching an external knowledge source at question time and handing only the relevant passages to the model, with the instruction to answer from them.

The effect is twofold: the model can answer about data it was never trained on, and every answer can be traced back to a source passage, which reduces hallucination and makes the result checkable. The original idea comes from Lewis et al., 2020.

## Q2. What are the stages of the canonical RAG pipeline?

The first lab builds it in six stages. **Load** reads the source (a PDF or text file). **Chunk** splits it into passages small enough to be searched and fit in the prompt. **Embed** turns each chunk into a vector. **Index** stores those vectors so they can be searched quickly. **Retrieve** embeds the question and returns the nearest chunks. **Generate** gives the question and those chunks to the LLM and asks for an answer grounded in them.

```python
chunks = splitter.split_text(document_text)       # chunk
vectors = embeddings.embed_documents(chunks)      # embed
scores = cosine_similarity([embeddings.embed_query(q)], vectors)[0]   # retrieve
top = [chunks[i] for i in scores.argsort()[-3:][::-1]]
```

Every later lab changes one of these stages; the rest of the pipeline stays recognizable.

## Q3. How do you choose a chunk size and overlap?

A chunk must be small enough that its vector represents one idea (a big chunk blurs several topics into one embedding) and large enough to carry the context needed to answer. Overlap repeats a little text at the boundary so a sentence cut in two is still found whole in one chunk.

There is no universal value; start with a few hundred characters or a few hundred tokens, then test with real questions and look at what is actually retrieved. Splitting on natural boundaries (paragraphs, then sentences, then words) is better than cutting at a fixed length. Later labs show two other answers to the size problem: semantic chunking, and parent-child chunking, where small and large chunks are both used.

## Q4. What is an embedding, and what does cosine similarity measure?

An embedding is a list of numbers (384 for `all-MiniLM-L6-v2`) produced by a model so that texts with similar meaning end up close together. Cosine similarity measures the angle between two vectors: 1 means the same direction (very similar meaning), values near 0 mean unrelated.

Two practical rules follow. The question and the chunks must be embedded with the same model, or the numbers are not comparable. And similarity search always returns the closest chunks, even when none are relevant, so a low top score is a warning sign that retrieval missed.

## Q5. Why is dense retrieval alone not enough, and what does Hybrid RAG add?

Dense (embedding) search matches meaning, so it handles paraphrases well but can miss exact terms such as product codes, names, error messages or rare keywords. Sparse search (BM25) matches the words themselves, so it is exact on those terms but blind to synonyms. Each fails where the other works.

Hybrid RAG runs both retrievers over the same chunks and fuses the two ranked lists. The fusion lab uses Reciprocal Rank Fusion (RRF): each chunk earns `1 / (k + rank)` from every list it appears in, and the sums decide the final order. RRF works on ranks, not scores, which matters because BM25 scores and cosine scores are on different scales and cannot be added directly.

## Q6. What is semantic chunking, and how is it different from fixed-size chunking?

Fixed-size chunking cuts after a number of characters, regardless of meaning. Semantic chunking embeds neighbouring sentences and starts a new chunk where the meaning shifts, so each chunk tends to cover one topic. The result is chunks of uneven length that are more coherent, at the cost of extra embedding work during ingestion and a threshold that needs tuning.

## Q7. What is Parent-Child (multi-vector) retrieval, and what problem does it solve?

There is a tension in chunk size: small chunks match a question precisely but give the LLM too little context, while large chunks give context but make fuzzy embeddings. Parent-child splits the difference. Documents are cut into large parent chunks, and each parent is cut again into small child chunks. Only the children (and optionally a summary of each parent) are embedded and searched; when a child matches, the system returns its whole parent to the LLM.

So one parent becomes two searchable entry points, its child chunks and its summary, and the answer is written from the full parent. The lab stores the vectors in Qdrant and keeps the parents in a separate store, linked by an id.

## Q8. What is ColBERT and late interaction, and when is it worth the extra cost?

A normal dense retriever squeezes a whole chunk into one vector. ColBERT keeps one small vector per token, for both the question and the chunk. Scoring is **MaxSim**: for each question token, find its best match among the chunk's tokens, then add up those best scores. This preserves fine detail, because a specific word in the question can match a specific word in the chunk.

The price is storage and compute: a chunk is a matrix of vectors, not one vector, so the index is much larger and scoring is heavier. It is worth it when exact phrasing matters and one-vector retrieval ranks the right chunk too low; the common compromise is to use cheap retrieval first and a ColBERT-style scorer on a short candidate list (the original paper is Khattab and Zaharia, 2020).

## Q9. How do you build RAG over scanned documents or images of text?

A scanned PDF contains pictures of pages, not text, so a normal loader returns nothing. The OCR lab adds a step before chunking: run an OCR engine (RapidOCR here) on each page image to recover the text, then continue with the usual chunk, embed, retrieve and generate stages.

Two cautions apply. OCR makes errors, especially on tables, small print and poor scans, and those errors become part of your index, so check a sample of the extracted text before trusting the answers. And a long PDF should be processed page by page (with page numbers kept as metadata), so you can cite where an answer came from.

## Q10. What is an LLM Wiki, and how does it differ from a vector index?

Instead of searching raw chunks at question time, the LLM Wiki approach has the model read the source once and write it up as a set of structured pages (the lab uses an Open Knowledge Format, OKF) plus an index that lists them. At question time the model reads the index, chooses the pages that matter, and answers from them.

The effort moves from query time to ingestion time. The benefit is a readable, auditable knowledge base where each fact lives in a known file; the cost is that you pay for the LLM during ingestion, and a mistake made while writing a page persists until you rebuild it.

## Q11. What is Graph RAG, and when does it beat vector search?

Graph RAG stores knowledge as a graph: nodes for concepts (entities) and edges for the relationships between them, extracted from the text as triples such as (Encoder, FEEDS, Decoder). A question is answered by finding the right nodes and walking their relationships.

It beats vector search on questions about connections and multiple hops ("what is two steps away from X?", "how are A and B related?"), because the links are stored explicitly rather than hoped for inside one chunk. It is weaker for plain definition questions, and the graph is only as good as the extraction: missing or wrong triples mean missing or wrong answers. The lab builds the graph first in memory with NetworkX, then in Neo4j (see Microsoft's GraphRAG paper, 2024).

## Q12. How do you store and query a graph in Neo4j?

Nodes and relationships are written with Cypher. `MERGE` creates a node or relationship only if it does not already exist, which keeps repeated writes from creating duplicates. Queries use `MATCH` with a pattern.

```python
session.run("MERGE (c:Concept {name: $name})", name=node)
session.run("MATCH (a:Concept {name:$s}), (b:Concept {name:$t}) "
            "MERGE (a)-[r:`FEEDS`]->(b)", s="Encoder", t="Decoder")
```

One detail to remember: the `MATCH` before the `MERGE` must find both endpoints, so a relationship whose source or target name was not extracted as a node is silently skipped. This is a common reason why fewer relationships are stored than the LLM returned.

## Q13. Why combine vector search and graph traversal (Hybrid Graph + Vector RAG)?

Each half covers the other's weakness. Vector search finds the concepts that match the wording of a question, even when the user does not know the exact name. The graph then expands from those concepts to their connected facts, which gives the multi-hop context vector search cannot.

In the lab, concept names are embedded and kept in a Neo4j vector index. A query first uses the index to pick the nearest concepts (the seeds), then a Cypher pattern follows their relationships one step out, and the combined facts go to the LLM. The vector step answers "where do I start?", the graph step answers "what is connected to it?".

## Q14. What is Vectorless RAG, and how does PageIndex retrieve without embeddings?

Vectorless RAG skips embeddings and the vector database. PageIndex reads a document and builds a tree of its sections, like a table of contents with summaries and page ranges. At question time the LLM reads the tree, reasons about which sections should hold the answer, and the system fetches the text of exactly those pages.

This works well for long, well-structured documents (reports, filings, manuals), where the answer lives in a named section and similarity search tends to return fragments out of context. A multi-hop version collects several sections before answering. The costs are LLM calls at retrieval time and weaker performance on documents with no clear structure.

## Q15. How do you choose between dense, sparse, hybrid, ColBERT, graph and vectorless retrieval?

Start from the question and the documents, not from the tool. Definition and "what is" questions over unstructured text suit dense search. Exact terms, codes and names add sparse search, which makes it hybrid. When precise word-level matching matters, a ColBERT-style scorer helps. Questions about connections and multi-step relationships suit graph retrieval. Long, structured documents where the answer sits in a known section suit vectorless, tree-based retrieval.

| Need | Reasonable first choice |
|------|-------------------------|
| Meaning, paraphrases | Dense vectors |
| Exact keywords, IDs | Hybrid (dense + BM25) |
| Fine-grained phrase match | ColBERT / late interaction |
| Relationships, multi-hop | Graph or graph + vector |
| Long structured reports | Vectorless (tree) |

The lesson of the course is that no single choice wins everywhere, which is why the last labs let an agent choose.

## Q16. What is Agentic RAG, and what does the self-correcting loop do?

Agentic RAG wraps retrieval in a loop that can check and change its own work. The agent retrieves, an LLM grades whether the facts help, and if the grade is NO it rewrites the question and retrieves again. A retry limit ends the loop, after which the answer step says plainly that the document does not cover the question.

The loop is built as a LangGraph `StateGraph` with nodes for retrieve, grade, rewrite and generate, and a conditional edge after `grade` that chooses between `generate` and `rewrite`. Related research includes Corrective RAG (CRAG) and Self-RAG.

## Q17. What is routing, and how does a fallback improve on rewriting alone?

A router lets the agent pick the tool per question: vector search for meaning and definitions, graph search for connections. When a grade fails, the fallback tries the cheapest fix first. The first failure only swaps the tool (no LLM call), on the idea that the router may simply have chosen the wrong one. The second failure rewrites the question, because then the question is the more likely problem.

This ordering keeps cost down: a swap is free, a rewrite costs an LLM call, and both count toward the same retry limit.

## Q18. Why must the answer step use only the retrieved facts?

The whole point of RAG is an answer you can check against a source. If the generator also draws on its training memory, you cannot tell which parts came from your documents, and wrong "facts" slip in with the right ones. So the prompt tells the model to answer using only the provided facts and to say when they do not contain the answer.

The labs reinforce this with an explainability section: the answer names the facts it used. A good test is a question the corpus cannot answer (such as the boiling point of liquid nitrogen in a paper about Transformers); the correct behaviour is an "insufficient evidence" reply, not a confident invention.

## Q19. How do you evaluate a RAG system?

Evaluate retrieval and generation separately, because they fail in different ways. For retrieval, build a small set of questions with known source chunks and measure whether the right chunk appears in the top-k (hit rate) and how high it ranks. For generation, check faithfulness (is every claim supported by the retrieved text?) and answer relevance (does it address the question?).

Include unanswerable questions in the set, since a system that always answers is wrong on those. Read real traces too: print the retrieved chunks and the grade for failing questions, and fix the stage that went wrong before changing anything else.

## Q20. What are the most common reasons a RAG system gives a bad answer?

Most failures trace back to a handful of causes. The right information was never indexed (bad loading or OCR). The chunking split an answer across chunks or buried it in a long one. The retriever matched the wrong kind of thing (meaning when exact terms were needed, or the reverse). The right chunk was retrieved but ranked below the top-k cut. The prompt allowed the model to ignore the context, or the context was so long that the relevant part was lost in the middle (Liu et al., 2023).

Debug in order: first check that the answer exists in the indexed text, then whether it was retrieved, then whether it reached the prompt, and only then whether the model used it.

## Q21. What does the capstone Agentic Research Assistant add on top of the individual labs?

The capstone puts several retrievers behind one agent. A router picks a tool for each question (dense, sparse or graph), one tool runs per attempt, a grader checks the evidence, and a correction step either swaps the tool or rewrites the question. Attempt 1 uses the routed tool, attempt 2 swaps it with the same question, and attempt 3 rewrites the question on the swapped tool, with `max_attempts` set to 3 counting the first try.

Everything the agent did is kept in the state (`original_question`, `question`, `route`, `attempts`, `retrieved`, `grade`, `answer`, `trace`), so the final output can show an explainability trace of each attempt. Fusion and reranking are optional extensions, and adapters let a cloud backend such as Qdrant replace a local tool without changing the loop.

## Q22. What would you check before putting a RAG system into production?

Check the data pipeline: how new or changed documents get re-ingested, and whether deleted documents leave the index. Check quality with a fixed test set that includes unanswerable questions, run again after each change. Check cost and latency per question, including the number of LLM calls on the worst path. Check safety: keep keys out of code, avoid sending sensitive data to services you have not approved, and limit what a tool can write. Finally, log each question with its retrieved sources and final answer, so a bad answer can be investigated afterwards.

## References

- Lewis et al., Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks (2020): https://arxiv.org/abs/2005.11401
- Khattab and Zaharia, ColBERT (2020): https://arxiv.org/abs/2004.12832
- Cormack et al., Reciprocal Rank Fusion (SIGIR 2009): https://dl.acm.org/doi/10.1145/1571941.1572114
- Edge et al., From Local to Global: A Graph RAG Approach (2024): https://arxiv.org/abs/2404.16130
- Liu et al., Lost in the Middle (2023): https://arxiv.org/abs/2307.03172
- Yan et al., Corrective RAG (2024): https://arxiv.org/abs/2401.15884
- Asai et al., Self-RAG (2023): https://arxiv.org/abs/2310.11511
- PageIndex (vectorless RAG): https://github.com/VectifyAI/PageIndex
- LangGraph documentation: https://langchain-ai.github.io/langgraph/
- Neo4j vector indexes: https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/
