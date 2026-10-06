# Assignment Answers: Agentic RAG — Reference Solutions

Instructor answer key for the **Agentic RAG** assignment. Each answer gives a short reference solution and the output to expect. Where a result depends on the LLM or on the graph the LLM extracted (problems 7, 9, 12, 13, 14, 15 and 16), the key states the pattern to check instead of exact text, so accept any run that shows the same pattern.

---

**1.** The retry limit is 2, and `retrieve` makes no LLM call, so only `grade`, `rewrite` and `generate` count.

```python
# YES on the first try: retrieve -> grade -> generate
predicted_yes = ["retrieve", "grade", "generate"]
# NO three times: grade says NO at retry 0, rewrite, NO at retry 1, rewrite,
# then at retry 2 the guard sends it to generate whatever the grade is
predicted_no3 = ["retrieve", "grade", "rewrite", "retrieve", "grade", "rewrite",
                 "retrieve", "grade", "generate"]
calls_yes = 2    # grade + generate
calls_no3 = 6    # 3 grade + 2 rewrite + 1 generate
print(predicted_yes, predicted_no3, calls_yes, calls_no3)
```

A common slip is to predict four rewrites. The third `NO` never reaches `rewrite`, because `retry_count` is already 2.

**2.**

```python
def simulate(grades, routed=False):
    nodes, calls, retry = [], 0, 0
    if routed:
        nodes.append("router"); calls += 1
    for g in grades:
        nodes += ["retrieve", "grade"]; calls += 1
        if g == "YES" or retry >= 2:
            nodes.append("generate"); calls += 1
            break
        if routed:
            nodes.append("fallback")
            if retry == 1: calls += 1      # second failure rewrites
        else:
            nodes.append("rewrite"); calls += 1
        retry += 1
    return nodes, calls
```

Expected counts (nodes, calls):

| Grades | Part 1 | Routed |
|--------|--------|--------|
| `["YES"]` | 3, 2 | 4, 3 |
| `["NO", "YES"]` | 6, 4 | 7, 4 |
| `["NO", "NO", "NO"]` | 9, 6 | 10, 6 |

Note the routed case: the first `fallback` only swaps the tool, so it costs no call. This gives `Matches problem 1: True` for both predicted Part 1 paths. If a student got `False`, the usual cause is a missing `rewrite` to `retrieve` edge or counting `retrieve` as a call.

**3.**

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class S(TypedDict):
    count: int

def bump(s): s["count"] += 1; return s
def again(s): return "again" if s["count"] < 3 else "stop"

g = StateGraph(S)
g.add_node("bump", bump)
g.add_edge(START, "bump")
g.add_conditional_edges("bump", again, {"again": "bump", "stop": END})
app = g.compile()

snaps = list(app.stream({"count": 0}, stream_mode="values"))
for s in snaps: print(s)
print(len(snaps), len(snaps) - 2)
```

Output: `{'count': 0}`, `{'count': 1}`, `{'count': 2}`, `{'count': 3}`, then `4 2`. There are 4 snapshots (the starting state plus three runs of `bump`), and 2 of them are loop-backs, because the first run of `bump` is not one.

**4.**

```python
print(len(document_text))                     # 1500
splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50,
                                          separators=["\n\n", "\n", ".", " ", ""])
knowledge_base = splitter.split_text(document_text)
print(f"Knowledge base ready with {len(knowledge_base)} chunks.")   # 6
tail = knowledge_base[0][-50:]
print("Overlap preserved:", tail in knowledge_base[1])
knowledge_vectors = embeddings.embed_documents(knowledge_base)
print(len(knowledge_vectors[0]))              # 384
```

Accept either `True` or `False`, provided the one-line reason matches. `True` means the splitter merged small pieces and repeated some text. `False` means the chunk ended at a paragraph or line break, so nothing was carried over. The vector length is 384 because `all-MiniLM-L6-v2` always returns 384 numbers.

**5.**

```python
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def chunk_scores(q):
    return cosine_similarity([embeddings.embed_query(q)], knowledge_vectors)[0]

