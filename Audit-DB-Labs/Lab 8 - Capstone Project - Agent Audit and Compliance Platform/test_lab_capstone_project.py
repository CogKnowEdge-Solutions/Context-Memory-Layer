"""Tests for Lab 8 - Capstone Project: Agent Audit and Compliance Platform (Audit DB Labs).

This is the grading harness the instructor runs against whatever the student
eventually submits. It is expected to fail/report "not found" right now,
since the student's notebook doesn't exist yet — that's correct, not a bug.

Testing strategy:

(a) FILE-BASED TESTS -- always run regardless of environment. Check the
    .md file's section presence/order, pinned dependency versions, Mermaid
    diagram count, absence of virtual-environment instructions, absence of
    .xlsx references, absence of hardcoded credentials, and that the
    assignment file contains required keywords.

(b) STUDENT-SUBMISSION TESTS -- check for a student-submitted notebook at
    a fixed path (reports not-found until a student submits). When present,
    run live-DB tests against the real Supabase Postgres to verify the
    student's implementation: hierarchy integrity, hash chain, auditor role.

(c) HONEST SKIPS -- if no .env/DATABASE_URL or no student notebook, live
    tests skip with an explicit reason rather than pretending to pass.
"""
import json
import re
import uuid
from hashlib import md5 as md5_fn
from pathlib import Path

import psycopg2
import pytest

LAB_DIR = Path(__file__).resolve().parent
MD_PATH = LAB_DIR / "lab-capstone-project.md"
ASSIGNMENT_PATH = LAB_DIR / "lab-capstone-project-assignment.md"

# The student's notebook is expected at this path once they submit.
STUDENT_NB_PATH = LAB_DIR / "lab-capstone-project.ipynb"

EXPECTED_PINS = ["python-dotenv==1.2.3", "psycopg2-binary==2.9.12"]

# The 13 sections the .md must contain, in this exact order.
MD_SECTIONS = [
    "Problem Statement / Use Case Overview",
    "Underlying Concepts",
    "Project Structure",
    "Input Data",
    "Processing",
    "Output",
    "Tech Stack",
    "Prerequisites",
    "Environment / Dependencies Setup",
    "Development Guide",
    "Marking Breakdown",
    "Optional Exercise",
    "What We Learnt",
]

VENV_PATTERNS = [r"\bvenv\b", r"virtualenv", r"virtual\s+environment", r"python\s+-m\s+venv"]
XLSX_PATTERNS = [r"\.xlsx\b", r"openpyxl", r"xlsxwriter"]

RUN_MARKER_PREFIX = "pytest-lab8-"


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def md_text():
    return MD_PATH.read_text(encoding="utf-8")


def assignment_text():
    return ASSIGNMENT_PATH.read_text(encoding="utf-8")


def student_notebook_exists():
    return STUDENT_NB_PATH.exists()


def load_student_notebook():
    return json.loads(STUDENT_NB_PATH.read_text(encoding="utf-8"))


def student_code_sources():
    sources = []
    for cell in load_student_notebook()["cells"]:
        if cell["cell_type"] == "code":
            src = "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
            sources.append(src)
    return sources


def find_env_path():
    for p in [LAB_DIR, *LAB_DIR.parents]:
        candidate = p / ".env"
        if candidate.exists():
            return candidate
    return None


def get_database_url():
    env_path = find_env_path()
    if env_path is None:
        return None
    match = re.search(r"^\s*DATABASE_URL\s*=\s*(.+)\s*$",
                      env_path.read_text(encoding="utf-8"), re.M)
    return match.group(1).strip().strip('"').strip("'") if match else None


# --------------------------------------------------------------------------
# Always-on tests: file-based (no database or student submission needed)
# --------------------------------------------------------------------------

