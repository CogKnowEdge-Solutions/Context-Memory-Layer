# Assignment: Hybrid RAG (Dense + Sparse) with Semantic Chunking — Coding Problems

Put what you learned in **Hybrid RAG (Dense + Sparse) with Semantic Chunking** into code — but go beyond the lab. The lab fuses a `VectorStoreIndex` dense retriever and a `BM25Retriever` sparse retriever over meaning-based `SemanticSplitterNodeParser` nodes and prints the post-fusion `source_nodes` behind an answer about tidal flow. The problems below rebuild each retriever on its own so you can see exactly where they disagree, sweep the knobs the lab only mentions — `breakpoint_percentile_threshold`, `buffer_size`, `num_queries`, and `mode` — and then break the pipeline on purpose to find out what each setting was quietly protecting you from.

**How to work**

- Write each problem from scratch in a scratch Python file. Each problem says exactly what to print; print it.
- Environment, API-key and LLM setup are not repeated here: reuse the setup from the first assignment (Classical RAG).
- Keep everything in one scratch file and run it top to bottom: problems 4 to 9 and 11 to 13 reuse the nodes, retrievers or `response` you build earlier, and each problem names what it needs.
- Problems 7, 8, 9, 11 and 14 call the LLM, so they need the key and LLM from that first assignment; the others run locally.
- The hints point to calls the lab did not show and say roughly what to expect; exact numbers vary by run.

---

**1.** Wire LlamaIndex to the setup you already have: with the OpenRouter key and model from the first assignment, assign `Settings.llm` to a LlamaIndex `OpenRouter` model (same model name, `temperature=0`, `max_tokens=512`) and set `Settings.embed_model` to `HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")`. Then build `SemanticSplitterNodeParser(buffer_size=1, breakpoint_percentile_threshold=95, embed_model=Settings.embed_model)` and print `Settings.embed_model.model_name`, then the splitter's `buffer_size`, then its `breakpoint_percentile_threshold`.

*Hint:* if the `OpenRouter` or `HuggingFaceEmbedding` import path is unclear, copy the imports from the lab's Setup cell. *Expected:* `all-MiniLM-L6-v2`, then `1`, then `95`. Later problems read these `Settings`, so run this first.

**2.** Write `load_pdf(path: str) -> list` that builds a `PDFReader()` and calls `load_data(file=path)` on `data/sample_text_document.pdf`. Print `Loaded {len(documents)} document(s)`, then print the `doc_id` of the first returned document and the `class_name` of that same document, so you can see what a LlamaIndex document actually carries before it is chunked.

*Hint:* `doc_id` is an attribute (`documents[0].doc_id`), while `class_name` is a method, so call it with parentheses: `documents[0].class_name()`. *Expected:* `Loaded 2 document(s)` for the lab's PDF, one `doc_id` string, and a short class name.

**3.** Write `chunk_documents(documents, threshold: int) -> list` that builds `SemanticSplitterNodeParser(buffer_size=1, breakpoint_percentile_threshold=threshold, embed_model=Settings.embed_model)` and returns `get_nodes_from_documents(documents)`. Call it three times with `threshold=95`, `threshold=75`, and `threshold=25`, and print one line per threshold in the form `{threshold} -> {n} nodes, mean {m:.0f} chars` where `m` is the mean character length of `node.text` — the point being that a high threshold cuts rarely while a low one shatters the same document into fragments.

*Hint:* each call embeds the whole document again, so it takes a little while. The `95` call should give the 4 nodes the lab reports; lower thresholds should give more, shorter nodes (exact counts depend on the model run). Problems 4 onward reuse the `threshold=95` nodes.

**4.** Build only the dense half: create `vector_index = VectorStoreIndex(nodes)` from the `threshold=95` nodes and `vector_retriever = vector_index.as_retriever(similarity_top_k=3)`, then call `vector_retriever.retrieve("tidal flow")` directly with no LLM involved. Print the number of nodes returned, then for each node print `Dense {i+1}: score={node.score:.4f} | {first 80 characters of node.text}`.