def vector_search(q, top_k=2):
    idx = chunk_scores(q).argsort()[-top_k:][::-1]
    return [knowledge_base[i] for i in idx]

q = "How does the Transformer work?"
sc = chunk_scores(q)
for text in vector_search(q, 3):
    print(knowledge_base.index(text), f"{sc[knowledge_base.index(text)]:.4f}")
print(f"{chunk_scores('What is the boiling point of liquid nitrogen?').max():.4f}")
```

The exact numbers depend on the chunks, so check the pattern: scores are printed highest first, and the top score for the Transformer question is clearly higher than the top score for the liquid nitrogen question. Retrieval always returns the top-k chunks, even for a poor match, so a low score is the only warning sign.

**6.**

```python
print(list(AgentState.__annotations__))
# ['question', 'retrieved_facts', 'grade', 'retry_count', 'final_answer']
print(new_state("transformer stuff"))
print(list(RoutedState.__annotations__))
# the five above, then 'current_tool'

s = new_state("a"); t = s
t["retry_count"] += 1
print(s["retry_count"])         # 1  (t and s are the same dict)
u = dict(s); u["retry_count"] += 1
print(s["retry_count"])         # 1  (u is a copy, s is unchanged)
print(s is t, s is u)           # True False
```

The usual wrong prediction is `2` for the second print. `dict(s)` makes a new dictionary, so the change through `u` never reaches `s`. Nodes that change `state` in place and return it still work because LangGraph takes the returned dictionary and merges its keys into the graph state; it does not depend on the node leaving the input untouched.

**7.**

```python
def grade_node(state):
    facts = "\n".join(state["retrieved_facts"])
    prompt = f"""Question: {state['question']}
Retrieved facts:
{facts}

Do these facts contain ANY relevant hints, keywords, or partial information that could help answer the question?
Reply with ONLY one word: YES or NO."""
    raw = llm.invoke(prompt).content.strip().upper()
    state["grade"] = "YES" if "YES" in raw else "NO"
    return state
```

Expected: `Grade: YES` for the Transformer question and `Grade: NO` for liquid nitrogen. A different result on the second is the grader being too generous; the point is that the facts, not the question alone, decide the grade.

**8.**

```python
def lenient(r): return "YES" if "YES" in r else "NO"
def strict(r):  return "YES" if r.strip() == "YES" else "NO"
for raw in ["YES", "YES.", "Yes, those facts are useful."]:
    r = raw.upper()
    print(f"{raw!r:36} lenient={lenient(r)} strict={strict(r)}")
```

| Reply | Substring match | Exact match |
|-------|-----------------|-------------|
| `YES` | YES | YES |
| `YES.` | YES | NO |
| `Yes, those facts are useful.` | YES | NO |

Exact matching silently turns a correct "yes" into `NO` whenever the model adds a full stop or a sentence, which causes needless rewrites. The weakness of the substring rule is the opposite one: a reply such as "NO, there is no YES here" would pass as `YES`, which is why the lab prompt demands one word.

**9.**

```python
def rewrite_node(state):
    prompt = f'''This question did not return good search results: "{state['question']}"
Rewrite it to be clearer and easier to search for. Reply with only the new question.'''
    state["question"] = llm.invoke(prompt).content.strip()
    state["retry_count"] += 1
    return state

s = new_state("transformer stuff"); s["grade"] = "NO"; s["retry_count"] = 1
rewrite_node(s)
print("Rewritten question:", s["question"])
print("retry_count:", s["retry_count"])
```

Check that the question text changed into a full question about the Transformer (the wording varies by run) and that `retry_count` is `2`.

**10.**

```python
def decide_after_grading(state, limit=2):
    return "generate" if state["grade"] == "YES" or state["retry_count"] >= limit else "rewrite"

for limit in (2, 3):
    n = 0
    for grade in ("YES", "NO"):
        row = [decide_after_grading({"grade": grade, "retry_count": rc}, limit) for rc in range(4)]
        n += row.count("rewrite")
        print(limit, grade, row)
    print("rewrite cells:", n)
