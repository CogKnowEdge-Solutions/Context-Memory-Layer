# Lab 7: Capstone Project -- AI Agent Memory Service

## Assignment Brief (2 Weeks)

---

# Objective Sheet

This is the final lab in the MongoDB Mastery module. You will build, from scratch, an **AI Agent Memory Service** that integrates everything from Labs 1-6 into a single storage layer an agent harness can rely on.

**What you are building:** A notebook (`lab-agent-memory-service.ipynb`) that logs conversations and messages (Labs 1-2), extracts and recalls long-term memories into a `memories` collection (Labs 2-4), records tool-call history and commits each turn atomically with its tool calls (Labs 3, 5), produces token and tool-failure analytics (Labs 1, 3), and secures the whole service with inspection, RBAC, and TLS (Lab 6).

**What you are NOT building:** This is not a take-home exam with hidden test cases. The rubric is fully transparent below. Every requirement is listed. There are no trick questions.

**The companion file (`lab-agent-memory-service.md`) is your reference**, not a script to copy-paste. It describes what a correct implementation looks like with illustrative output. Your actual output will differ in `_id`s, token counts, and exact aggregation numbers.

---

# Mandatory

All of the following **must** be present in your submission. Missing any one means you lose the associated points.

| # | Requirement | Where to verify |
|---|-------------|----------------|
| 1 | Notebook first code cell is exactly `!pip install -qU "pymongo[srv,tls]==4.10.1" python-dotenv==1.0.1 certifi` (single line only) | Notebook cell 1 |
| 2 | Connection loads `MONGODB_URI` from `.env` via `load_dotenv("../../.env")` and `os.environ`; no hardcoded credentials | Connection cell |
| 3 | Four collections exist in the `agent_memory` database: `conversations`, `messages`, `memories`, `tool_calls` | List collections check |
| 4 | Schema decision documented: what is embedded vs. referenced across the four collections (Lab 4); messages/tool_calls reference `conversation_id` | Design note |
| 5 | 3 synthetic conversations inserted, tagged `pytest-lab7-<hex>` (Lab 1 insert, Lab 2 CRUD) | Collection count check |
| 6 | 8 synthetic messages inserted across those conversations, spanning `user` and `assistant` roles (Labs 1-2) | Collection count check |
| 7 | At least 5 synthetic memories extracted into `memories` and linked to their source conversation via `$lookup` (Lab 4) | Query returning linked memory |
| 8 | Memory extraction uses `upsert` so re-runs never duplicate a memory (Lab 2) | Re-run shows 0 duplicates |
| 9 | A text index on `memories.text` exists (Lab 4) and a ranked text-search recall returns a memory from a *different* conversation (continuity, Lab 6) | Recall query + outcome |
| 10 | `.explain()` on the recall query shows index use, not a collection scan (Lab 3) | explain() output |
| 11 | 4 synthetic tool calls logged in `tool_calls`, tagged, mixing `ok: True` and `ok: False` outcomes (Lab 3) | Collection count check |
| 12 | The assistant-message + its tool-call write is a multi-document transaction; a change stream on `tool_calls` observes at least one new document (Lab 5) | Transaction + change stream output |
| 13 | Aggregation pipelines: token usage per conversation, and tool-failure rate per tool (Labs 1, 3) | Aggregation output |
| 14 | An index + `.explain()` on a hot analytics query shows index use (Lab 3) | explain() output |
| 15 | Replica set inspected (e.g. `hello` shows `setName` and `hosts`) and TLS verified via the `tlsCAFile=certifi.where()` connection (Lab 6) | hello + connection output |
| 16 | A read-only reviewer role has `read` on `memories` only, verified by a permissions query (Lab 6 RBAC) | Permissions query |
| 17 | Cleanup: all tagged rows deleted in child-first order, reviewer role dropped | Final verification query |
| 18 | No hardcoded credentials in notebook (MONGODB_URI loaded from .env) | Grep for mongodb+srv in code cells |

---

# Optional

These are **not required for a Pass** but improve your grade. Attempt them after completing all Mandatory items.

| # | Exercise | Points | Notes |
|---|----------|--------|-------|
| 1 | Per-agent memory filter: compound index on `{agent: 1, source_conversation_id: 1}` and a recall that only returns the current agent's memories, with `.explain()` showing index use | +5 | Combines Labs 3-4; the Assignment brief's Optional Exercise |
| 2 | Add a "token cost by conversation" report using an aggregation pipeline with both a `$group` and a `$sort` stage | +3 | Reuses Lab 3 aggregation |
| 3 | Write a one-page "Memory Service Checklist" document (Appendix A format) and include it in `submission/` | +2 | Maps each requirement to verification method |