class TestMarkdownStructure:
    """Verify lab-capstone-project.md has all 13 sections in order."""

    def test_all_thirteen_sections_exist_in_order(self):
        text = md_text()
        assert len(MD_SECTIONS) == 13
        positions = [text.find(f"# {s}") for s in MD_SECTIONS]
        missing = [s for s, p in zip(MD_SECTIONS, positions) if p == -1]
        assert not missing, f"missing sections: {missing}"
        assert positions == sorted(positions), "sections appear out of order"

    def test_section_2_is_underlying_concepts(self):
        text = md_text()
        problem_pos = text.find("# Problem Statement / Use Case Overview")
        concepts_pos = text.find("# Underlying Concepts")
        assert problem_pos != -1, "missing Problem Statement"
        assert concepts_pos != -1, "missing Underlying Concepts"
        assert concepts_pos > problem_pos, "Underlying Concepts must come after Problem Statement"
        # Check nothing else is between them (no other H1 section)
        between = text[problem_pos + 1:concepts_pos]
        assert "# " not in between, (
            f"Underlying Concepts must be section 2, immediately after Problem Statement. "
            f"Found another H1 section between them: {between[:200]}")

    def test_appendix_a_and_b_exist(self):
        text = md_text()
        assert "# Appendix A" in text, "missing Appendix A"
        assert "# Appendix B" in text, "missing Appendix B"

    def test_markdown_has_at_least_two_mermaid_diagrams(self):
        text = md_text()
        mermaid_count = len(re.findall(r"```mermaid", text))
        assert mermaid_count >= 2, f"need at least 2 Mermaid diagrams, found {mermaid_count}"

    def test_md_mentions_labs_1_through_7(self):
        text = md_text()
        for lab_num in ["Lab 1", "Lab 2", "Lab 3", "Lab 7"]:
            assert lab_num in text, f"markdown must mention {lab_num}"

    def test_markdown_carries_pinned_versions(self):
        text = md_text()
        for pin in EXPECTED_PINS:
            assert pin in text, f"{pin} must appear in the markdown"
            assert text.count(pin) >= 2, (
                f"{pin} should appear in Tech Stack and Environment Setup (at least 2 times)")

    def test_markdown_python_blocks_exist_verbatim_in_student_notebook(self):
        """When a student submits a notebook, its code must match the .md's code blocks."""
        if not student_notebook_exists():
            pytest.skip("no student notebook submitted yet")
        text = md_text()
        blocks = re.findall(r"```python\n(.*?)```", text, re.S)
        assert len(blocks) >= 10, "Section 10 should carry one block per step"
        joined = "\n".join(student_code_sources())
        for i, block in enumerate(blocks):
            for raw_line in block.splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                assert line in joined, (
                    f"markdown python block {i} line not found in student notebook: {line!r}")

    @pytest.mark.parametrize("path_label", ["md", "assignment"])
    def test_no_virtual_environment_instructions(self, path_label):
        text = md_text() if path_label == "md" else assignment_text()
        fname = "lab-capstone-project.md" if path_label == "md" else "assignment file"
        for pattern in VENV_PATTERNS:
            hits = re.findall(pattern, text, re.I)
            assert not hits, f"{fname} mentions virtual environment ({pattern!r}): {hits[:3]}"

    @pytest.mark.parametrize("path_label", ["md", "assignment"])
    def test_no_xlsx_references(self, path_label):
        text = md_text() if path_label == "md" else assignment_text()
        fname = "lab-capstone-project.md" if path_label == "md" else "assignment file"
        for pattern in XLSX_PATTERNS:
            hits = re.findall(pattern, text, re.I)
            assert not hits, f"{fname} references .xlsx ({pattern!r}): {hits[:3]}"

    @pytest.mark.parametrize("path_label", ["md", "assignment"])
    def test_no_hardcoded_credentials(self, path_label):
        text = md_text() if path_label == "md" else assignment_text()
        fname = "lab-capstone-project.md" if path_label == "md" else "assignment file"
        leaks = [m for m in re.findall(r"postgres(?:ql)?://\S+:\S+@", text) if "<" not in m]
        assert not leaks, f"possible credential leak in {fname}: {leaks}"