```

Prediction to write before running: 2 cells with `limit=2` and 3 cells with `limit=3`. The `"rewrite"` cells are `NO` at `retry_count` 0 and 1 for `limit=2`, and `NO` at 0, 1 and 2 for `limit=3`. Every `YES` row is `generate`.

- `If the retry clause were removed:` a `NO` grade would always return `"rewrite"`, so a question the corpus cannot answer (such as liquid nitrogen) would cycle between `grade` and `rewrite` until LangGraph stops it with a recursion error.
- `Raising the limit costs:` two more LLM calls per failing question (one `rewrite` and one `grade`), since `retrieve` is free. This matches the jump from 4 to 6 calls between the `["NO", "YES"]` and `["NO", "NO", "NO"]` runs in problem 2.

**11.**

```python
def retrieve_node(state):
    state["retrieved_facts"] = vector_search(state["question"]); return state

def generate_node(state):
    facts = "\n".join(state["retrieved_facts"])
    prompt = f"""Answer the question using ONLY these facts. If they do not contain the answer, say the document does not cover it.
{facts}

Question: {state['question']}

Output EXACTLY two sections:
--- FINAL ANSWER ---
[short, direct answer]

--- EXPLAINABILITY ---
[the specific facts you used]"""
    state["final_answer"] = llm.invoke(prompt).content.strip(); return state

b = StateGraph(AgentState)
for n, f in [("retrieve", retrieve_node), ("grade", grade_node),
             ("rewrite", rewrite_node), ("generate", generate_node)]:
    b.add_node(n, f)
b.add_edge(START, "retrieve"); b.add_edge("retrieve", "grade")
b.add_conditional_edges("grade", decide_after_grading,
                        {"generate": "generate", "rewrite": "rewrite"})
b.add_edge("rewrite", "retrieve"); b.add_edge("generate", END)
agent = b.compile()
print("Self-correcting agent compiled successfully!")
print(sorted(agent.get_graph().nodes.keys()))
for e in agent.get_graph().edges: print(e.source, "->", e.target)
```

Expected nodes: `['__end__', '__start__', 'generate', 'grade', 'retrieve', 'rewrite']`. Expected edges: `__start__ -> retrieve`, `retrieve -> grade`, `grade -> generate`, `grade -> rewrite`, `rewrite -> retrieve`, `generate -> __end__`. The two edges out of `grade` are the conditional ones.

**12.**

```python
for q in ["How does the Transformer work?", "What is the boiling point of liquid nitrogen?"]:
    prev, loops = None, 0
    for s in agent.stream(new_state(q), stream_mode="values"):
        if prev is not None and s["retry_count"] > prev: loops += 1
        prev = s["retry_count"]
        print(s["question"][:60], "|", s["grade"], "|", s["retry_count"], "|", len(s["retrieved_facts"]))
    print("Loop-backs through rewrite:", loops)
```

Expected pattern. The Transformer question grades `YES` first time, giving 3 steps (plus the starting snapshot) and `Loop-backs through rewrite: 0`. The liquid nitrogen question grades `NO`, is rewritten twice, and stops at `retry_count == 2`, giving `Loop-backs through rewrite: 2`. The history then shows 10 snapshots: the start plus 9 node steps, the same 9-node path predicted in problem 1. If the grader says `YES` for the second question, the run ends sooner; report that and say that the softened prompt is lenient. Retrieved facts always has 2 items because `vector_search` returns `top_k=2`.

**13.**

```python
for k in ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD"):
    assert os.getenv(k), f"{k} is missing"
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
driver.verify_connectivity()
# ... clear the database, extract JSON from document_text, MERGE nodes and
# relationships, create the concept_embeddings index (384, cosine), embed every Concept ...
print(f"LLM extracted {len(graph_data['nodes'])} nodes and {len(graph_data['relationships'])} relationships.")
```

The counts vary between runs, so check only that both are non-zero and that the code used the lab's `MERGE` pattern, the index settings (384 dimensions, cosine) and an embedding on every `Concept`. The database is cleared first, so it must be a throwaway instance.

**13b (stretch).**

```python
with driver.session() as s:
    n_nodes = s.run("MATCH (n:Concept) RETURN count(n) AS n").single()["n"]
    types = s.run("MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS c ORDER BY c DESC").data()