*Hint:* `retrieve(...)` takes a plain string and returns a list of nodes with a `.score`. *Expected:* 3 nodes (the document has only 4 chunks), with cosine scores on a roughly 0 to 1 scale. This needs the 95-threshold `nodes` from problem 3.

**5.** Build only the sparse half over the exact same `nodes`: `bm25_retriever = BM25Retriever.from_defaults(nodes=nodes, similarity_top_k=3)`, then call `bm25_retriever.retrieve("tidal flow")` — the identical string used in the previous problem. Print `Sparse {i+1}: score={node.score:.4f} | {first 80 characters of node.text}` for each returned node, so the two lists of scores can be laid side by side and the scale mismatch made obvious.

*Hint:* BM25 scores are not cosine values and can be well above 1, so compare the order of the two lists, not the numbers. *Expected:* up to 3 nodes. Uses the same `nodes` as problem 4.

**6.** Compute the agreement between the two retrievers for the query `"How is sediment handled after a breach?"`: fetch the `node.id_` values from `vector_retriever.retrieve(...)` and from `bm25_retriever.retrieve(...)`, print how many nodes each retriever returned, print the count of `node.id_` values present in both lists, and print each shared `node.id_` on its own line.

*Hint:* collect each list's `node.id_` values into a `set` and use `&` to find the shared ones. *Expected:* 3 nodes from each retriever; because 3 + 3 is more than the 4 chunks that exist, at least 2 IDs must be shared. Uses the retrievers from problems 4 and 5.

**7.** Build the fused retriever exactly as the lab does — `QueryFusionRetriever([vector_retriever, bm25_retriever], similarity_top_k=3, num_queries=1, mode="reciprocal_rerank")` — wrap it in `RetrieverQueryEngine.from_args(hybrid_retriever)`, and ask `QUERY = "Why do restoration teams reintroduce tidal flow gradually instead of all at once?"`. Print `Source nodes used (Post-Fusion):`, then for each node in `response.source_nodes` print `--- Source {i + 1} (score: {node.score:.4f}) ---` followed by the first 200 characters of `node.text`, and finally print the answer itself under an `Answer:` line.

*Expected:* 3 source nodes, with scores close to the lab's `0.0333`, `0.0328` and `0.0161`, followed by an answer about erosion and a phased, staged opening. Wording of the answer varies. Needs the retrievers from problems 4 and 5 and the LLM from problem 1.

**8.** Rebuild the fusion with `mode="simple"` instead of `mode="reciprocal_rerank"`, leaving everything else identical, and run the same `QUERY` through it. Print one line per rank showing `simple={simple_score:.4f} | reciprocal={reciprocal_score:.4f}` for the source nodes in rank order, then print a single line reporting whether the top-ranked `node.id_` is the same under both fusion modes.

*Hint:* `mode="simple"` does not add scores; it keeps the highest raw score per chunk and sorts by it, so its values are on the cosine or BM25 scale. Run the query through both retrievers and match scores by `node.id_`. *Expected:* the simple scores look very different from the tiny reciprocal ones, and the top chunk may or may not match. Reuses `vector_retriever`, `bm25_retriever` and `response` from problems 4, 5 and 7.

**9.** Build a third `QueryFusionRetriever` with `num_queries=3` instead of `num_queries=1`, run the same `QUERY`, and print the number of source nodes returned, the number of distinct `node.id_` values among them, and the fused `.score` of each. Then print one line stating whether raising `num_queries` widened the retrieved set or just re-ranked the same set.

*Hint:* with `num_queries=3` LlamaIndex asks the LLM to write extra versions of the question, so this makes extra API calls and needs your key. *Expected:* never more than 3 sources, since `similarity_top_k=3` and the document has only 4 chunks. Reuses the retrievers from problems 4 and 5 and `QUERY` from problem 7.