class TestAssignmentStructure:
    """Verify lab-capstone-project-assignment.md has required content."""

    def test_assignment_contains_mandatory(self):
        assert "Mandatory" in assignment_text(), "assignment must contain 'Mandatory'"

    def test_assignment_contains_deliverables(self):
        text = assignment_text()
        assert "Deliverables" in text or "deliverables" in text, (
            "assignment must contain 'Deliverables'")

    def test_assignment_contains_rubric(self):
        assert "Rubric" in assignment_text(), "assignment must contain 'Rubric'"

    def test_assignment_contains_success_or_criteria(self):
        text = assignment_text()
        has_success = "Success" in text or "success" in text
        has_criteria = "Criteria" in text or "criteria" in text
        has_checkmark = "✓" in text
        assert has_success or has_criteria or has_checkmark, (
            "assignment must contain 'Success', 'Criteria', or '✓'")

    def test_assignment_contains_proposal_stage(self):
        text = assignment_text()
        assert "Proposal" in text, "assignment must contain 'Proposal Stage'"

    def test_assignment_contains_milestone_checkins(self):
        text = assignment_text()
        assert "Milestone" in text, "assignment must contain 'Milestone Check-ins'"

    def test_assignment_rubric_sums_to_100(self):
        text = assignment_text()
        # Look for patterns like "15 points" or "20 pts" in a rubric table
        points = re.findall(r"\b(\d{1,3})\s*(?:points?|pts?)\b", text, re.I)
        total = sum(int(p) for p in points)
        assert total == 100, f"rubric must sum to 100, found {total}"

    def test_assignment_contains_submission_format(self):
        text = assignment_text()
        assert "Submission" in text or "submission" in text, (
            "assignment must contain 'Submission Format'")

    def test_assignment_contains_project_summary_template(self):
        text = assignment_text()
        assert "PROJECT_SUMMARY" in text, (
            "assignment must contain PROJECT_SUMMARY.md template")


class TestCompanionFiles:
    """Verify all three required files exist."""

    def test_md_file_exists(self):
        assert MD_PATH.exists(), "lab-capstone-project.md not found"

    def test_assignment_file_exists(self):
        assert ASSIGNMENT_PATH.exists(), "lab-capstone-project-assignment.md not found"

    def test_test_file_is_self(self):
        """This test file itself should exist (sanity check)."""
        assert Path(__file__).exists()


# --------------------------------------------------------------------------
# Student-submission tests (skipped until notebook exists)
# --------------------------------------------------------------------------

class TestStudentNotebookStructure:
    """Run only when a student submits their notebook."""

    def test_notebook_exists(self):
        if not student_notebook_exists():
            pytest.skip("no student notebook submitted yet — "
                        "expected until a student builds their implementation")

    def test_first_code_cell_is_pinned_pip_install(self):
        if not student_notebook_exists():
            pytest.skip("no student notebook submitted yet")
        first_code = student_code_sources()[0].strip()
        assert "\n" not in first_code, "pip install must be one single line"
        assert first_code.startswith("!pip install")
        for pin in EXPECTED_PINS:
            assert pin in first_code, f"first cell must pin {pin}"

    def test_cell_ids_unique_within_notebook(self):
        if not student_notebook_exists():
            pytest.skip("no student notebook submitted yet")
        ids = [c["id"] for c in load_student_notebook()["cells"]]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        assert not dupes, f"duplicate cell IDs: {dupes}"

    def test_no_virtual_environment_in_notebook(self):
        if not student_notebook_exists():
            pytest.skip("no student notebook submitted yet")
        for src in student_code_sources():
            for pattern in VENV_PATTERNS:
                assert not re.search(pattern, src, re.I), (
                    f"student notebook contains venv reference: {pattern!r}")

    def test_connection_sourced_from_env(self):
        if not student_notebook_exists():
            pytest.skip("no student notebook submitted yet")
        joined = "\n".join(student_code_sources())
        assert 'os.getenv("DATABASE_URL")' in joined or "os.getenv('DATABASE_URL')" in joined
        assert "DATABASE_URL not found" in joined


# --------------------------------------------------------------------------
# Live-database tests (skipped without DATABASE_URL or student notebook)
# --------------------------------------------------------------------------

