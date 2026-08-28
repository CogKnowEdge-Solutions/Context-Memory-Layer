"""Tests for Lab 7 - Capstone Project: AI Agent Memory Service (MongoDB Labs).

This is the grading harness the instructor runs against whatever the student
eventually submits. It is expected to report "documented-only" cleanly right
now, because this capstone is intentionally NOT built as an example notebook —
the student builds `lab-agent-memory-service.ipynb` themselves.

Testing strategy:

(a) FILE-BASED TESTS -- always run regardless of environment. Check the four
    provided files exist and parse, the .md has its sections in order and
    Mermaid diagrams, the brief carries pinned dependency versions and a
    MONGODB_URI connection convention, the assignment and brief rubrics each
    sum to 100 AND match each other, every Lab 1..Lab 6 appears MULTIPLE times
    in the brief (anti-orphan: no Lab may be mentioned but never required),
    and neither file references another module.

(b) DATA-LOGIC TESTS -- mongomock. Exercise the seed + tagged-cleanup helpers
    the capstone's synthetic-data pipeline relies on (safe, repeatable runs).

(c) LIVE-CLUSTER TESTS -- gated behind a real MONGODB_URI in the module .env.
    When absent, they SKIP honestly with an explicit reason rather than failing.

Note: there is deliberately NO test asserting the student's .ipynb exists —
this capstone is documented-only, and the notebook is what the student builds.
"""
import re
from pathlib import Path

import pytest
import mongomock

# ---------------------------------------------------------------------------
# Paths to this lab's artifacts
# ---------------------------------------------------------------------------

LAB_DIR = Path(__file__).resolve().parent
MD_PATH = LAB_DIR / "lab-agent-memory-service.md"
ASSIGNMENT_PATH = LAB_DIR / "lab-agent-memory-service-assignment.md"
README_PATH = LAB_DIR / "README.md"

ENV_PATH = LAB_DIR.parent / ".env"

INSTALL_LINE = (
    '!pip install -qU "pymongo[srv,tls]==4.10.1" python-dotenv==1.0.1 certifi'
)

EXPECTED_PINS = ["pymongo[srv,tls]==4.10.1", "python-dotenv==1.0.1", "certifi"]

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

LAB7_MARKER = "pytest-lab7-"

# The four collections the memory service uses.
COLLECTIONS = ["conversations", "messages", "memories", "tool_calls"]

