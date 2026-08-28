# Lab 8: Capstone Project -- Agent Audit and Compliance Platform

## Assignment Brief (2 Weeks)

---

# Objective Sheet

This is the final lab in the Audit DB Labs module. You will build, from scratch, an **Agent Audit & Compliance Platform** that integrates everything from Labs 1-7 into a single, auditable pipeline.

**What you are building:** A notebook (`lab-capstone-project.ipynb`) that ingests agent runs with full hierarchy (Labs 1-2), produces cross-run compliance reports through an auditor-facing view (Lab 3), guarantees tamper detection via hash chains (Lab 7), and verifies RBAC through a read-only auditor role (Lab 7).

**What you are NOT building:** This is not a take-home exam with hidden test cases. The rubric is fully transparent below. Every requirement is listed. There are no trick questions.

**The companion file (`lab-capstone-project.md`) is your reference**, not a script to copy-paste. It describes what a correct implementation looks like with illustrative output. Your actual output will differ in run ids, event ids, and hash values.

---

# Mandatory

All of the following **must** be present in your submission. Missing any one means you lose the associated points.

| # | Requirement | Where to verify |
|---|-------------|----------------|
| 1 | Notebook first code cell is `!pip install python-dotenv==1.2.3 psycopg2-binary==2.9.12` (single line only) | Notebook cell 1 |
| 2 | All five Lab 1-2 tables exist and are populated: run, event, span, tool_call, guardrail_event | Schema check query |
| 3 | Foreign key constraints enforced (span.run_id -> run.run_id, etc.) | `information_schema.table_constraints` query |
| 4 | CHECK constraint on guardrail_event.outcome (pass/fail/warn) | `information_schema.check_constraints` query |
| 5 | Synthetic runs tagged with `pytest-lab5-<hex>` prefix in agent_name | SELECT query on run table |
| 6 | `v_audit_trail` view created (4-table LEFT JOIN) | View exists check |
| 7 | Append-only trigger on event (BEFORE UPDATE/DELETE raises exception) | Trigger test (UPDATE should fail) |
| 8 | Hash chain table exists with row_hash and prev_hash columns | Schema check query |
| 9 | Hash chain built for all events: 0 content breaks, 0 linkage breaks | Chain verification query |
| 10 | Tamper detection: privileged bypass (drop trigger -> tamper -> recreate) detected by chain | Tamper test sequence |
| 11 | Auditor role created with SELECT on v_audit_trail only | `information_schema.role_table_grants` query |
| 12 | Cross-run compliance report: failure rates per agent, cost analysis, window-function ranking | Report output |
| 13 | EXPLAIN ANALYZE shows index usage on JOINs | EXPLAIN output |
| 14 | Cleanup: all triggers, view, hash chain table, auditor role, and tagged rows dropped/deleted | Final verification query |
| 15 | No hardcoded credentials in notebook (DATABASE_URL loaded from .env) | Grep for postgres:// |

---

# Optional

These are **not required for a Pass** but improve your grade. Attempt them after completing all Mandatory items.

| # | Exercise | Points | Notes |
|---|----------|--------|-------|
| 1 | Create a second auditor role `lab5_guardrail_reader` with SELECT on guardrail_event only | +5 | Verify via information_schema |
| 2 | Add a "Cost by guardrail outcome" report section (do guardrail failures cost more?) | +3 | GROUP BY guardrail_event.outcome |
| 3 | Write a one-page "Compliance Checklist" document (Appendix A format) and include it in submission/ | +2 | Maps each requirement to verification method |

---

# Deliverables

Submit the following files:

| File | What it is | Mandatory? |
|------|-----------|-----------|
| `lab-capstone-project.ipynb` | Your notebook (the main graded artifact) | Yes |
| `lab-capstone-project.md` | Reference companion (from module materials) | Already provided |
| `lab-capstone-project-assignment.md` | This assignment file | Already provided |
| `submission/PROJECT_SUMMARY.md` | Your write-up (see template below) | Yes |
| `src/*.py` | Optional modular code | No |
| `tests/*.py` | Optional test files | No |

---

# Rubric

| Category | Points | What is assessed |
|----------|--------|-----------------|
| **Hierarchy integrity** | 15 points | All 5 tables present; FK constraints enforced; CHECK constraints on guardrail_event.outcome |
| **Cross-run reporting correctness** | 20 points | JOIN queries through v_audit_trail; GROUP BY aggregation; window-function ranking; EXPLAIN ANALYZE shows index usage |
| **Hash-chain / tamper-detection correctness** | 20 points | Chain built for all events; 0 content + 0 linkage breaks; tamper detected after privileged bypass; chain restored to clean |
| **RBAC correctness** | 15 points | Auditor role created; SELECT on v_audit_trail verified; no INSERT on base tables; role cleaned up |
| **Compliance-log completeness** | 10 points | All 3 runs ingested with full hierarchy; events span multiple event_types; guardrail outcomes cover pass, fail, warn |
| **Code quality** | 10 points | SAVEPOINT-guarded cleanup; child-first deletes; tagged rows; no hardcoded credentials; single pinned pip install |
| **Documentation** | 10 points | Output section matches notebook; Mermaid diagrams present; Appendix A and B present; PROJECT_SUMMARY.md submitted |

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
- [ ] All five Lab 1-2 tables have synthetic data tagged with `pytest-lab5-<hex>`
- [ ] `v_audit_trail` view returns rows (SELECT * FROM v_audit_trail LIMIT 5 works)
- [ ] Append-only trigger fires on UPDATE (raises exception)
- [ ] Hash chain has 0 content breaks and 0 linkage breaks
- [ ] Tamper detection catches privileged bypass (drop trigger -> tamper -> recreate)
- [ ] Auditor role exists with SELECT on v_audit_trail only
- [ ] Compliance report prints failure rates, cost analysis, and window-function ranking
- [ ] EXPLAIN ANALYZE shows index usage (not Seq Scan)
- [ ] Cleanup drops all objects and deletes all tagged rows
- [ ] No hardcoded credentials in notebook
- [ ] PROJECT_SUMMARY.md submitted in submission/ directory

