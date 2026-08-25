"""Tests for Lab 2 - Modeling Runs, Spans, and Tool Calls (Audit DB Labs).

Testing strategy (documented per AGENTS.md / TEST.md), mirroring Lab 1's:

(a) LIVE-DB TESTS -- when DATABASE_URL can be resolved the same way the
    notebook resolves it (walking upward from this file's folder for a .env),
    tests run against the real Supabase Postgres. All live-test writes are
    tagged with a unique per-session marker ("pytest-lab2-<hex>" run rows),
    and the tagged-run fixture deletes every tagged row afterwards -- child
    tables first (guardrail_event, tool_call, span), then the run itself --
    so the suite is safe to re-run and leaves no residue.

(b) HONEST SKIPS + FILE-BASED TESTS -- if no .env/DATABASE_URL is configured,
    live tests skip with an explicit reason rather than pretending to pass.
    Tests that need no database at all (dependency pinning consistency,
    CQ-1 line budget, cell-ID uniqueness, section order, absence of
    hardcoded credentials, absence of virtual-environment instructions,
    absence of Lab 3+ scope creep) always run regardless of environment.

TEST.md categories actually applied here (no padding):
  - Documentation vs Actual Behavior ....... pinned versions match across files;
                                             markdown code blocks exist in notebook;
                                             section order is exactly right
  - Security & Configuration Hygiene ....... no hardcoded credentials anywhere;
                                             no virtual-environment instructions
  - Correctness of Core Logic .............. FK constraints reject orphaned
                                             child rows; CHECK constraint rejects
                                             an out-of-range outcome; NOT NULL
                                             rejects a missing required field;
                                             nested-history query returns the
                                             right shape
  - Boundary & Limit Conditions ............ CQ-1 line budget at Intermediate bounds
  - Cleanup & Side Effects ................. tagged-row teardown in FK-safe order

Scope note: Lab 2 builds ONLY the span / tool_call / guardrail_event tables
on top of Lab 1's existing run/event tables (README Section 8.1). It must not
redefine `run` or `event`, and must not reach into Lab 3's territory (JOINs,
GROUP BY, window functions, CTEs, EXPLAIN) -- those checks run here as scope
guards, same spirit as Lab 1's guard against Lab 2 entities.
"""
import json
import re
import uuid
from pathlib import Path

import psycopg2
import pytest

LAB_DIR = Path(__file__).resolve().parent
NB_PATH = LAB_DIR / "lab-modeling-runs-spans-tool-calls.ipynb"
MD_PATH = LAB_DIR / "lab-modeling-runs-spans-tool-calls.md"
ASSIGNMENT_PATH = LAB_DIR / "lab-modeling-runs-spans-tool-calls-assignment.md"

EXPECTED_PINS = ["python-dotenv==1.2.3", "psycopg2-binary==2.9.12"]
NEW_TABLES = {"span", "tool_call", "guardrail_event"}
# Lab 3's territory (README Section 8.1: JOINs, GROUP BY, window functions, CTEs, EXPLAIN).
LAB3_SQL_PATTERNS = [r"\bJOIN\b", r"\bGROUP\s+BY\b", r"\bOVER\s*\(", r"\bEXPLAIN\b"]
VENV_PATTERNS = [r"\bvenv\b", r"virtualenv", r"virtual\s+environment", r"python\s+-m\s+venv"]

RUN_MARKER_PREFIX = "pytest-lab2-"

# Matches Lab 1's own run/event DDL exactly -- used only to guarantee the
# fixture's prerequisite exists; Lab 2's own notebook never creates this.
RUN_TABLE_DDL = """
    CREATE TABLE IF NOT EXISTS run (
        run_id      SERIAL PRIMARY KEY,
        agent_name  TEXT,
        started_at  TIMESTAMPTZ DEFAULT now(),
        ended_at    TIMESTAMPTZ,
        status      TEXT,
        total_cost  NUMERIC(10, 6));
"""