**10.** Hold `breakpoint_percentile_threshold=95` fixed and change only `buffer_size`. Before running anything, write a comment with your prediction: will `buffer_size=0` give fewer, the same, or more nodes than the 4 you got with `buffer_size=1`, and why? Then build a `SemanticSplitterNodeParser(buffer_size=b, breakpoint_percentile_threshold=95, embed_model=Settings.embed_model)` for `b` in `0`, `1` and `3`, run each on `documents`, and print one line per value in the form `buffer_size={b} -> {n} nodes`. Finish with a comment explaining any gap between your prediction and the result, using the lab's definition of `buffer_size`.

*Hint:* each run re-embeds the document, so it takes a little while. *Expected:* `buffer_size=1` gives the lab's 4 nodes. For the other two values, look for whether the count moves at all and in which direction; exact counts depend on the model run, and a small or zero change is a valid result to explain. Needs `documents` from problem 2.

**11.** Break the retrieval on purpose: ask the fused query engine the completely off-topic question `"Who won the 1998 FIFA World Cup?"`. Print the answer, then print the number of source nodes that came back with it, then print one line explaining why a retriever configured with `similarity_top_k=3` hands back three "relevant" chunks even when nothing in the document is relevant at all.

*Expected:* still 3 source nodes, because retrievers always return the best `top_k` they can find, relevant or not. The LLM may decline to answer or answer from its own knowledge; the wording varies. Reuses the query engine from problem 7.

**12.** Reproduce the lab's fused scores yourself. Run `vector_retriever.retrieve(QUERY)` and `bm25_retriever.retrieve(QUERY)` and record each node's position (counting from 0) by `node.id_` in a dict per retriever. Then for each node in `response.source_nodes` (from problem 7) compute `expected = sum(1 / (60 + rank))` over the lists the node appears in, and print one line per source: `Source {i + 1}: dense_rank={r1 or None} sparse_rank={r2 or None} computed={expected:.4f} actual={node.score:.4f}`. Before running, write a comment predicting which source appears in only one list.

*Hint:* use `dict.get(node.node_id)` so a missing node gives `None`; add only the terms for lists that contain it. *Expected:* `computed` equals `actual` on every line (to 4 decimals), and the pattern matches the lab's table: one source in the same position in both lists, one in only one list with a single `1/(60 + rank)` term. Needs the retrievers from problems 4 and 5 and `response` from problem 7.

**13.** The `60` in `1 / (60 + rank)` controls how fast a rank's contribution falls off. Using the two rank dicts from problem 12, recompute the fused score of every source node with the constant changed to `1`, i.e. `1 / (1 + rank)`. Before running, write a comment predicting two things: whether the order of the three sources changes, and whether the gap between the top and bottom source gets larger or smaller. Then print one line per source, `Source {i + 1}: k=60 -> {score60:.4f} | k=1 -> {score1:.4f}`, then `Top/bottom ratio: k=60 -> {ratio60:.2f} | k=1 -> {ratio1:.2f}`, then one line stating whether the order stayed the same. End with a comment explaining, in one sentence, what a larger constant does to the importance of rank.

*Hint:* the ratio is the top source's score divided by the bottom source's. *Expected:* with the lab's ranks, `k=1` scores come out as `2.0000`, `1.0000` and `0.3333` and the order stays the same; the top/bottom ratio is about `2.07` at `k=60` and `6.00` at `k=1`, so a smaller constant makes rank matter more. Depends on problem 12.

**14.** Write `hybrid_answer(query: str, top_k: int = 3, mode: str = "reciprocal_rerank") -> tuple` that builds the dense retriever, the `BM25Retriever`, and the `QueryFusionRetriever` inside the function, runs `RetrieverQueryEngine.from_args(...)`, and returns the answer string plus the list of source nodes. Call it twice on the same `QUERY`, once with `top_k=1` and once with `top_k=5`, and print `top_k=1 -> {n} sources, {c} context chars` and `top_k=5 -> {n} sources, {c} context chars` where `c` is the total character length of all source nodes passed to the LLM.

*Expected:* `top_k=1` returns 1 source; `top_k=5` returns at most 4 sources because the document has only 4 chunks, so the character count grows but stops there. Reuses `nodes` from problem 3 and the `Settings` from problem 1.
