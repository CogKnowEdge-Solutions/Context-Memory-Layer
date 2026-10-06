# Agentic RAG & LangGraph — Questions & Answers

## Q1. What is Agentic RAG, and how is it different from classical RAG?

Classical RAG is a fixed pipeline: embed the question, fetch the top-k chunks, and generate an answer from them. It runs once, in one order, and it never checks whether the retrieved text was any good. If retrieval misses, the model either guesses or gives a weak answer built on irrelevant context.

Agentic RAG puts a decision-making loop around that pipeline. After retrieving, the agent grades the facts, and if they are poor it changes something (the question, or the tool) and tries again. It stops when the evidence is good enough or when a retry limit is reached. The retrieval step is the same; what is new is that the system can look at its own result and react.

In short: classical RAG retrieves and answers, Agentic RAG retrieves, checks, corrects, and only then answers.

## Q2. Walk through the Part 1 loop (retrieve, grade, rewrite, generate) and say which steps call the LLM.

The loop has four nodes. `retrieve` embeds the question and picks the top chunks with cosine similarity, so it needs no LLM. `grade` asks the LLM one question: do these facts contain any relevant hints, YES or NO. `rewrite` asks the LLM for a clearer version of the question and increases `retry_count`. `generate` writes the final answer from the retrieved facts only.

```python
builder.add_edge(START, "retrieve")
builder.add_edge("retrieve", "grade")
builder.add_conditional_edges("grade", decide_after_grading,
                              {"generate": "generate", "rewrite": "rewrite"})
builder.add_edge("rewrite", "retrieve")
builder.add_edge("generate", END)
```

Only `grade`, `rewrite` and `generate` cost an LLM call. A question that grades YES on the first try therefore costs 2 calls (grade and generate), and a question that fails three times costs 6 (three grades, two rewrites, one generate).

## Q3. What is the agent state, and why is it a TypedDict?

The state is the single object that every node reads and writes as the graph runs. In the lab it holds five keys: `question` (the current, possibly rewritten question), `retrieved_facts`, `grade`, `retry_count` and `final_answer`. Nodes do not pass arguments to each other; they only change this shared state, and the graph decides which node runs next.

A `TypedDict` is used because LangGraph needs to know the state's keys and types when it builds the graph, and a plain typed dictionary is the lightest way to say that. It also gives you editor hints and catches a misspelled key early. Part 2 extends the state with `RoutedState(AgentState)`, which adds one key, `current_tool`.

## Q4. How does the conditional edge decide between `generate` and `rewrite`, and why does it need a retry limit?

The conditional edge calls a routing function after `grade` and uses the returned label to pick the next node.

```python
def decide_after_grading(state):
    if state["grade"] == "YES" or state["retry_count"] >= 2:
        return "generate"
    return "rewrite"
```