LAB2_SCHEMA_DDL = """
    CREATE TABLE IF NOT EXISTS span (
        span_id     SERIAL PRIMARY KEY,
        run_id      INTEGER NOT NULL REFERENCES run(run_id),
        span_name   TEXT NOT NULL,
        started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        ended_at    TIMESTAMPTZ);
    CREATE TABLE IF NOT EXISTS tool_call (
        tool_call_id SERIAL PRIMARY KEY,
        span_id      INTEGER NOT NULL REFERENCES span(span_id),
        tool_name    TEXT NOT NULL,
        arguments    TEXT,
        result       TEXT,
        success      BOOLEAN NOT NULL,
        called_at    TIMESTAMPTZ NOT NULL DEFAULT now());
    CREATE TABLE IF NOT EXISTS guardrail_event (
        guardrail_event_id SERIAL PRIMARY KEY,
        span_id             INTEGER NOT NULL REFERENCES span(span_id),
        check_name          TEXT NOT NULL,
        outcome             TEXT NOT NULL CHECK (outcome IN ('pass', 'fail', 'warn')),
        reason              TEXT,
        checked_at          TIMESTAMPTZ NOT NULL DEFAULT now());
    CREATE INDEX IF NOT EXISTS idx_span_run_id ON span (run_id);
    CREATE INDEX IF NOT EXISTS idx_tool_call_span_id ON tool_call (span_id);
    CREATE INDEX IF NOT EXISTS idx_guardrail_event_span_id ON guardrail_event (span_id);
"""


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def load_notebook():
    return json.loads(NB_PATH.read_text(encoding="utf-8"))


def notebook_code_sources():
    sources = []
    for cell in load_notebook()["cells"]:
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


@pytest.fixture(scope="module")
def db():
    """Live connection; skips honestly when no DATABASE_URL is configured."""
    url = get_database_url()
    if not url:
        pytest.skip("DATABASE_URL not configured (.env missing at repo/module level) "
                    "-- live Postgres tests skipped honestly, not failed")
    conn = psycopg2.connect(url, connect_timeout=15)
    yield conn
    conn.close()


@pytest.fixture()
def marked_run(db):
    """Ensure schema (Lab 1's run table + Lab 2's new tables), create a
    uniquely-tagged run row, and clean up every tagged row on teardown in
    FK-safe order (children before parent)."""
    cur = db.cursor()
    cur.execute(RUN_TABLE_DDL)
    cur.execute(LAB2_SCHEMA_DDL)
    db.commit()
    marker = f"{RUN_MARKER_PREFIX}{uuid.uuid4().hex[:12]}"
    cur.execute(
        "INSERT INTO run (agent_name, status) VALUES (%s, %s) RETURNING run_id",
        (marker, "running"),
    )
    run_id = cur.fetchone()[0]
    db.commit()
    yield {"run_id": run_id, "marker": marker}
    cur.execute(
        "DELETE FROM guardrail_event WHERE span_id IN (SELECT span_id FROM span WHERE run_id = %s)",
        (run_id,),
    )
    cur.execute(
        "DELETE FROM tool_call WHERE span_id IN (SELECT span_id FROM span WHERE run_id = %s)",
        (run_id,),
    )
    cur.execute("DELETE FROM span WHERE run_id = %s", (run_id,))
    cur.execute("DELETE FROM run WHERE agent_name LIKE %s", (f"{RUN_MARKER_PREFIX}%",))
    db.commit()
    cur.close()


# --------------------------------------------------------------------------
# Always-on tests: file-based (no database needed)
# --------------------------------------------------------------------------