---

# Deliverables

Submit the following files:

| File | What it is | Mandatory? |
|------|-----------|-----------|
| `lab-agent-memory-service.ipynb` | Your notebook (the main graded artifact) | Yes |
| `lab-agent-memory-service.md` | Reference companion (from module materials) | Already provided |
| `lab-agent-memory-service-assignment.md` | This assignment file | Already provided |
| `submission/PROJECT_SUMMARY.md` | Your write-up (see template below) | Yes |
| `src/*.py` | Optional modular code | No |
| `tests/*.py` | Optional test files | No |

---

# Rubric

| Category | Points | What is assessed |
|----------|--------|-----------------|
| **Conversation & message ingestion** | 15 points | 3 tagged conversations + 8 tagged messages present; read/filter/sort/aggregate over them (Lab 1); full CRUD lifecycle (Lab 2) |
| **Memory extraction & upsert** | 15 points | `memories` populated; `upsert` dedup so re-runs don't duplicate; `$lookup` links each memory to its source conversation (Labs 2, 4) |
| **Recall & schema design** | 15 points | Embed-vs-reference decision documented (Lab 4); text index on `memories.text`; ranked search recall with `.explain()` showing index use (Labs 3, 4) |
| **Tool-call history & atomicity** | 15 points | 4 tagged tool calls logged; assistant-message + tool-call write is a multi-document transaction; change stream on `tool_calls` demonstrated (Labs 3, 5) |
| **Analytics** | 15 points | Aggregation pipelines: token usage per conversation, tool failure rate; an index + `.explain()` on a hot query (Labs 1, 3) |
| **Security & continuity** | 15 points | Replica set inspected + TLS verified (Lab 6); read-only reviewer role on `memories` only, verified; continuity: a memory recalled in a different conversation (Lab 6) |
| **Code quality** | 7 points | Tagged synthetic rows; child-first cleanup; no hardcoded credentials; single pinned pip install |
| **Documentation** | 3 points | Output section matches notebook; Mermaid diagrams present; PROJECT_SUMMARY.md submitted |

**Grading bands:**

| Band | Points | Description |
|------|--------|-------------|
| Distinction | 85-100 | All components working; documentation thorough; optional exercises attempted |
| Merit | 70-84 | All core components working; minor documentation gaps |
| Pass | 50-69 | Most components working; some bugs or missing features |
| Borderline | 40-49 | Partial implementation; significant gaps in one or more categories |
| Fail | 0-39 | Minimal or non-functional implementation |

> These bands describe the 100-point mandatory rubric above. The Optional section awards bonus points on top of it -- a perfect mandatory score plus every optional exercise tops out at 110.

---

# Success Criteria

Before submitting, confirm **every** item in this checklist. If any box is unchecked, you are not ready to submit.

- [ ] Notebook runs top-to-bottom with no errors (Kernel -> Restart & Run All)
- [ ] First code cell is the single pinned `!pip install` line
- [ ] `agent_memory` database has all four collections: conversations, messages, memories, tool_calls
- [ ] 3 conversations + 8 messages present, tagged `pytest-lab7-<hex>`
- [ ] 5 memories extracted and linked via `$lookup`; re-running produces 0 duplicates
- [ ] Text index on `memories.text` exists and recall returns a memory from a different conversation
- [ ] `.explain()` shows IXSCAN (index use) on recall and analytics hot queries
- [ ] 4 tool calls logged, mixing ok/not-ok outcomes
- [ ] Turn + tool-call write is a multi-document transaction; change stream observes a new document
- [ ] Token-usage and tool-failure aggregations print sensible results with an index
- [ ] Replica set inspected (`setName`, `hosts`) and TLS verified
- [ ] Reviewer role has `read` on `memories` only, verified by permissions query
- [ ] Cleanup deletes all tagged rows in child-first order and drops the reviewer role
- [ ] No hardcoded credentials in notebook
- [ ] PROJECT_SUMMARY.md submitted in `submission/` directory

---

# Submission Format

Your `submission/PROJECT_SUMMARY.md` must follow this template:

```markdown
# Project Summary: AI Agent Memory Service

## Author
[Your name]

## Date
[Submission date]

## Lab
Lab 7 - Capstone Project

## What I Built
[2-3 sentences describing your implementation]

## Verification Results

| Check | Status | Evidence |
|-------|--------|----------|
| Conversation & message ingestion | Pass/Fail | [counts, sample query result] |
| Memory extraction & upsert | Pass/Fail | [0 duplicates on re-run] |
| Recall across sessions | Pass/Fail | [recalled memory from another conversation] |
| Transaction + change stream | Pass/Fail | [turn + tool call committed together] |
| Index usage (.explain) | Pass/Fail | [IXSCAN output] |
| RBAC reviewer role | Pass/Fail | [permissions query result] |
| Cleanup | Pass/Fail | [collections empty, role dropped] |

## Optional Exercises Attempted
[List any optional exercises you completed]

## Challenges & Learnings
[2-3 sentences about what was hardest and what you learned]

## Time Spent
[Approximate hours over the 2-week period]
```

---

# Proposal Stage (Due: End of Week 1, Day 2)

Before writing any code, submit a brief proposal (can be a comment in your notebook or a separate file) answering:

1. **Which collections from Labs 1-6 already exist in your cluster?** (Run `db.getMongo().getDBNamesList()` or list databases in Atlas)
2. **What database name will you use?** (The service expects `agent_memory` -- confirm it does not collide with `school_db` from earlier labs)
3. **What is your synthetic data plan?** (How many conversations, messages per conversation, memories, tool calls; what token counts and tool outcomes)
4. **What is your cleanup strategy?** (How will you find and delete only your synthetic rows?)

This proposal is not graded for correctness -- it's a checkpoint to make sure you've started thinking before Week 1 ends.

---

# Resource Validation (Due: End of Week 1, Day 3)

By Day 3, your notebook should be able to:

- Connect to the cluster and print the replica-set name via `db.command("hello")`
- Confirm `agent_memory` exists and list its four collections
- Insert one tagged conversation + message and commit them

If you cannot do these three things by Day 3, raise a flag immediately. The most common blocker is a missing `.env` file or a wrong MONGODB_URI format.

---

# Milestone Check-ins

| Milestone | Due | What to have working |
|-----------|-----|---------------------|
| **M1: Foundation** | End of Week 1, Day 5 | 3 conversations + 8 messages ingested, tagged `pytest-lab7-` prefix; collections confirmed |
| **M2: Core Integration** | End of Week 2, Day 2 | 5 memories extracted with upsert + `$lookup`; text search recall with index; transaction + change stream working |
| **M3: Analytics & Security** | End of Week 2, Day 4 | Token/tool-failure aggregations with `.explain()`; replica set + TLS verified; reviewer role created and verified |
| **M4: Polish** | End of Week 2, Day 5 | Cleanup complete (child-first, role dropped); PROJECT_SUMMARY.md written; notebook runs cleanly top-to-bottom |

---

# Evaluation Criteria

Your work will be evaluated on:

1. **Correctness** -- Does the notebook run without errors? Do queries return expected results?
2. **Completeness** -- Are all 18 Mandatory items addressed?
3. **Integrity** -- Is the extraction truly deduplicated? Is the turn+tool-call write actually a transaction?
4. **Cleanliness** -- Is the cleanup complete? Are all tagged rows and the reviewer role removed?
5. **Documentation** -- Does the PROJECT_SUMMARY.md clearly explain what you built and how you verified it?

---

# FAQ

**Q: Can I use a different Python driver (e.g., motor)?**
A: Yes, as long as the notebook's first cell installs it with a pinned version and the connection uses `os.environ.get("MONGODB_URI")` with TLS.

**Q: What if my cluster already has data from Labs 1-6?**
A: That's expected and good. Your synthetic rows should be tagged so cleanup can remove them without touching the existing `school_db` data.

**Q: Can I put everything in one long notebook?**
A: Yes. The rubric evaluates what the notebook produces, not how many files it uses.

**Q: What if I can't connect to the database?**
A: Check your `.env` file format: `MONGODB_URI="mongodb+srv://..."` (with quotes). Check that your Atlas IP allow-list includes your current IP (the module README Section 8, Step 4). Run the Resource Validation check by Day 3.

**Q: Is the illustrative output in the .md file what I should get exactly?**
A: No. The output is illustrative. Your `_id` values, token counts, and exact aggregation numbers will differ. The structure should be similar.

---

# Resource Links

- **Lab 7 companion file:** `lab-agent-memory-service.md` (in this directory)
- **Labs 1-6 reference:** Same module directory
- **Atlas dashboard:** https://cloud.mongodb.com
- **MongoDB docs:** https://www.mongodb.com/docs/manual/
- **pymongo docs:** https://pymongo.readthedocs.io/en/stable/
