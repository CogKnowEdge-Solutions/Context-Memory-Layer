# CareMatch API — Project Summary

**Status: Prototype complete through Phase 5 (simulated). Phases 6-7 require real-world adoption, not more code.**

This document is the single narrative summary of the whole project — what it is, what got built, what actually broke and got fixed, and what the real, honest results are. Everything described here was actually run and verified, not just written and assumed to work.

---

## The Problem

Hospitals running clinical trials have to check whether each patient qualifies, against a checklist of rules (inclusion/exclusion criteria). This is done by hand today, by a **research coordinator** reading through medical records — slow, and easy to miss something in a long chart.

Two things make AI adoption in this space hard in practice:
- **Cost** — typical enterprise AI integrations run \$250K–\$500K per hospital
- **Trust** — a black-box "yes/no" verdict is unusable in a clinical/legal setting with no way to check it

## The Idea

CareMatch is a lightweight reasoning layer, not a black box. It never gives a flat yes/no — every result is a structured, per-rule breakdown with a direct quote from the patient record as evidence, and a human coordinator always makes the final call.

```json
{
  "suggested_status": "likely_eligible",
  "requires_coordinator_approval": true,
  "rule_results": [
    {"rule_id": "INC-01", "status": "matches", "evidence": "60-year-old patient"}
  ]
}
```

---

## What Got Built

| Layer | What It Is | Status |
|---|---|---|
| **Reasoning engine** | Python core that walks a trial's rules one at a time against a patient record, calling an LLM per rule | ✅ Built, tested with a real LLM |
| **API** | FastAPI doorway — register trials, run assessments, record coordinator decisions | ✅ Built, 13/13 tests passing |
| **Dashboard** | React/TanStack Start UI — New Assessment, Assessment Review, Trial Setup | ✅ Built, wired to the real API, browser-tested |
| **Docker** | All services containerized, one `docker-compose up` starts everything | ✅ 4 containers running together |
| **Observability** | Prometheus + Grafana, built into the real API (not a separate toy service) | ✅ Real metrics, real dashboard |

## Architecture

```
Coordinator (browser)
        │
        ▼
   Dashboard (React / TanStack Start)
        │  HTTP
        ▼
   API (FastAPI) ──────────► Prometheus ──► Grafana
        │
        ▼
   Reasoning Engine (Python)
        │  one call per rule
        ▼
   LLM (Anthropic Claude Haiku, via OpenRouter or direct)
```

---

## Real Bugs Found and Fixed

This is the part that matters most — not that bugs happened, but that they were found *before* this touched anything real, and each one is now backed by a regression test.

### 1. Negated exclusion phrasing confused the model
**Found:** Exclusion rules phrased as "Patient must **not** be taking Warfarin" caused the model to answer `does_not_match` almost regardless of the actual facts — a double-negative it consistently got wrong.
**Fixed:** Rephrased exclusion criteria as plain, positive disqualifying statements ("Patient is currently taking Warfarin"), and made the prompt explicitly state what a match means per rule category.
**Verified:** Re-tested in a later 12-patient batch — every Warfarin check across all patients came back correctly polarized.

### 2. Overconfident inference from absence
**Found:** Given "no diabetes screening on file," the model confidently answered "does not have diabetes" — inferring a negative from an absence, rather than flagging genuine uncertainty.
**Fixed:** Explicit prompt instruction: prefer `unclear` over an inferred answer whenever the record doesn't state something directly.
**Verified:** A later test specifically contrasted "no history of diabetes" (correctly confident) against "no diabetes screening on file" (correctly unclear) — both handled correctly.

### 3. Malformed LLM output could crash an entire assessment
**Found:** If the LLM returned an invalid status value or a missing field, the whole assessment would crash instead of failing gracefully.
**Fixed:** Wrapped rule evaluation in validation with a safe fallback to `unclear` — one bad rule result can no longer take down the whole assessment.
**Verified:** 4 dedicated tests, including proof that one malformed rule doesn't affect other valid rules in the same assessment.

### 4. Metrics double-counted, wrong model naming, confidence field crept back in
**Found during code review of an early, larger alternative codebase** that was ultimately set aside — a metric was incremented twice per event, status field naming drifted from the locked schema, and a "confidence score" had been reintroduced despite that being explicitly ruled out in planning.
**Action:** That codebase was not used. Confirms the value of the Phase 0 planning discipline — these were real, working-code mistakes that planning decisions were specifically designed to prevent.

### 5. Docker port conflict silently routed traffic to the wrong container
**Found:** An old, unrelated container from early Prometheus/Grafana testing was still running on the same port as the real API. Windows resolved `localhost` to the old container first, causing real requests to silently hit the wrong server and return a misleading 404.
**Fixed:** Retired the old standalone container entirely; observability is now built into the real API, in the same Docker Compose stack — structurally impossible for this exact conflict to recur.

---

## Harness Hardening

Beyond the core reasoning loop, four additional safety layers were built in, addressing gaps identified during initial planning:

1. **Malformed output handling** — see bug #3 above
2. **Prompt injection defense** — patient records are wrapped in explicit data-only delimiters, with instructions to never treat their contents as commands. *(Honestly documented as a real mitigation, not a guarantee — full adversarial testing would need a dedicated red-team exercise.)*
3. **Token usage visibility** — every real LLM call logs its token cost and a running session total
4. **Model/provider traceability** — every assessment records exactly which AI model produced it

**Deliberately not built, and why:** bias/fairness auditing (needs real-world pilot data to be meaningful), model version pinning with rollback (an operational concern for real deployment, not a prototype), formal cost budget caps (visibility came first).

---

## Evaluation Results (Simulated Phase 5)

A real hospital pilot wasn't available for this project, so a substitute evaluation was run instead: 12 synthetic patients, each with a human-decided correct answer, run through the real system end-to-end (real Anthropic Claude Haiku calls, not mocked).

**Result: 12/12 correct (100% agreement), 0 false exclusions.**

The batch was deliberately designed to re-test the two reasoning bugs above, plus:
- **Boundary conditions**: a patient exactly at the age cutoff (correctly eligible) vs. one year under (correctly excluded)
- **Multi-failure cases**: a patient failing three rules simultaneously — all three correctly identified, not just the first one noticed
- **Distractor information**: an unrelated allergy noted in the record, correctly ignored

**Honest limits of this result:** 12 cases is a real signal, not statistical proof — a larger batch (30-50+) would be more robust. One trial with three simple rules is far simpler than a real trial's typical 10+ criteria. This was synthetic, clean data — real clinical notes are messier and more inconsistent.

---

## What's Genuinely Left (Not Code)

| Phase | What It Actually Requires |
|---|---|
| **6 — Compliance** | Real legal review (HIPAA), a real third-party security audit |
| **7 — Scale** | Real hospital customers, a business model, a larger trial-protocol library built from real demand |

Both of these need an actual organization adopting this system — they are not things more engineering time can produce on their own.

---

## Repository Structure

```
carematch/
├── reasoning_engine/    Phase 1 — core AI reasoning logic
├── api/                 Phase 2 — FastAPI doorway + Prometheus metrics
├── dashboard/           Phase 3 — React/TanStack Start coordinator UI
├── docs/                This file, and original Phase 0 planning documents
├── docker-compose.yml   Runs the full stack: api, dashboard, prometheus, grafana
└── README.md            Living technical status, updated throughout the build
```

---

*This document reflects the project's actual, verified state as of the end of active development. Every claim above was tested and confirmed running — not assumed.*