class TestDocumentationVsBehavior:
    """TEST.md category 11: written spec must match actual code."""

    def test_pip_cell_pins_exact_expected_versions(self):
        first_code = notebook_code_sources()[0]
        assert first_code.startswith("!pip install ")
        for pin in EXPECTED_PINS:
            assert pin in first_code

    def test_markdown_carries_pinned_versions_in_sections_6_9_and_step0(self):
        md_text = MD_PATH.read_text(encoding="utf-8")
        for pin in EXPECTED_PINS:
            assert md_text.count(pin) >= 3, (
                f"{pin} must appear in Tech Stack, Environment Setup, and Step 0")

    def test_markdown_python_blocks_exist_verbatim_in_notebook(self):
        md_text = MD_PATH.read_text(encoding="utf-8")
        blocks = re.findall(r"```python\n(.*?)```", md_text, re.S)
        assert len(blocks) >= 10, "Section 10 should carry one block per step"
        joined_notebook = "\n".join(notebook_code_sources())
        for i, block in enumerate(blocks):
            for raw_line in block.splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                assert line in joined_notebook, (
                    f"markdown python block {i} line not found in notebook: {line!r}")

    def test_markdown_has_all_required_sections_in_order(self):
        """The lab's documented convention: 'Underlying Concepts' sits 2nd,
        immediately after Problem Statement, matching Lab 1's deliberate
        deviation from the constitution's original ordering. This lists
        exactly the 11 sections that must appear, in order -- not 12 and not
        hardcoded to a stale count."""
        md_text = MD_PATH.read_text(encoding="utf-8")
        sections = ["Problem Statement / Use Case Overview", "Underlying Concepts",
                    "Input Data", "Processing", "Output", "Tech Stack", "Prerequisites",
                    "Environment / Dependencies Setup", "Step-wise Development Instructions",
                    "Optional Exercise", "What We Learnt"]
        assert len(sections) == 11
        positions = [md_text.find(f"# {s}") for s in sections]
        missing = [s for s, p in zip(sections, positions) if p == -1]
        assert not missing, f"missing sections: {missing}"
        assert positions == sorted(positions), "sections appear out of order"

    def test_prerequisites_mentions_lab1_is_required(self):
        md_text = MD_PATH.read_text(encoding="utf-8")
        prereq_start = md_text.find("# Prerequisites")
        prereq_end = md_text.find("# Environment / Dependencies Setup")
        prereq_section = md_text[prereq_start:prereq_end]
        assert "Lab 1" in prereq_section, "Prerequisites must state Lab 1 is required"

    def test_difficulty_header_does_not_claim_no_prerequisites(self):
        md_text = MD_PATH.read_text(encoding="utf-8")
        header_line = md_text.splitlines()[4]
        assert "no prerequisites" not in header_line.lower()
        assert "requires lab 1" in header_line.lower()


