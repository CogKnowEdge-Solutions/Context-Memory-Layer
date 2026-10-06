# Lab 7: Capstone Project — AI Agent Memory Service

**Capstone (Advanced) | 2-Week Timeline | Requires Labs 1-6 completed**

A documented-only capstone — not a worked example — for the storage/memory layer of an AI agent harness. This is where the whole MongoDB module's end goal lands: the same MongoDB skills from Labs 1-6, applied to logging conversations, storing and recalling long-term memories, and reviewing tool-call history across sessions. It ships a brief, an assignment, and a grading harness; the notebook itself is what you build.

## Overview

An agent harness needs memory: it must remember earlier turns, facts a user told it weeks ago, and the tool calls it has already made. This capstone combines Labs 1-6 into one **AI Agent Memory Service** running in an `agent_memory` database on the same M0 Atlas cluster — with a proposal stage, milestone check-ins, and a transparent 100-point rubric (+10 optional bonus).

## File Structure

```
Lab 7 - AI Agent Memory Service/
├── lab-agent-memory-service.md              # 13-section capstone brief (read this first)
├── lab-agent-memory-service-assignment.md   # Full evaluation framework
├── test_lab_agent_memory_service.py         # Grading harness
├── lab-agent-memory-service.ipynb           # YOUR NOTEBOOK — you build this
├── submission/
│   └── PROJECT_SUMMARY.md                   # YOUR write-up — you build this
├── .env                                     # your MONGODB_URI .env, kept inside this module, never committed
└── README.md                                # This file
```

The `.md`, `-assignment.md`, and test file are provided. Everything else — the notebook and your submission write-up — is what you build over the two weeks.

## What You Build

**AI Agent Memory Service** — a storage layer that:

- **Logs each turn** — conversations and messages in `agent_memory` (Labs 1-2)
- **Stores and recalls long-term memories** — a `memories` collection with upsert dedup, `$lookup`, and text-search recall (Labs 2-4)
- **Reviews tool-call history** — a `tool_calls` collection written atomically with the turn that triggered it (Labs 3, 5)
- **Keeps it fast and safe** — indexes with `.explain()`, a read-only reviewer role, TLS, and a replica-set inspection (Labs 3, 6)

Integrates every concept from Labs 1-6:

| Lab | Integration |
|-----|-------------|
| Lab 1 | Connect, insert, filter, sort, and aggregate the conversations/messages collections |
| Lab 2 | Full CRUD on the four collections; `upsert` dedup so memory extraction never duplicates a fact |
| Lab 3 | Aggregation pipelines (token usage, tool-failure rate); indexes + `.explain()` on recall and analytics hot paths |
| Lab 4 | Schema design (embed vs. reference), `$lookup` linking memories to conversations, text-search recall |
| Lab 5 | Multi-document transaction committing a turn + its tool call together; change stream on `tool_calls` |
| Lab 6 | Replica-set inspection, TLS verification, and a read-only reviewer role on `memories` only (RBAC) |

## Evaluation Framework (2-Week Timeline)

**Week 1: Proposal & Planning**
- Days 1-2: Submit your proposal (existing collections, database name, synthetic data plan, cleanup strategy — see the assignment file's Proposal Stage section)
- Day 3: Resource validation — connect, confirm `agent_memory` and its four collections, insert and commit one tagged conversation + message

**Week 2: Implementation & Evaluation**
- End of Week 1, Day 5 (M1 — Foundation): 3 conversations + 8 messages ingested, tagged `pytest-lab7-<hex>`
- Week 2, Day 2 (M2 — Core Integration): 5 memories extracted with upsert + `$lookup`; text-search recall with index; transaction + change stream working
- Week 2, Day 4 (M3 — Analytics & Security): token/tool-failure aggregations with `.explain()`; replica set + TLS verified; reviewer role created and verified
- Week 2, Day 5 (M4 — Polish): cleanup complete; PROJECT_SUMMARY.md written; notebook runs cleanly top-to-bottom

## Grading Rubric at a Glance

| Category | Points |
|----------|--------|
| Conversation & message ingestion | 15 |
| Memory extraction & upsert | 15 |
| Recall & schema design | 15 |
| Tool-call history & atomicity | 15 |
| Analytics | 15 |
| Security & continuity | 15 |
| Code quality | 7 |
| Documentation | 3 |
| **Mandatory total** | **100** |
| Optional exercises (bonus, on top of the 100) | up to +10 |

**Passing:** ≥50 · **Distinction:** ≥85 (full rubric and bands in the assignment file)

## How to Start

1. **Read `lab-agent-memory-service.md` in full** — start to finish, it's your reference, not a script to copy.
2. **Submit your proposal** — answer the 4 questions in the assignment file's Proposal Stage section.
3. **Run resource validation** — connect, confirm `agent_memory` and its four collections, insert and commit one tagged conversation + message.
4. **Build `lab-agent-memory-service.ipynb`** — first cell must be exactly:
   ```
   !pip install -qU "pymongo[srv,tls]==4.10.1" python-dotenv==1.0.1 certifi
   ```
5. **Work through the seven processing phases**: schema design → conversation ingestion → memory extraction & upsert → recall → tool-call history & atomicity → analytics → security & continuity.
6. **Run the test suite:**
   ```
   python -m pytest test_lab_agent_memory_service.py -v
   ```
7. **Write `submission/PROJECT_SUMMARY.md`** using the template in the assignment file.
8. **Submit** per the Deliverables table in the assignment file.

## Mandatory Features (≥50 to pass)

See the assignment file's Mandatory table for the full 18-item list. In short:

- ✅ Four `agent_memory` collections with a documented embed-vs-reference schema (Lab 4)
- ✅ 3 conversations + 8 messages tagged and populated (`pytest-lab7-<hex>`)
- ✅ 5 memories extracted with `upsert` dedup + `$lookup`; text-search recall across sessions
- ✅ 4 tool calls committed atomically with their turns (transaction) + a change stream
- ✅ Token-usage and tool-failure aggregations with an index and `.explain()`
- ✅ Replica-set inspection + TLS verified; read-only reviewer role on `memories` only
- ✅ Full child-first cleanup; no hardcoded credentials

## Optional Extensions (bonus, up to +10)

- **+5** — Per-agent memory filter: compound index on `{agent: 1, source_conversation_id: 1}` returning only the current agent's memories
- **+3** — A "token cost by conversation" aggregation report with `$group` + `$sort`
- **+2** — A standalone Memory Service Checklist document in `submission/`

## Success Criteria

The full checklist lives in `lab-agent-memory-service-assignment.md` under Success Criteria — every box must be checked before you submit.

## Resources

- **In this folder:** `lab-agent-memory-service.md` (read first), `lab-agent-memory-service-assignment.md` (evaluation framework), `test_lab_agent_memory_service.py`
- **Reference:** Labs 1-6 in this module
- **External:** Atlas dashboard, MongoDB docs, pymongo docs — links in the assignment file's Resource Links section

## Tips for Success

- **Start with the proposal** — a wrong assumption about `school_db` still holding earlier data, or which collections already exist, costs hours later.
- **Test early, test often** — run the test suite after each phase, not just at the end.
- **Tag before you insert** — every synthetic document needs its `pytest-lab7-<hex>` marker from the moment it's created, not added afterward.
- **Reuse, don't copy** — this capstone is about composing Labs 1-6, not repeating their code.
- **Cleanup order matters** — child collections (`tool_calls`, `messages`) before parent `conversations`, reviewer role dropped last, so one failed delete never leaves stragglers.