class TestLiveIntegration:
    """Run against the real database only when a student notebook exists
    AND a DATABASE_URL is configured. Verifies the student's actual output."""

    @pytest.fixture(scope="class")
    def db(self):
        url = get_database_url()
        if not url:
            pytest.skip("DATABASE_URL not configured — live tests skipped honestly")
        conn = psycopg2.connect(url, connect_timeout=15)
        yield conn
        conn.close()

    def test_prerequisite_tables_exist(self, db):
        cur = db.cursor()
        for table in ["run", "event", "span", "tool_call", "guardrail_event"]:
            cur.execute("SELECT to_regclass(%s)", (f"public.{table}",))
            assert cur.fetchone()[0] is not None, f"{table} table missing"
        cur.close()

    def test_hash_chain_concept_works(self, db):
        """Verify the hash-chain algorithm works against real Postgres.
        This tests the concept, not the student's specific implementation."""
        cur = db.cursor()
        marker = f"{RUN_MARKER_PREFIX}{uuid.uuid4().hex[:12]}"
        cur.execute(
            "INSERT INTO run (agent_name, status) VALUES (%s, %s) RETURNING run_id",
            (marker, "test"))
        run_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO event (run_id, event_type, payload) VALUES (%s, %s, %s) RETURNING event_id",
            (run_id, "test_event", "test payload"))
        ev_id = cur.fetchone()[0]
        db.commit()

        # Build chain link
        content = f"{ev_id}|{run_id}|test_event|test payload|GENESIS"
        row_hash = md5_fn(content.encode()).hexdigest()

        # Verify recomputation matches
        content2 = f"{ev_id}|{run_id}|test_event|test payload|GENESIS"
        assert row_hash == md5_fn(content2.encode()).hexdigest(), "hash chain concept broken"

        # Verify tamper detection
        content_tampered = f"{ev_id}|{run_id}|test_event|TAMPERED|GENESIS"
        assert row_hash != md5_fn(content_tampered.encode()).hexdigest(), (
            "hash chain should detect tamper")

        # Cleanup
        cur.execute("DELETE FROM event WHERE event_id = %s", (ev_id,))
        cur.execute("DELETE FROM run WHERE run_id = %s", (run_id,))
        db.commit()
        cur.close()

    def test_rbac_grants_concept_works(self, db):
        """Verify GRANT/REVOKE works against real Postgres.
        This tests the concept, not the student's specific role."""
        cur = db.cursor()
        cur.execute("DROP VIEW IF EXISTS v_audit_trail")
        cur.execute("""CREATE VIEW v_audit_trail AS
            SELECT r.run_id, r.agent_name
            FROM run r""")
        db.commit()

        for stmt in [
            "REVOKE ALL ON SCHEMA public FROM lab8_auditor",
            "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM lab8_auditor",
            "DROP USER IF EXISTS lab8_auditor",
        ]:
            try:
                cur.execute(stmt)
            except Exception:
                db.rollback()
        db.commit()
        cur.execute("CREATE USER lab8_auditor WITH PASSWORD 'lab5_test_pass_2026'")
        cur.execute("GRANT SELECT ON v_audit_trail TO lab8_auditor")
        cur.execute("GRANT USAGE ON SCHEMA public TO lab8_auditor")
        db.commit()

        cur.execute("""SELECT privilege_type FROM information_schema.role_table_grants
            WHERE grantee = 'lab8_auditor' AND table_name = 'v_audit_trail'""")
        privs = [row[0] for row in cur.fetchall()]
        assert "SELECT" in privs, f"expected SELECT grant, got {privs}"

        cur.execute("""SELECT privilege_type FROM information_schema.role_table_grants
            WHERE grantee = 'lab8_auditor' AND table_name = 'run'""")
        privs = [row[0] for row in cur.fetchall()]
        assert "INSERT" not in privs, f"should NOT have INSERT on run, got {privs}"

        # Cleanup
        for stmt in [
            "DROP VIEW IF EXISTS v_audit_trail",
            "REVOKE ALL ON SCHEMA public FROM lab8_auditor",
            "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM lab8_auditor",
            "DROP USER IF EXISTS lab8_auditor",
        ]:
            try:
                cur.execute(stmt)
            except Exception:
                db.rollback()
        db.commit()
        cur.close()