class TestScopeGuards:
    """Lab 2 scope per README Section 8.1: build the schema, not Lab 3's joins."""

    def test_notebook_does_not_recreate_lab1_tables(self):
        joined = "\n".join(notebook_code_sources())
        created = set(re.findall(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(\w+)", joined, re.I))
        assert created == NEW_TABLES, f"expected only {NEW_TABLES}, found {created}"

    def test_notebook_has_no_lab3_sql_patterns(self):
        joined = "\n".join(notebook_code_sources())
        for pattern in LAB3_SQL_PATTERNS:
            hits = re.findall(pattern, joined, re.I)
            assert not hits, f"Lab 3 SQL pattern {pattern!r} found in notebook: {hits[:3]}"

    def test_schema_has_foreign_keys_not_null_check_and_index(self):
        joined = "\n".join(notebook_code_sources())
        assert re.search(r"REFERENCES\s+run\s*\(\s*run_id\s*\)", joined, re.I)
        assert re.search(r"REFERENCES\s+span\s*\(\s*span_id\s*\)", joined, re.I)
        assert len(re.findall(r"NOT\s+NULL", joined, re.I)) >= 3
        assert re.search(r"CHECK\s*\(\s*outcome\s+IN", joined, re.I)
        assert len(re.findall(r"CREATE\s+INDEX", joined, re.I)) >= 1

    @pytest.mark.parametrize("path", [NB_PATH, MD_PATH])
    def test_no_virtual_environment_instructions_anywhere(self, path):
        text = path.read_text(encoding="utf-8")
        for pattern in VENV_PATTERNS:
            hits = re.findall(pattern, text, re.I)
            assert not hits, f"{path.name} mentions a virtual environment ({pattern!r}): {hits[:3]}"


class TestNotebookStructure:
    def test_cell_ids_unique_within_notebook(self):
        ids = [c["id"] for c in load_notebook()["cells"]]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        assert not dupes, f"duplicate cell IDs corrupt notebooks: {dupes}"

    def test_cell_ids_do_not_collide_with_other_labs(self):
        ours = {c["id"] for c in load_notebook()["cells"]}
        others = set()
        for nb_path in REPO_GLOB:
            try:
                data = json.loads(nb_path.read_text(encoding="utf-8"))
                for c in data.get("cells", []):
                    cid = c.get("id")
                    if cid and nb_path.resolve() != NB_PATH.resolve():
                        others.add(cid)
            except Exception:
                continue
        collision = sorted(ours & others)
        assert not collision, f"cell IDs collide with other labs' notebooks: {collision}"

    def test_cq1_intermediate_line_budget(self):
        nonblank = sum(
            1 for src in notebook_code_sources() for line in src.splitlines() if line.strip()
        )
        assert 110 <= nonblank <= 150, f"CQ-1 Intermediate budget violated: {nonblank} lines"

    def test_first_code_cell_is_single_pinned_pip_install_line(self):
        first_code = notebook_code_sources()[0].strip()
        assert "\n" not in first_code, "pip install must be one single line"
        assert first_code.startswith("!pip install")


REPO_GLOB = list(LAB_DIR.parents[1].glob("**/*.ipynb"))  # repo root notebooks


class TestSecurityHygiene:
    """TEST.md category 8: no secrets in shipped files."""

    @pytest.mark.parametrize("path", [NB_PATH, MD_PATH, ASSIGNMENT_PATH])
    def test_no_hardcoded_credentials(self, path):
        text = path.read_text(encoding="utf-8")
        leaks = [m for m in re.findall(r"postgres(?:ql)?://\S+:\S+@", text) if "<" not in m]
        assert not leaks, f"possible credential leak in {path.name}: {leaks}"

    def test_connection_string_sourced_from_env_not_literal(self):
        joined = "\n".join(notebook_code_sources())
        assert 'os.getenv("DATABASE_URL")' in joined
        assert "DATABASE_URL not found" in joined  # fail-fast message present


# --------------------------------------------------------------------------
# Live-database tests (skipped honestly without DATABASE_URL)
# --------------------------------------------------------------------------

class TestConnection:
    def test_connection_succeeds_and_reports_postgres_version(self, db):
        cur = db.cursor()
        cur.execute("SELECT version();")
        version_string = cur.fetchone()[0]
        cur.close()
        assert version_string.startswith("PostgreSQL"), version_string

    def test_create_tables_is_safe_to_rerun(self, db):
        cur = db.cursor()
        cur.execute(RUN_TABLE_DDL)
        cur.execute(LAB2_SCHEMA_DDL)
        cur.execute(LAB2_SCHEMA_DDL)  # second execution must not raise
        db.commit()
        cur.close()


class TestForeignKeyConstraints:
    def test_span_rejects_orphaned_run_id(self, db, marked_run):
        cur = db.cursor()
        with pytest.raises(psycopg2.errors.ForeignKeyViolation):
            cur.execute(
                "INSERT INTO span (run_id, span_name) VALUES (%s, %s)",
                (999999999, "orphan_span"),
            )
        db.rollback()
        cur.close()

    def test_tool_call_rejects_orphaned_span_id(self, db, marked_run):
        cur = db.cursor()
        with pytest.raises(psycopg2.errors.ForeignKeyViolation):
            cur.execute(
                "INSERT INTO tool_call (span_id, tool_name, success) VALUES (%s, %s, %s)",
                (999999999, "orphan_tool", True),
            )
        db.rollback()
        cur.close()

    def test_guardrail_event_rejects_orphaned_span_id(self, db, marked_run):
        cur = db.cursor()
        with pytest.raises(psycopg2.errors.ForeignKeyViolation):
            cur.execute(
                "INSERT INTO guardrail_event (span_id, check_name, outcome) VALUES (%s, %s, %s)",
                (999999999, "orphan_check", "pass"),
            )
        db.rollback()
        cur.close()


class TestColumnConstraints:
    def test_check_constraint_rejects_out_of_range_outcome(self, db, marked_run):
        cur = db.cursor()
        cur.execute(
            "INSERT INTO span (run_id, span_name) VALUES (%s, %s) RETURNING span_id",
            (marked_run["run_id"], "check_test_span"),
        )
        span_id = cur.fetchone()[0]
        db.commit()

        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute(
                "INSERT INTO guardrail_event (span_id, check_name, outcome) VALUES (%s, %s, %s)",
                (span_id, "bad_outcome_test", "maybe"),
            )
        db.rollback()
        cur.close()

    def test_not_null_rejects_missing_tool_name(self, db, marked_run):
        cur = db.cursor()
        cur.execute(
            "INSERT INTO span (run_id, span_name) VALUES (%s, %s) RETURNING span_id",
            (marked_run["run_id"], "not_null_test_span"),
        )
        span_id = cur.fetchone()[0]
        db.commit()

        with pytest.raises(psycopg2.errors.NotNullViolation):
            cur.execute(
                "INSERT INTO tool_call (span_id, tool_name, success) VALUES (%s, %s, %s)",
                (span_id, None, True),
            )
        db.rollback()
        cur.close()


class TestNestedHistoryReconstruction:
    def test_query_reconstructs_run_spans_and_children_in_right_shape(self, db, marked_run):
        run_id = marked_run["run_id"]
        cur = db.cursor()

        cur.execute(
            "INSERT INTO span (run_id, span_name) VALUES (%s, %s) RETURNING span_id",
            (run_id, "retrieve_orders"),
        )
        retrieve_span_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO tool_call (span_id, tool_name, result, success) VALUES (%s, %s, %s, %s)",
            (retrieve_span_id, "query_orders_db", "1284 rows returned", True),
        )

        cur.execute(
            "INSERT INTO span (run_id, span_name) VALUES (%s, %s) RETURNING span_id",
            (run_id, "generate_answer"),
        )
        answer_span_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO guardrail_event (span_id, check_name, outcome, reason) VALUES (%s, %s, %s, %s)",
            (answer_span_id, "pii_scan", "pass", "clean"),
        )
        db.commit()

        cur.execute(
            "SELECT span_id, span_name FROM span WHERE run_id = %s ORDER BY started_at",
            (run_id,),
        )
        spans = cur.fetchall()
        assert [s[1] for s in spans] == ["retrieve_orders", "generate_answer"]

        cur.execute(
            "SELECT tool_name, result, success FROM tool_call WHERE span_id = %s",
            (retrieve_span_id,),
        )
        tool_rows = cur.fetchall()
        assert tool_rows == [("query_orders_db", "1284 rows returned", True)]

        cur.execute(
            "SELECT check_name, outcome, reason FROM guardrail_event WHERE span_id = %s",
            (answer_span_id,),
        )
        guardrail_rows = cur.fetchall()
        assert guardrail_rows == [("pii_scan", "pass", "clean")]
        cur.close()