# Other modules this lab must NOT reference (modules are standalone).
FORBIDDEN_MODULES = ["Audit-DB", "Audit DB", "RAG", "Supabase", "psycopg2", "postgres"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def md_text():
    return MD_PATH.read_text(encoding="utf-8")


def assignment_text():
    return ASSIGNMENT_PATH.read_text(encoding="utf-8")


def readme_text():
    return README_PATH.read_text(encoding="utf-8")


def rubric_points(text):
    """Sum the 'N points' values that appear in a rubric table.

    Mirrors the Audit-DB sum-to-100 check: every rubric category is written as
    'N points', there is no single 'Total' row, so the sum of the category
    values equals the mandatory rubric total (100)."""
    vals = [int(p) for p in re.findall(r"\b(\d{1,3})\s*points?\b", text, re.I)]
    return vals, sum(vals)


def rubric_category_points(text):
    """Extract (category, points) pairs from a rubric / marking table.

    Each category row is written as `| Category | N points | ... |` (the
    category name may be bolded). Returns the mapping with bold/backtick
    decoration stripped."""
    mapping = {}
    # Match a table cell that ends with 'points' and is preceded by a category
    # name cell. This targets the rubric tables specifically.
    lines = text.splitlines()
    for line in lines:
        if line.startswith("|") and "points" in line:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 3:
                cell_name, cell_points = cells[0], cells[1]
                m = re.match(r"(\d{1,3})\s*points?", cell_points, re.I)
                if m:
                    name = re.sub(r"[*`]", "", cell_name).strip()
                    mapping[name] = int(m.group(1))
    return mapping


# ---------------------------------------------------------------------------
# Data-logic helpers (the synthetic seed + tagged cleanup the capstone relies
# on). These are testable against mongomock, unlike live-cluster behavior.
# ---------------------------------------------------------------------------

def seed_conversation(db, conv_id="LAB7CONV001", agent="support-agent"):
    """Insert a clearly-tagged conversation. Idempotent: a pre-existing tagged
    conversation with the same id is replaced so re-runs never accumulate."""
    conv = db["conversations"]
    conv.delete_many({"conversation_id": conv_id, LAB7_MARKER: True})
    conv.insert_one({
        "conversation_id": conv_id,
        "agent": agent,
        "status": "completed",
        LAB7_MARKER: True,
    })
    return conv_id


def seed_message(db, conv_id, msg_id="LAB7MSG001", role="user", content="hi"):
    msg = db["messages"]
    msg.delete_many({"message_id": msg_id, LAB7_MARKER: True})
    msg.insert_one({
        "message_id": msg_id,
        "conversation_id": conv_id,
        "role": role,
        "content": content,
        "tokens": 10,
        LAB7_MARKER: True,
    })
    return msg_id


def cleanup_tagged(db):
    """Remove every tagged document across all four collections.
    Returns the total number of documents deleted."""
    total = 0
    for name in COLLECTIONS:
        total += db[name].delete_many({LAB7_MARKER: True}).deleted_count
    return total


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Fresh mongomock client for every test — ensures test isolation."""
    return mongomock.MongoClient()


@pytest.fixture
def db(client):
    """agent_memory database from a fresh client."""
    return client["agent_memory"]


# ---------------------------------------------------------------------------
# 1. File presence & parseability — always run
# ---------------------------------------------------------------------------

class TestFilesExist:
    def test_md_exists(self):
        assert MD_PATH.exists(), "lab-agent-memory-service.md not found"

    def test_assignment_exists(self):
        assert ASSIGNMENT_PATH.exists(), "lab-agent-memory-service-assignment.md not found"

    def test_readme_exists(self):
        assert README_PATH.exists(), "README.md not found"

    def test_test_file_is_self(self):
        """This test file itself should exist (sanity check)."""
        assert Path(__file__).exists()

    @pytest.mark.parametrize("path", [MD_PATH, ASSIGNMENT_PATH, README_PATH])
    def test_valid_utf8_no_null_bytes(self, path):
        raw = path.read_bytes()
        assert b"\x00" not in raw, f"{path.name} contains null bytes"
        text = raw.decode("utf-8")
        assert text, f"{path.name} decodes but is empty"

    def test_notebook_is_student_built_not_asserted(self):
        """This capstone is documented-only: the notebook is the thing the
        student builds. The harness must not load or assert a notebook — so it
        must not import the modules (json, nbformat, nbconvert) needed to parse
        one — and every provided doc references the notebook as a file the
        student creates."""
        import ast as _ast

        tree = _ast.parse(Path(__file__).read_text(encoding="utf-8"))
        imported = set()
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Import):
                imported.add(node.names[0].name.split(".")[0])
            elif isinstance(node, _ast.ImportFrom):
                if node.module:
                    imported.add(node.module.split(".")[0])
        forbidden = {"json", "nbformat", "nbconvert"}
        assert not (imported & forbidden), (
            f"harness imports notebook-loading module(s): {imported & forbidden}")
        for doc in (md_text(), assignment_text(), readme_text()):
            assert "lab-agent-memory-service.ipynb" in doc, (
                "each provided doc must reference the notebook the student builds")


# ---------------------------------------------------------------------------
# 2. Markdown brief structure — always run
# ---------------------------------------------------------------------------

class TestMarkdownStructure:
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
        between = text[problem_pos + 1:concepts_pos]
        assert "# " not in between, (
            f"Underlying Concepts must be section 2, immediately after the "
            f"Problem Statement. Found another H1 between them: {between[:200]}")

    def test_appendix_a_and_b_exist(self):
        text = md_text()
        assert "# Appendix A" in text, "missing Appendix A"
        assert "# Appendix B" in text, "missing Appendix B"

    def test_markdown_has_at_least_two_mermaid_diagrams(self):
        text = md_text()
        mermaid_count = len(re.findall(r"```mermaid", text))
        assert mermaid_count >= 2, f"need at least 2 Mermaid diagrams, found {mermaid_count}"

    def test_markdown_carries_pinned_versions(self):
        text = md_text()
        for pin in EXPECTED_PINS:
            assert pin in text, f"{pin} must appear in the markdown"
            assert text.count(pin) >= 2, (
                f"{pin} should appear in Tech Stack and Environment Setup "
                f"(at least 2 times)")

    def test_markdown_uses_memory_service_db_name(self):
        """The capstone must NOT keep using school_db — it shifts to a new
        agent-memory database and calls the domain shift out explicitly."""
        assert "agent_memory" in md_text()
        assert "harness" in md_text()

    def test_markdown_has_install_line(self):
        assert INSTALL_LINE in md_text(), ("the exact pinned install line must "
                                           "appear in the markdown")

    def test_markdown_references_env_connection_convention(self):
        text = md_text()
        assert 'load_dotenv("../.env")' in text, "must use ../.env (module root)"
        assert '"MONGODB_URI"' in text or "'MONGODB_URI'" in text
        assert "certifi.where()" in text

    def test_every_lab_1_to_6_required_multiple_times(self):
        """Anti-orphan: Labs 1-6 must each appear MULTIPLE times in the brief
        (prereqs + concept mapping + architecture + rubric), so no lab is
        mentioned once and never actually required."""
        text = md_text()
        for lab_num in [f"Lab {i}" for i in range(1, 7)]:
            count = text.count(lab_num)
            assert count >= 2, (
                f"{lab_num} must appear at least 2 times in the brief "
                f"(prereqs + concept map + rubric); found {count}")

    def test_every_lab_1_to_6_in_rubric(self):
        """Anti-orphan in the rubric: every Lab number must appear in the
        Marking Breakdown section (not just the prose)."""
        text = md_text()
        breakdown = text[text.find("# Marking Breakdown"):]
        for lab_num in [f"Lab {i}" for i in range(1, 7)]:
            assert lab_num in breakdown, f"{lab_num} missing from Marking Breakdown rubric"

    def test_no_hardcoded_credentials(self):
        text = md_text()
        leaks = [m for m in re.findall(r"mongodb(?:\+srv)?://", text)]
        # The only allowed form is the generic placeholder / describe-the-scheme.
        real = [m for m in leaks if "@" not in m]
        # Ensure no user:password@ appears in a connection string.
        assert not re.search(r"mongodb(?:\+srv)?://[^<\s]+:[^<\s]+@", text), (
            "possible credential leak in markdown")

    @pytest.mark.parametrize("path_label", ["md", "assignment"])
    def test_no_cross_module_references(self, path_label):
        """Modules are standalone. No Audit-DB, RAG, Supabase, psycopg2, or
        Postgres references in the brief or assignment."""
        text = md_text() if path_label == "md" else assignment_text()
        fname = "brief" if path_label == "md" else "assignment"
        for term in FORBIDDEN_MODULES:
            assert term not in text, f"{fname} must not reference other modules ({term})"


# ---------------------------------------------------------------------------
# 3. Assignment structure — always run
# ---------------------------------------------------------------------------

class TestAssignmentStructure:
    def test_assignment_contains_mandatory(self):
        assert "Mandatory" in assignment_text(), "assignment must contain 'Mandatory'"

    def test_assignment_contains_deliverables(self):
        assert "Deliverables" in assignment_text(), "assignment must contain 'Deliverables'"

    def test_assignment_contains_rubric(self):
        assert "Rubric" in assignment_text(), "assignment must contain 'Rubric'"

    def test_assignment_contains_success_criteria(self):
        text = assignment_text()
        assert "Success Criteria" in text, "assignment must contain 'Success Criteria'"

    def test_assignment_contains_proposal_stage(self):
        assert "Proposal Stage" in assignment_text(), (
            "assignment must contain 'Proposal Stage'")

    def test_assignment_contains_milestone_checkins(self):
        assert "Milestone" in assignment_text(), "assignment must contain 'Milestone Check-ins'"

    def test_assignment_contains_submission_format(self):
        assert "Submission" in assignment_text(), "assignment must contain 'Submission Format'"

    def test_assignment_contains_project_summary_template(self):
        assert "PROJECT_SUMMARY" in assignment_text(), (
            "assignment must contain PROJECT_SUMMARY.md template")

    def test_assignment_contains_project_summary(self):
        assert "PROJECT_SUMMARY.md" in assignment_text()

    def test_assignment_every_lab_mandatory_requirement(self):
        """Each Lab 1-6 must have at least one concrete Mandatory requirement."""
        text = assignment_text()
        mandatory = text[text.find("# Mandatory"):]
        for lab_num in [f"Lab {i}" for i in range(1, 7)]:
            assert lab_num in mandatory, f"{lab_num} missing from Mandatory requirements"

    def test_assignment_contains_faq(self):
        assert "FAQ" in assignment_text(), "assignment must contain an FAQ"


# ---------------------------------------------------------------------------
# 4. Rubric sums to 100 in BOTH files, and they match
# ---------------------------------------------------------------------------

class TestRubric:
    def test_brief_marking_breakdown_sums_to_100(self):
        vals, total = rubric_points(md_text())
        assert total == 100, f"brief Marking Breakdown must sum to 100, found {total} ({vals})"

    def test_assignment_rubric_sums_to_100(self):
        vals, total = rubric_points(assignment_text())
        assert total == 100, f"assignment rubric must sum to 100, found {total} ({vals})"

    def test_brief_and_assignment_rubrics_match(self):
        brief = rubric_category_points(md_text())
        assign = rubric_category_points(assignment_text())
        assert brief, "could not parse brief rubric categories"
        assert assign, "could not parse assignment rubric categories"
        # Same categories with the same point values in both files.
        assert brief == assign, (
            f"brief and assignment rubrics must match.\nbrief: {brief}\n"
            f"assignment: {assign}")

    def test_all_eight_categories_present(self):
        assign = rubric_category_points(assignment_text())
        assert set(assign.keys()) == {
            "Conversation & message ingestion",
            "Memory extraction & upsert",
            "Recall & schema design",
            "Tool-call history & atomicity",
            "Analytics",
            "Security & continuity",
            "Code quality",
            "Documentation",
        }, f"unexpected rubric categories: {set(assign.keys())}"


# ---------------------------------------------------------------------------
# 5. README structure — always run
# ---------------------------------------------------------------------------

class TestReadme:
    def test_readme_has_file_structure_with_env(self):
        text = readme_text()
        assert ".env" in text, "README must show the .env in the file structure"
        assert 'load_dotenv("../.env")' in text or "MONGODB_URI" in text

    def test_readme_integrates_every_lab(self):
        text = readme_text()
        for lab_num in [f"Lab {i}" for i in range(1, 7)]:
            assert lab_num in text, f"README must list {lab_num} in the integration table"

    def test_readme_rubric_at_a_glance_sums_to_100(self):
        text = readme_text()
        assert "100" in text, "README must show the mandatory total"
        assert "Mandatory total" in text, "README must show the 'Mandatory total' row"


# ---------------------------------------------------------------------------
# 6. Data-logic helpers — mongomock (no DB required)
# ---------------------------------------------------------------------------

class TestSeedAndCleanup:
    def test_seed_inserts_tagged_conversation(self, db):
        seed_conversation(db)
        doc = db["conversations"].find_one({"conversation_id": "LAB7CONV001"})
        assert doc is not None
        assert doc[LAB7_MARKER] is True
        assert doc["agent"] == "support-agent"

    def test_seed_is_idempotent(self, db):
        seed_conversation(db)
        seed_message(db, "LAB7CONV001")
        res = seed_conversation(db)
        assert db["conversations"].count_documents({}) == 1
        assert res == "LAB7CONV001"

    def test_cleanup_removes_all_tagged_docs(self, db):
        seed_conversation(db)
        seed_message(db, "LAB7CONV001")
        removed = cleanup_tagged(db)
        assert removed == 2
        tagged_left = sum(
            db[name].count_documents({LAB7_MARKER: True}) for name in COLLECTIONS)
        assert tagged_left == 0

    def test_cleanup_leaves_untagged_docs(self, db):
        seed_conversation(db)
        # An untagged existing doc from a hypothetical earlier lab.
        db["conversations"].insert_one({"conversation_id": "SCHOOL001", "name": "x"})
        cleanup_tagged(db)
        assert db["conversations"].count_documents({}) == 1
        assert db["conversations"].find_one({"conversation_id": "SCHOOL001"}) is not None

    def test_cleanup_on_empty_collections_returns_zero(self, db):
        assert cleanup_tagged(db) == 0


# ---------------------------------------------------------------------------
# 7. Live-cluster tests (skipped honestly when no MONGODB_URI configured)
# ---------------------------------------------------------------------------

def get_uri():
    if not ENV_PATH.exists():
        return None
    match = re.search(
        r"^\s*MONGODB_URI\s*=\s*(.+)\s*$",
        ENV_PATH.read_text(encoding="utf-8"),
        re.M,
    )
    if not match:
        return None
    return match.group(1).strip().strip('"').strip("'")


def live_client():
    uri = get_uri()
    if not uri:
        return None
    import certifi
    import pymongo
    return pymongo.MongoClient(uri, tlsCAFile=certifi.where())


class TestLiveCluster:
    def test_live_connection_uses_tls(self):
        client = live_client()
        if client is None:
            pytest.skip("MONGODB_URI not configured (.env missing at module "
                        "root) -- live TLS test skipped honestly, not failed")
        try:
            client["agent_memory"].command("ping")
            scheme = get_uri().split("://", 1)[0]
            assert scheme == "mongodb+srv", (
                "mongodb+srv scheme is what requires and enforces TLS")
        finally:
            client.close()

    def test_live_hello_reports_replica_set(self):
        client = live_client()
        if client is None:
            pytest.skip("MONGODB_URI not configured -- live replica-set test "
                        "skipped honestly, not failed")
        try:
            hello = client["agent_memory"].command("hello")
            assert hello.get("setName"), "hello must report a replica-set name"
            assert len(hello.get("hosts", [])) >= 2, (
                "a replica set must have at least 2 hosts")
        finally:
            client.close()