The first half sends good evidence on to generation. The second half is the safety valve: when the corpus simply cannot answer the question (the lab's liquid nitrogen example), the grade will stay NO forever, and without a limit the graph would loop between `grade` and `rewrite` until LangGraph stops it with a recursion error. With the limit, the agent gives up after two rewrites and `generate` is told to say that the document does not cover the question.

## Q5. Why does the grader use a softened prompt, and what does the `"YES" in raw_grade` check protect against?

The grading prompt asks whether the facts contain ANY relevant hints, keywords or partial information, rather than whether they fully answer the question. A strict "does this fully answer it" prompt makes the grader reject useful but partial evidence, which triggers needless rewrites and extra cost. A soft prompt keeps the loop for cases where the retrieval really missed.

The parser `"YES" if "YES" in raw_grade else "NO"` is lenient on purpose. Models often reply `YES.` or `Yes, those facts are useful.` even when told to answer with one word, and an exact comparison against `"YES"` would treat these as NO. The trade-off is that a reply such as "NO, there is no YES here" would pass, which is why the prompt demands one word and the temperature is set to 0.

## Q6. What does the rewrite step actually change, and what does it leave alone?

`rewrite_node` replaces `state["question"]` with a clearer version of the question and adds 1 to `retry_count`. It does not touch `retrieved_facts`, `grade` or `final_answer`; the next `retrieve` overwrites the facts and the next `grade` overwrites the grade.

This matters for two reasons. First, the rewritten question is what `generate` will see in the end, so a rewrite that drifts from the user's intent changes the final answer. Second, the lab keeps no copy of the original question. If you want to show the user what they originally asked, you would add an `original_question` key to the state, which is how the capstone handles it.

## Q7. Why is Part 1 retrieval done by cosine similarity, and what does a low score tell you?

`vector_search` embeds the question with the same model that embedded the chunks (`all-MiniLM-L6-v2`, 384 numbers per vector), scores it against every chunk with `cosine_similarity`, and returns the best `top_k` using `scores.argsort()[-top_k:][::-1]`.

```python
scores = cosine_similarity([question_vector], knowledge_vectors)[0]
top_indices = scores.argsort()[-top_k:][::-1]   # best match first
```

Cosine similarity always returns a top-k, even for a question the corpus cannot answer, so a result never says "nothing found" by itself. A low top score (compare the Transformer question with the liquid nitrogen one) is the only signal, and in the lab it is the grader, not a score threshold, that turns that signal into a decision.

## Q8. What problem does the Part 2 router solve, and how does it choose a tool?

Different questions need different retrieval. A definition question ("What is the Transformer?") is a meaning-matching task that vector search handles well. A question about connections ("How is the encoder connected to the decoder?") needs relationships, which a graph database stores explicitly. A router lets the agent pick per question instead of using one tool for everything.

`router_node` asks the LLM to reply with one word, VECTOR or GRAPH, and sets `current_tool` to `GRAPH` only if the reply contains "GRAPH"; anything else defaults to VECTOR. Defaulting to the simpler tool means a messy or empty reply cannot send the run to the graph by accident.

## Q9. How does the graph tool find facts in Neo4j?

`graph_search` works in two steps inside one Cypher query. First it queries the `concept_embeddings` vector index for the 2 concepts nearest to the question (the seeds). Then it follows each seed's relationships one step out and returns lines shaped like `seed --[TYPE]-> neighbor`, capped at 5.

```python
CALL db.index.vector.queryNodes('concept_embeddings', 2, $vector)
YIELD node AS seed, score
MATCH (seed)-[r]-(neighbor:Concept)
RETURN seed.name + ' --[' + type(r) + ']-> ' + neighbor.name AS path
LIMIT 5
```

Two details are worth knowing. The pattern `-[r]-` has no arrow, so it matches both directions and the printed arrow is only a separator. And the vector index always returns the nearest concepts, even for nonsense such as `"zzzz"`, so the placeholder "No relevant information found in Neo4j." only appears when those concepts have no relationships at all.

## Q10. Why does the fallback swap the tool first and only rewrite on the second failure?

A failed grade has two possible causes: the wrong tool was picked, or the question itself is poor. Swapping the tool is free (no LLM call), while rewriting costs one, so the cheaper fix is tried first.

```python
def fallback_node(state):
    if state["retry_count"] == 0:
        state["current_tool"] = "VECTOR" if state["current_tool"] == "GRAPH" else "GRAPH"
        state["retry_count"] += 1
    else:
        state = rewrite_node(state)
    return state
```

The first failure swaps the tool, and the second one reuses Part 1's `rewrite_node`. Because both branches increase `retry_count`, the same limit in `decide_after_grading` still ends the loop after two corrections.

## Q11. How many LLM calls does each path cost in the routed agent?

The routed agent adds one call for the router at the start, and the first fallback is free. A question graded YES on the first try takes 4 nodes and 3 calls (router, grade, generate). A swap and then a YES takes 7 nodes and 4 calls. A question that fails three times takes 10 nodes and 6 calls: router, three grades, one rewrite (the second fallback) and generate.

This is a useful way to see what raising the retry limit would cost: each extra allowed retry adds a rewrite and a grade, so two more LLM calls per failing question.

## Q12. Why can nodes change `state` in place and return it?

In the lab, nodes do `state["retry_count"] += 1` and then `return state`. Python dictionaries are shared by reference, so a plain assignment such as `t = s` points both names at the same dictionary, while `dict(s)` makes a separate copy. LangGraph takes the dictionary a node returns and merges its keys into the graph state, so it does not matter that the node edited the input in place.

The one thing to be careful about is hidden sharing: if a node returned a changed copy that other code also holds, or if you stored the same list in two places, a later change would show up in both. Returning a new dictionary with only the changed keys is the safer style for larger graphs.

## Q13. How do you watch the loop run instead of trusting only the final answer?

Use `stream_mode="values"`. Each item it yields is the whole state after one step, and the first item is the starting state, so you can see `grade` and `retry_count` change as the loop runs.

```python
for s in agent.stream(new_state(q), stream_mode="values"):
    print(s["question"][:60], s["grade"], s["retry_count"], len(s["retrieved_facts"]))
```

A loop-back through `rewrite` is a snapshot where `retry_count` went up. For the unanswerable liquid nitrogen question you should see two of them and a stop at `retry_count == 2`, in about 10 snapshots. Streaming `stream_mode="updates"` instead gives only the keys each node changed, which is shorter when the state is large.

## Q14. How do you stop an agent loop from running forever?

Use several layers, because each one catches a different failure. The first is the retry limit inside the routing function (`retry_count >= 2`), which ends the correction loop by design. The second is LangGraph's own `recursion_limit`, which raises `GraphRecursionError` when a run takes more steps than allowed (the default is 25), and can be set per run:

```python
agent.invoke(new_state(q), config={"recursion_limit": 12})
```

The third is a cost control: count LLM calls per question, as in the call-count table above, so that a change to the limit shows up as a number. The recursion limit is a backstop, not a design tool; a loop that reaches it is a bug in the routing function.

## Q15. How would you extend this agent for production?

Start with what the lab leaves out. Keep the original question in the state next to the rewritten one, so the answer and the trace refer to what the user asked. Record a trace of every attempt (tool, question text, grade) so that "why did it answer this?" has an answer. Add a threshold check on the retrieval score as a cheap pre-grade filter, so obviously empty results skip an LLM call.

Then look at the structure. Add checkpointing so a run can be resumed or paused for a human. Run evaluation questions that the corpus can and cannot answer, and check that the second group ends in an "insufficient evidence" reply rather than a made-up answer. Finally, treat the router and grader prompts as code: pin the model and temperature, and test them against fixed examples.

## References

- LangGraph documentation: https://langchain-ai.github.io/langgraph/
- Corrective RAG (CRAG), Yan et al., 2024: https://arxiv.org/abs/2401.15884
- Self-RAG, Asai et al., 2023: https://arxiv.org/abs/2310.11511
- Adaptive-RAG, Jeong et al., 2024: https://arxiv.org/abs/2403.14403
- Neo4j vector indexes: https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/