class TestCleanup:
    def test_cleanup_removes_all_tagged_rows_safe_to_rerun(self, db, marked_run):
        run_id = marked_run["run_id"]
        cur = db.cursor()
        cur.execute(
            "INSERT INTO span (run_id, span_name) VALUES (%s, %s) RETURNING span_id",
            (run_id, "cleanup_test_span"),
        )
        span_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO tool_call (span_id, tool_name, success) VALUES (%s, %s, %s)",
            (span_id, "cleanup_tool", True),
        )
        db.commit()

        cur.execute("SELECT count(*) FROM run WHERE agent_name LIKE %s",
                    (f"{RUN_MARKER_PREFIX}%",))
        before = cur.fetchone()[0]
        assert before >= 1

        cur.execute("DELETE FROM tool_call WHERE span_id = %s", (span_id,))
        cur.execute("DELETE FROM span WHERE run_id = %s", (run_id,))
        cur.execute("DELETE FROM run WHERE agent_name LIKE %s", (f"{RUN_MARKER_PREFIX}%",))
        db.commit()

        cur.execute("SELECT count(*) FROM run WHERE agent_name LIKE %s",
                    (f"{RUN_MARKER_PREFIX}%",))
        after = cur.fetchone()[0]
        assert after == 0, "tagged test rows must be fully removable"
        cur.close()