---

# Submission Format

Your `submission/PROJECT_SUMMARY.md` must follow this template:

```markdown
# Project Summary: Agent Audit and Compliance Platform

## Author
[Your name]

## Date
[Submission date]

## Lab
Lab 8 - Capstone Project

## What I Built
[2-3 sentences describing your implementation]

## Verification Results

| Check | Status | Evidence |
|-------|--------|----------|
| Hierarchy integrity | Pass/Fail | [query result or screenshot] |
| Hash chain integrity | Pass/Fail | [0 breaks across N links] |
| Tamper detection | Pass/Fail | [chain detected tamper after bypass] |
| RBAC | Pass/Fail | [information_schema query result] |
| Cleanup | Pass/Fail | [objects dropped, rows deleted] |

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

1. **Which tables from Labs 1-2 already exist in your Supabase project?** (Run `\dt public.*` in psql or check `information_schema.tables`)
2. **What agent names have you already used?** (So you can choose a non-colliding tag)
3. **What is your synthetic data plan?** (How many runs, how many spans per run, what guardrail outcomes)
4. **What is your cleanup strategy?** (How will you find and delete only your synthetic rows?)

This proposal is not graded for correctness -- it's a checkpoint to make sure you've started thinking before Week 1 ends.

---

# Resource Validation (Due: End of Week 1, Day 3)

By Day 3, your notebook should be able to:

- Connect to the database and print the PostgreSQL version
- Query `information_schema.tables` and confirm all five Lab 1-2 tables exist
- Insert one synthetic run with the full hierarchy and commit it

If you cannot do these three things by Day 3, raise a flag immediately. The most common blocker is a missing `.env` file or wrong DATABASE_URL format.

---

# Milestone Check-ins

| Milestone | Due | What to have working |
|-----------|-----|---------------------|
| **M1: Foundation** | End of Week 1, Day 5 | All 3 synthetic runs ingested with full hierarchy; tagged with pytest-lab5- prefix |
| **M2: Core Integration** | End of Week 2, Day 2 | v_audit_trail view created; append-only trigger working; hash chain built and verified |
| **M3: Compliance Layer** | End of Week 2, Day 4 | Tamper detection demonstrated; auditor role created and verified; EXPLAIN ANALYZE shows indexes |
| **M4: Polish** | End of Week 2, Day 5 | Cleanup complete; PROJECT_SUMMARY.md written; notebook runs cleanly top-to-bottom |

---

# Evaluation Criteria

Your work will be evaluated on:

1. **Correctness** -- Does the notebook run without errors? Do queries return expected results?
2. **Completeness** -- Are all 15 Mandatory items addressed?
3. **Integrity** -- Is the hash chain actually verified? Is the trigger actually append-only?
4. **Cleanliness** -- Is the cleanup complete? Are all objects and tagged rows removed?
5. **Documentation** -- Does the PROJECT_SUMMARY.md clearly explain what you built and how you verified it?

---

# FAQ

**Q: Can I use a different database driver (e.g., SQLAlchemy)?**
A: Yes, as long as the notebook's first cell installs it with a pinned version and the connection uses `os.getenv("DATABASE_URL")`.

**Q: What if my Supabase project already has data from Labs 1-7?**
A: That's expected and good. Your synthetic rows should be tagged so cleanup can remove them without touching the existing data.

**Q: Can I put everything in one long notebook?**
A: Yes. The rubric evaluates what the notebook produces, not how many files it uses.

**Q: What if I can't connect to the database?**
A: Check your `.env` file format: `DATABASE_URL="postgresql://..."` (with quotes). Check that your Supabase project isn't paused (free tier pauses after inactivity). Run the Resource Validation check by Day 3.

**Q: Is the illustrative output in the .md file what I should get exactly?**
A: No. The output is illustrative. Your run ids, event ids, hash values, and exact numbers will differ. The structure should be similar.

---

# Resource Links

- **Lab 8 companion file:** `lab-capstone-project.md` (in this directory)
- **Labs 1-7 reference:** Same module directory
- **Supabase dashboard:** https://supabase.com/dashboard
- **PostgreSQL docs:** https://www.postgresql.org/docs/17/
- **psycopg2 docs:** https://www.psycopg.org/docs/