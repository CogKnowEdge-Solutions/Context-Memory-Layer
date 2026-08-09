"""
Tests the API's HTTP layer: routing, validation, trial registration/lookup,
and error handling. Forces LLM_MODE=fake so these never cost anything or
touch the network -- they prove the plumbing works, not reasoning quality
(that's Phase 1's job, already proven separately).

Also: since the API now persists to SQLite, tests run against a throwaway
temp DB (never the real one), and one test proves the data really lands on
disk by re-opening the file with a brand-new connection -- the storage-layer
half of the "survives a hard kill" proof.
"""

import os
import tempfile

os.environ["LLM_MODE"] = "fake"
os.environ["CAREMATCH_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "carematch-test.db")

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

client = TestClient(app)


def test_list_trials_returns_all_registered_trials():
    client.post(
        "/trials",
        json={
            "trial_id": "T-LIST-A",
            "trial_name": "List Test A",
            "rules": [{"rule_id": "INC-01", "rule_text": "test", "category": "inclusion"}],
        },
    )
    client.post(
        "/trials",
        json={
            "trial_id": "T-LIST-B",
            "trial_name": "List Test B",
            "rules": [{"rule_id": "INC-01", "rule_text": "test", "category": "inclusion"}],
        },
    )
    r = client.get("/trials")
    assert r.status_code == 200
    trial_ids = [t["trial_id"] for t in r.json()]
    assert "T-LIST-A" in trial_ids
    assert "T-LIST-B" in trial_ids


def test_assess_records_which_provider_and_model_were_used():
    """Harness traceability: every assessment must record exactly which
    model produced it, not leave that implicit or guessable."""
    client.post(
        "/trials",
        json={
            "trial_id": "T-TRACE-TEST",
            "trial_name": "Traceability Test",
            "rules": [{"rule_id": "INC-01", "rule_text": "test rule", "category": "inclusion"}],
        },
    )
    r = client.post(
        "/assess",
        json={"trial_id": "T-TRACE-TEST", "patient_id": "P-1", "patient_record": "record"},
    )
    data = r.json()
    # LLM_MODE=fake for this whole test file, so we expect the fake markers
    assert data["provider_used"] == "fake"
    assert data["model_used"] == "fake-mode-no-llm-call"


def test_metrics_endpoint_exposes_carematch_specific_metrics():
    """Phase 4, done properly this time: metrics live in the real API,
    not a separate toy service. Prove our custom metrics actually appear,
    not just the generic auto-instrumented HTTP ones."""
    client.post(
        "/trials",
        json={
            "trial_id": "T-METRICS-TEST",
            "trial_name": "Metrics Test",
            "rules": [{"rule_id": "INC-01", "rule_text": "test rule", "category": "inclusion"}],
        },
    )
    assess_resp = client.post(
        "/assess",
        json={"trial_id": "T-METRICS-TEST", "patient_id": "P-1", "patient_record": "record"},
    )
    assessment_id = assess_resp.json()["assessment_id"]
    client.post(f"/assessments/{assessment_id}/decision", json={"decision": "approved"})

    metrics_text = client.get("/metrics").text
    assert "trials_registered_total" in metrics_text
    assert "assessments_total" in metrics_text
    assert "reasoning_duration_seconds" in metrics_text
    assert "coordinator_decisions_total" in metrics_text
    # Confirm the label values we expect actually show up, not just the metric names
    assert 'suggested_status="needs_more_info"' in metrics_text  # fake mode always returns this
    assert 'decision="approved"' in metrics_text


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_register_and_fetch_trial():
    r = client.post(
        "/trials",
        json={
            "trial_id": "T-TEST-01",
            "trial_name": "Test Trial",
            "rules": [
                {"rule_id": "INC-01", "rule_text": "Patient must be 18 or older", "category": "inclusion"}
            ],
        },
    )
    assert r.status_code == 201
    assert r.json()["trial_id"] == "T-TEST-01"

    r2 = client.get("/trials/T-TEST-01")
    assert r2.status_code == 200
    assert r2.json()["trial_name"] == "Test Trial"


def test_get_unknown_trial_returns_404():
    r = client.get("/trials/DOES-NOT-EXIST")
    assert r.status_code == 404


def test_assess_unknown_trial_returns_404():
    r = client.post(
        "/assess",
        json={"trial_id": "DOES-NOT-EXIST", "patient_id": "P-1", "patient_record": "some record"},
    )
    assert r.status_code == 404


def test_assess_with_fake_llm_returns_correct_schema():
    client.post(
        "/trials",
        json={
            "trial_id": "T-ASSESS-TEST",
            "trial_name": "Assess Test Trial",
            "rules": [
                {"rule_id": "INC-01", "rule_text": "Patient must be 18 or older", "category": "inclusion"},
                {"rule_id": "EXC-01", "rule_text": "Patient is taking Warfarin", "category": "exclusion"},
            ],
        },
    )
    r = client.post(
        "/assess",
        json={"trial_id": "T-ASSESS-TEST", "patient_id": "P-1", "patient_record": "some fake record"},
    )
    assert r.status_code == 201
    data = r.json()

    # /assess now returns an AssessmentRecord wrapping the AssessmentResult
    assert "assessment_id" in data
    assert data["decision"] is None  # never pre-decided, ever
    assessment = data["assessment"]

    # Fake LLM always says "unclear" -> aggregation must produce needs_more_info
    assert assessment["suggested_status"] == "needs_more_info"
    assert assessment["requires_coordinator_approval"] is True
    assert len(assessment["rule_results"]) == 2

    # Phase 0 rule enforced end-to-end, through the actual HTTP layer this time
    assert "confidence" not in assessment
    for rule_result in assessment["rule_results"]:
        assert "confidence" not in rule_result


def test_get_assessment_by_id():
    client.post(
        "/trials",
        json={
            "trial_id": "T-GET-TEST",
            "trial_name": "Get Test Trial",
            "rules": [{"rule_id": "INC-01", "rule_text": "test rule", "category": "inclusion"}],
        },
    )
    create_resp = client.post(
        "/assess",
        json={"trial_id": "T-GET-TEST", "patient_id": "P-1", "patient_record": "record"},
    )
    assessment_id = create_resp.json()["assessment_id"]

    r = client.get(f"/assessments/{assessment_id}")
    assert r.status_code == 200
    assert r.json()["assessment_id"] == assessment_id


def test_get_unknown_assessment_returns_404():
    r = client.get("/assessments/does-not-exist")
    assert r.status_code == 404


def test_recording_a_decision_updates_the_assessment():
    client.post(
        "/trials",
        json={
            "trial_id": "T-DECISION-TEST",
            "trial_name": "Decision Test Trial",
            "rules": [{"rule_id": "INC-01", "rule_text": "test rule", "category": "inclusion"}],
        },
    )
    create_resp = client.post(
        "/assess",
        json={"trial_id": "T-DECISION-TEST", "patient_id": "P-1", "patient_record": "record"},
    )
    assessment_id = create_resp.json()["assessment_id"]
    assert create_resp.json()["decision"] is None  # confirm it starts undecided

    decision_resp = client.post(
        f"/assessments/{assessment_id}/decision",
        json={"decision": "overridden", "reason": "Coordinator saw additional labs not in the record"},
    )
    assert decision_resp.status_code == 200
    data = decision_resp.json()
    assert data["decision"] == "overridden"
    assert data["decision_reason"] == "Coordinator saw additional labs not in the record"

    # Confirm it actually persisted, not just echoed back in the response
    fetch_resp = client.get(f"/assessments/{assessment_id}")
    assert fetch_resp.json()["decision"] == "overridden"


def test_recording_decision_on_unknown_assessment_returns_404():
    r = client.post(
        "/assessments/does-not-exist/decision",
        json={"decision": "approved"},
    )
    assert r.status_code == 404


def test_invalid_rule_category_is_rejected():
    r = client.post(
        "/trials",
        json={
            "trial_id": "T-BAD",
            "trial_name": "Bad Trial",
            "rules": [{"rule_id": "INC-01", "rule_text": "test", "category": "not_a_real_category"}],
        },
    )
    assert r.status_code == 422  # FastAPI/pydantic request validation error


def test_invalid_rule_id_format_is_rejected_at_registration():
    """The INC-##/EXC-## format rule from Phase 0 is enforced on Rule itself
    (see reasoning_engine/protocol.py), so a bad rule_id is caught immediately
    at trial registration -- not deferred to a confusing failure later
    during assessment."""
    r = client.post(
        "/trials",
        json={
            "trial_id": "T-BAD-ID",
            "trial_name": "Bad Rule Id Trial",
            "rules": [{"rule_id": "RULE-1", "rule_text": "test", "category": "inclusion"}],
        },
    )
    assert r.status_code == 422


def test_data_persists_across_a_fresh_database_connection():
    """The storage-layer half of the persistence proof: everything the API
    wrote must be readable back through a brand-new sqlite3 connection --
    exactly what a freshly-started process would do. This exercises the
    full join across trials -> rules and assessments -> rule_results ->
    decisions, not just one table in isolation."""
    import sqlite3

    import db

    client.post(
        "/trials",
        json={
            "trial_id": "T-PERSIST-1",
            "trial_name": "Persistent Trial",
            "rules": [
                {"rule_id": "INC-01", "rule_text": "Patient must be 50 or older", "category": "inclusion"},
                {"rule_id": "EXC-01", "rule_text": "Patient is taking Warfarin", "category": "exclusion"},
            ],
        },
    )
    assess_resp = client.post(
        "/assess",
        json={"trial_id": "T-PERSIST-1", "patient_id": "P-1", "patient_record": "some record"},
    )
    assessment_id = assess_resp.json()["assessment_id"]
    client.post(f"/assessments/{assessment_id}/decision", json={"decision": "overridden"})

    # New connection to the SAME file -- no reference to anything main.py
    # or the TestClient still holds in memory.
    conn = sqlite3.connect(db.DB_PATH)
    try:
        trial = conn.execute("SELECT trial_id, trial_name FROM trials WHERE trial_id='T-PERSIST-1'").fetchone()
        assert trial is not None
        assert trial[1] == "Persistent Trial"

        rules = conn.execute("SELECT rule_id FROM rules WHERE trial_id='T-PERSIST-1'").fetchall()
        assert {r[0] for r in rules} == {"INC-01", "EXC-01"}

        assessment = conn.execute(
            "SELECT assessment_id, trial_id, patient_id FROM assessments WHERE assessment_id=?",
            (assessment_id,),
        ).fetchone()
        assert assessment is not None
        assert assessment[1] == "T-PERSIST-1"
        assert assessment[2] == "P-1"

        rule_results = conn.execute(
            "SELECT rule_id, status FROM rule_results WHERE assessment_id=?",
            (assessment_id,),
        ).fetchall()
        assert len(rule_results) == 2
        assert {rr[0] for rr in rule_results} == {"INC-01", "EXC-01"}

        decision = conn.execute(
            "SELECT decision FROM decisions WHERE assessment_id=?", (assessment_id,)
        ).fetchone()
        assert decision is not None
        assert decision[0] == "overridden"
    finally:
        conn.close()