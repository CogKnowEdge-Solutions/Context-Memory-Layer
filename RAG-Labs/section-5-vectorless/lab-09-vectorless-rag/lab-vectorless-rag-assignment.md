# Assignment: Vectorless RAG — Coding Problems

Put what you learned in **Vectorless RAG** into code — but go beyond the lab. The lab indexed the bundled Century Communities Q1 2025 earnings release once with PageIndex, then answered three kinds of question without any vectors: Part 1 let the LLM read the tree's `node_id`/`title`/`summary` and pick sections, Part 2 gathered text from several sections ("hops") and printed a trail, and Part 3 kept tables whole and tagged every number with `[Table n]`. The problems below rebuild each piece from scratch, then stretch it: measure what the tree costs against the whole document, diagnose a broken JSON parser, see what the page cap silently drops, change `top_k`, compare the lab's crude title check with a number-based check, and compare a tree-reasoning answer with a search-based answer.

**How to work**

- Environment, API-key and LLM setup are not repeated here: reuse the setup from the first assignment (Classical RAG); only the PageIndex key and client are new. `call_llm(prompt)` is just `llm.invoke([HumanMessage(content=prompt)]).content.strip()` around that `llm` (keep `max_tokens` modest and the model's hidden reasoning switched off, as the earlier assignments do).
- Write each problem in a scratch Python file, run the setup once, then reuse `tree`, `doc_id` and the helpers. Run the problems in order in one session.
- Each problem says exactly what to print; print it.
- PageIndex output depends on an LLM, so node ids, titles and numbers can differ a little from run to run. Check your output against the shape given in the hints, not word for word.
- Where a problem asks for a prediction, write it as a comment before you run the code, then explain any gap between prediction and result.
- **State carries over.** Problem 1 creates `pi_client` and `doc_id`; 2 creates `tree`; 3 creates `node_map`; 4 creates `page_texts`; 5 creates `parse_json`, which 6 uses; 6 creates `pick_sections`; 7 creates `build_context` and needs `node_map` (3) and `page_texts` (4); 8 and 9 use `build_context` (7); 6-9 need `tree`; 9 also uses `pick_sections` (6); 10-14 need `doc_id`; 11 creates `hops` and `answer`, which 12 needs; 13 needs `explain` from 12; 14 needs `reasoning_rag` (9) and `table_rag` (13).

---

**1.** Set up PageIndex, the one new service in this assignment: read `PAGEINDEX_API_KEY` with `os.getenv` (fall back to `input()` if it is missing), set `os.environ["PAGEINDEX_API_KEY"]`, and build `pi_client = PageIndexClient(api_key=PAGEINDEX_API_KEY)`. Then write `index_pdf(client, path, timeout=600, poll=5) -> str` from scratch: submit `data/CCS-Q1-2025-Earnings-Release.pdf`, poll `client.is_retrieval_ready(doc_id)` until true, and raise `TimeoutError("PageIndex timeout")` when `timeout` seconds pass. Return `doc_id`. Print `Submitted: {doc_id}` and `Tree ready after {elapsed}s`.

*Hint:* indexing takes a minute or two; do it once and reuse `doc_id` for everything below.

**2.** Fetch the tree with `pi_client.get_tree(doc_id, node_summary=True)["result"]` and write a recursive `count_nodes(node) -> int` plus a recursive `list_titles(node, depth=0) -> list[str]` that returns each title indented by two spaces per level. Print `Total nodes: {n}` and then one title per line.

*Hint:* child nodes sit under the `"nodes"` key; a leaf has none. Expected: `Total nodes: <a number around a dozen or more>` then the indented titles.

**3.** Audit the page ranges the tree gives you. Build `node_map = utils.create_node_mapping(tree, include_page_ranges=True)` and, for every id in it, compute the span `end_index - start_index + 1`. Print `Widest node: {id} | {title} | pages {start}-{end} ({span} pages)` for the widest node other than the root, `Single-page nodes: {n} of {len(node_map)}`, and `Nodes with an empty summary: {k}` (use `.get("summary")` on the node). Add one comment saying why a node that spans many pages is a risk when you build context from page ranges (problem 8 puts a number on it).

*Hint:* `node_map[id]` gives `["start_index"]`, `["end_index"]` and `["node"]["title"]`. In the lesson's tree the widest non-root node is usually `Forward-Looking Statements` (about pages 3-11), but the exact tree varies between runs, so report whatever you get.

**4.** Measure what reading the tree costs against reading the whole document. Extract the PDF's page text with `pymupdf.open(...)` and `doc.load_page(i).get_text()` into `page_texts`, a dict keyed by 1-based page number. Print `Whole PDF text: {chars} characters across {n} pages`, `Tree as JSON: {chars} characters`, and `Tree is {ratio:.0f}% of the document text`, then one line saying what the ratio means for how the LLM can be asked to choose sections.

*Hint:* `json.dumps(tree)` gives the tree string you would embed in a prompt. Report your actual ratio; it depends on the run's tree and summaries.

**5.** A classmate wrote this parser, and it is missing something the lesson's `parse_json` has:

```python
def parse_json_v1(reply):
    try:
        return json.loads(reply)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", reply)
        return json.loads(match.group()) if match else {"thinking": "", "node_list": []}
```

Build a pretty-printed reply that wraps the JSON in chatter over several lines: `Sure! Here you go:`, then `{`, `"thinking": "short",`, `"node_list": ["0003"]` and `}` each on their own line, then `Hope that helps.` First write a comment predicting what `parse_json_v1` returns for it and why. Run it, then write the fixed `parse_json(reply) -> dict` from scratch (try `json.loads`, fall back to `re.search(r"\{.*\}", reply, re.DOTALL)`, and keep the `{"thinking": "", "node_list": []}` fallback when nothing matches) and test it on four strings: clean JSON, the same JSON wrapped on one line in `Sure! Here you go: ... Hope that helps.`, the pretty-printed reply, and the plain sentence `no json here`. Print `broken: {result}`, `clean: {result}`, `wrapped: {result}`, `pretty: {result}` and `plain: {result}`.

*Hint:* look at what `.` matches in a regular expression by default, and at the `re.DOTALL` flag. Expected: `broken:` prints `{'thinking': '', 'node_list': []}` (no single line holds both braces); `clean:`, `wrapped:` and `pretty:` print the same dict; `plain:` prints `{'thinking': '', 'node_list': []}`.

**6.** Write `pick_sections(query) -> dict` from scratch: embed the full `tree` as JSON in a prompt that demands a reply of exactly `{"thinking": "...", "node_list": ["node_id_1"]}` and asks for the most specific nodes, call `call_llm`, and parse with your `parse_json`. Run it with `"How much cash and total liquidity did the company have at the end of the first quarter?"` and print the first 200 characters of `thinking`, then the `node_list` on its own line.

**7.** Write `build_context(node_ids, max_pages=3) -> tuple[str, list[int]]` from scratch using `node_map` (3) and `page_texts` (4). For each id in `node_ids`, take at most `max_pages` pages from its page range, skip ids missing from the map, never add a page twice, and prefix each page with `--- Page {p} ---`. Return the joined context and the list of pages. Call it with the ids from problem 6 and print `Pages used: {pages}` and `Context length: {len(context)} characters`.

*Hint:* PageIndex page numbers are 1-indexed, which is why `page_texts` is keyed from 1.

**8.** Show what the page cap silently drops. Predict first: in a comment, write which pages of a wide node you expect `max_pages=3` to drop. Then call `build_context(["0008"], max_pages=3)` and `build_context(["0008"], max_pages=20)` (use the widest-spanning node from problem 3 if `0008` differs). Work out which pages the cap dropped and check whether any dropped page mentions `Adjusted Net Income` (use `in` on `page_texts`). Print `Capped: {pages_capped} -> {chars_capped} chars`, `Uncapped: {pages_all} -> {chars_all} chars`, `Dropped pages: {dropped}` and `Dropped pages mentioning Adjusted Net Income: {hits}`, then one line stating which run risks overflowing the LLM's prompt and why, and one line stating what risk the capped run takes instead.

*Hint:* expect the capped run to list 3 pages and the uncapped run many more; `Dropped pages` is exactly the uncapped list minus the capped one. Report whatever `hits` shows; the point is that the cap drops pages with no warning.

**9.** Collapse Part 1 into `reasoning_rag(query) -> tuple[str, list[int]]`: pick sections, print one line per pick as `picked {nid} | {title}` (printing `{nid} | not in tree` for an id the tree does not contain), build the context, and answer with a prompt containing the context, the question and the rules `Answer only from the context`, `If the answer is not there, say so` and `Be concise`. Add the branch the lab never reaches: when the context is empty return `("No relevant section found.", [])` without calling the LLM. Run it on the problem 6 question and on a forced empty pick, and print both outcomes.

**10.** Write `retrieve(query, top_k=5) -> list[dict]` from scratch using `pi_client.submit_query(doc_id=doc_id, query=query)` and a polling loop on `pi_client.get_retrieval(retrieval_id)` that stops on `status == "completed"`, returns `[]` on `"failed"`, and prints and retries on exceptions. For each of the first `top_k` retrieved nodes return `{"number", "section", "node_id", "pages", "text"}`, extracting page numbers with `re.search(r"(\d+)", ...)` from the `physical_index` strings. Run it on `"What was adjusted net income for Q1 2025 and Q1 2024?"` and print one line per item as `{number} | {section} | node_id {node_id} | pages {pages}`.

*Hint:* search replies list matches under `retrieved_nodes`, each with `relevant_contents` groups holding `relevant_content` and `physical_index`; see "What the search sends back" in the lesson. Expected: up to `top_k` lines of the form `1 | <section> | node_id <id> | pages [<numbers>]`.

**11.** Write `multi_hop_rag(query, top_k=5) -> tuple[str, list[dict]]` from scratch: retrieve, join the texts, and ask the LLM for a short plain-language answer from that context only. Run it with the lab's GAAP-versus-adjusted net income question and print the hop titles, the answer, and then the `top_k=2` result for the same question as `top_k=2 answer: {answer}`. Keep the `top_k=5` results as `hops` and `answer`. Print one line saying whether the two answers contain the same Q1 2024 net income figure.

**12.** Write `explain(query, items, is_used, kind) -> None` from scratch: for each item print `{kind} {number}: "{section}"`, then `node_id: ... | page(s): ... | USED in answer` or `retrieved but NOT clearly used` according to `is_used(item)`, then ask the LLM for a 3-4 line reason that cites the numbers in the section, printing it after `Why:`. Call it for the multi-hop run from problem 11 with the lab's crude check `lambda h: h["section"] in answer`. Then compare two designs of `is_used`: predict in a comment whether a number-based check will mark more or fewer hops than the title check, and write `number_used(h)` that returns true when any decimal figure found in the answer (for example `64.3`) also appears in that hop's `text`. Print `Title check: {a} of {len(hops)} hops used` and `Number check: {b} of {len(hops)} hops used`, then one line naming a hop the two checks disagree on (if any) and which check you trust more, and why.

*Hint:* `re.findall(r"\d[\d,]*\.\d+", answer)` pulls decimal figures out of the answer; strip `$` and commas before comparing if you like. The number check usually marks at least as many hops as the title check, because the hop that supplied the figures need not have its title quoted in the answer. Report your actual counts; do not expect a fixed number.

**13.** Write `table_rag(query, top_k=2) -> tuple[str, list[dict]]` from scratch: label each retrieved item `[Table {number} - {section}]` in the context and use a prompt that requires every number to be tagged like `[Table 1]`, tagged separately per table, and requires the exact text `Not found in document.` when the data is absent. Run it on `"What was the total revenue for the three months ended March 31, 2025?"`, print the answer, then call `explain` with `lambda t: f"[Table {t['number']}]" in answer`. Print `Tables cited: {n_cited} of {len(tables)}`.

*Hint:* expected answer around `$903.2 million [Table 1]`.

**14.** Compare the two retrieval styles on one question: answer `"How much cash and total liquidity did the company have at the end of the first quarter?"` with `reasoning_rag` (tree reasoning) and with `table_rag(top_k=2)` (PageIndex search). Print `reasoning_rag: {answer}` and `table_rag: {answer}`, then the pages each one read (`pages` from the first, the union of `item["pages"]` from the second), and one line stating whether the two answers agree on the liquidity figure.