print(n_nodes); [print(r["t"], r["c"]) for r in types]
stored = sum(r["c"] for r in types)
print(f"LLM returned {len(graph_data['relationships'])}, stored {stored}: "
      "they can differ because MERGE collapses duplicates and a relationship is skipped "
      "when its source or target name was not extracted as a node.")
```

The stored count is at most the returned count. Two causes: `MERGE` stores a repeated relationship once, and the `MATCH (a), (b)` before `MERGE` finds nothing when an endpoint name does not match any node exactly, so that relationship is silently dropped.

**14.**

```python
q = "What models or mechanisms are sequence transduction models based on or connected to?"
print("VECTOR:"); [print(" ", t[:80]) for t in vector_search(q)]
print("GRAPH:");  [print(" ", p) for p in graph_search(q)]
r = graph_search("zzzz")
print(len(r)); [print(p) for p in r]
```

Expected: `VECTOR:` shows two text chunks, `GRAPH:` shows up to 5 lines such as `Concept --[TYPE]-> Neighbor`. For `"zzzz"`, expect up to 5 lines rather than the placeholder. The vector index returns the 2 nearest concepts whatever the question is, so the placeholder `No relevant information found in Neo4j.` appears only when those concepts have no relationships.

**15.**

```python
def router_node(state):
    prompt = f'''Analyze this question: "{state['question']}"
- VECTOR: general concepts, definitions, broad meaning.
- GRAPH: connections, components, relationships, multi-hop logic.
Reply with ONLY one word: VECTOR or GRAPH.'''
    state["current_tool"] = "GRAPH" if "GRAPH" in llm.invoke(prompt).content.strip().upper() else "VECTOR"
    return state

def fallback_node(state):
    if state["retry_count"] == 0:
        state["current_tool"] = "VECTOR" if state["current_tool"] == "GRAPH" else "GRAPH"
        state["retry_count"] += 1
    else:
        state = rewrite_node(state)
    return state
```

Expected router choices: `VECTOR` for "What is the Transformer?", `GRAPH` for the encoder-to-decoder connection question, and usually `VECTOR` for the liquid nitrogen question. Expected fallback results: with `retry_count=0` and `GRAPH`, the tool becomes `VECTOR`, the question is unchanged and `retry_count` is 1. With `retry_count=1`, the tool is unchanged, the question is rewritten and `retry_count` is 2. Defaulting to `VECTOR` unless the reply contains `GRAPH` keeps a messy reply from sending the run to the graph.

**16.**

```python
b = StateGraph(RoutedState)
b.add_node("router", router_node); b.add_node("retrieve", routed_retrieve_node)
b.add_node("grade", grade_node);   b.add_node("fallback", fallback_node)
b.add_node("generate", generate_node)
b.add_edge(START, "router"); b.add_edge("router", "retrieve"); b.add_edge("retrieve", "grade")
b.add_conditional_edges("grade", decide_after_grading,
                        {"generate": "generate", "rewrite": "fallback"})
b.add_edge("fallback", "retrieve"); b.add_edge("generate", END)
routed_agent = b.compile()
print("Routed agent compiled successfully!")
for e in routed_agent.get_graph().edges: print(e.source, "->", e.target)
```

Expected edges: `__start__ -> router`, `router -> retrieve`, `retrieve -> grade`, `grade -> generate`, `grade -> fallback`, `fallback -> retrieve`, `generate -> __end__`.

To list the tools used in order, stream each question with `new_state(q, current_tool="")` and collect `s["current_tool"]` from each snapshot, dropping repeats. Report what your run shows. The expected pattern is that the first two questions are answered with no `fallback`, and the liquid nitrogen question is the one most likely to swap and then rewrite, ending with `retry_count` 2. Its path should match the routed `["NO", "NO", "NO"]` simulation from problem 2: router, retrieve, grade, fallback (swap), retrieve, grade, fallback (rewrite), retrieve, grade, generate. A grade of `YES` earlier is also acceptable; the check is that the final line states which questions swapped and which rewrote, and that this agrees with the printed tool order and `retry_count`.
