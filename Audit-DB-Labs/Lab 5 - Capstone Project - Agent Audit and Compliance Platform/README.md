# Lab 5: Capstone Project — Agent Audit and Compliance Platform

**Capstone (Advanced) | 2-Week Timeline | Requires Labs 1-4 completed**

An assignment spec — not a worked example — for a capstone that integrates Labs 1-4 into one Agent Audit & Compliance Platform, with a proposal stage, milestone check-ins, and a transparent 100-point rubric (+10 optional bonus).

## File Structure

```
Lab 5 - Capstone Project - Agent Audit and Compliance Platform/
├── lab-capstone-project.md              # 13-section brief (read this first)
├── lab-capstone-project-assignment.md   # Full evaluation framework
├── test_lab_capstone_project.py         # Grading harness
├── lab-capstone-project.ipynb           # YOUR NOTEBOOK — you build this
├── submission/
│   └── PROJECT_SUMMARY.md               # YOUR write-up — you build this
├── .env                                 # Reuse Labs 1-4's .env (not committed)
└── README.md                            # This file
```

The `.md`, `-assignment.md`, and test file are provided. Everything else — the notebook and your submission write-up — is what you build over the two weeks.

## What You Build

**Agent Audit & Compliance Platform** — a single pipeline that:

- Ingests agent runs as an append-only event log (Lab 1)
- Organizes them into a queryable run/span/tool_call/guardrail_event hierarchy (Lab 2)
- Produces cross-run compliance reports via JOINs, aggregation, and window functions (Lab 3)
- Guarantees the log is tamper-evident via hash chains, and restricts auditor access via RBAC (Lab 4)

Integrates every concept from Labs 1-4:

| Lab | Integration |
|-----|-------------|
| Lab 1 | Append-only event ingestion |
| Lab 2 | run/span/tool_call/guardrail_event hierarchy — FKs, CHECK constraints, indexes |
| Lab 3 | Cross-run JOINs, GROUP BY aggregation, window-function ranking, EXPLAIN ANALYZE |
| Lab 4 | v_audit_trail view, append-only trigger, hash chain, auditor RBAC role |

## Evaluation Framework (2-Week Timeline)

**Week 1: Proposal & Planning**
- Days 1-2: Submit your proposal (tables already in your Supabase project, your tag prefix, synthetic data plan, cleanup strategy — see the assignment file's Proposal Stage section)
- Day 3: Resource validation — connect, confirm the five Lab 1-2 tables exist, insert and commit one synthetic run

**Week 2: Implementation & Evaluation**
- Day 5 (M1 — Foundation): all 3 synthetic runs ingested with full hierarchy, tagged `pytest-lab5-<hex>`
- Week 2, Day 2 (M2 — Core Integration): `v_audit_trail` view created; append-only trigger working; hash chain built and verified
- Week 2, Day 4 (M3 — Compliance Layer): tamper detection demonstrated; auditor role created and verified; EXPLAIN ANALYZE shows index usage
- Week 2, Day 5 (M4 — Polish): cleanup complete; PROJECT_SUMMARY.md written; notebook runs cleanly top-to-bottom

## Grading Rubric at a Glance

| Category | Points |
|----------|--------|
| Hierarchy integrity | 15 |
| Cross-run reporting correctness | 20 |
| Hash-chain / tamper-detection correctness | 20 |
| RBAC correctness | 15 |
| Compliance-log completeness | 10 |
| Code quality | 10 |
| Documentation | 10 |
| **Mandatory total** | **100** |
| Optional exercises (bonus, on top of the 100) | up to +10 |

**Passing:** ≥50 · **Distinction:** ≥85 (full rubric and bands in the assignment file)

## How to Start

1. **Read `lab-capstone-project.md` in full** — start to finish, it's your reference, not a script to copy.
2. **Submit your proposal** — answer the 4 questions in the assignment file's Proposal Stage section.
3. **Run resource validation** — connect, confirm the five Lab 1-2 tables exist, insert and commit one synthetic run.
4. **Build `lab-capstone-project.ipynb`** — first cell must be exactly:
   ```
   !pip install python-dotenv==1.2.3 psycopg2-binary==2.9.12
   ```
5. **Work through the six processing phases**: schema verification → data ingestion → audit layer (view + trigger + hash chain) → compliance report (via the view) → integrity verification (hash chain + tamper detection) → RBAC exercise.
6. **Run the test suite:**
   ```
   python3 -m pytest test_lab_capstone_project.py -v
   ```
7. **Write `submission/PROJECT_SUMMARY.md`** using the template in the assignment file.
8. **Submit** per the Deliverables table in the assignment file.

## Mandatory Features (≥50 to pass)

See the assignment file's Mandatory table for the full 15-item list. In short:

- ✅ Full Lab 1-2 hierarchy tagged and populated (`pytest-lab5-<hex>`)
- ✅ `v_audit_trail` view with an append-only trigger on `event`
- ✅ Hash chain: 0 content breaks, 0 linkage breaks; tamper detected after a simulated privileged bypass
- ✅ Auditor role with SELECT on the view only — no INSERT on base tables
- ✅ Cross-run compliance report: failure rates, cost analysis, window-function ranking, EXPLAIN ANALYZE
- ✅ Full cleanup (SAVEPOINT-guarded, child-before-parent); no hardcoded credentials

## Optional Extensions (bonus, up to +10)

- **+5** — A second, more restricted auditor role (`lab5_guardrail_reader`) scoped to `guardrail_event` only
- **+3** — A "Cost by guardrail outcome" report section
- **+2** — A standalone Compliance Checklist document in `submission/`

## Success Criteria

The full checklist lives in `lab-capstone-project-assignment.md` under Success Criteria — every box must be checked before you submit.

## Resources

- **In this folder:** `lab-capstone-project.md` (read first), `lab-capstone-project-assignment.md` (evaluation framework), `test_lab_capstone_project.py`
- **Reference:** Labs 1-4 in this module
- **External:** Supabase dashboard, PostgreSQL docs, psycopg2 docs — links in the assignment file's Resource Links section

## Tips for Success

- **Start with the proposal** — a wrong assumption about which tables/tags already exist costs hours later.
- **Test early, test often** — run the test suite after each phase, not just at the end.
- **Tag before you insert** — every synthetic row needs its `pytest-lab5-<hex>` marker from the moment it's created, not added afterward.
- **Reuse, don't copy** — this capstone is about composing Labs 1-4, not repeating their code.
- **Cleanup order matters** — child objects before parent objects, SAVEPOINT-guarded, so one failed drop doesn't roll back earlier successes.