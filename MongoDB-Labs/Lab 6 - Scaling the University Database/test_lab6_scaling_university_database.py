import json
import re
from pathlib import Path

import pytest
import mongomock

# ---------------------------------------------------------------------------
# Paths to this lab's artifacts
# ---------------------------------------------------------------------------

LAB_DIR = Path(__file__).resolve().parent
NOTEBOOK_PATH = LAB_DIR / "lab-6-scaling-university-database.ipynb"
MD_PATH = LAB_DIR / "lab-6-scaling-university-database.md"
ASSIGNMENT_PATH = LAB_DIR / "lab-6-scaling-university-database-assignment.md"

ENV_PATH = LAB_DIR.parent / ".env"

INSTALL_LINE = (
    '!pip install -qU "pymongo[srv,tls]==4.10.1" python-dotenv==1.0.1 certifi'
)

LAB6_MARKER = "lab6_marker"


def load_notebook():
    return json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))


def code_cells():
    return [c for c in load_notebook()["cells"] if c["cell_type"] == "code"]


def markdown_cells():
    return [c for c in load_notebook()["cells"] if c["cell_type"] == "markdown"]


def md_text():
    return MD_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Data-logic helpers (mirror the notebook's Step 4 / Step 8 seed + cleanup).
# These are testable against mongomock, unlike replica-set / TLS behavior.
# ---------------------------------------------------------------------------

def seed_lab6_doc(students, student_id="LAB6TAG001", name="Replica Read Test"):
    """Insert one clearly-tagged document so there is data to read from a
    secondary. Idempotent: a pre-existing tagged doc with the same id is
    replaced so re-runs never accumulate duplicates."""
    students.delete_many({LAB6_MARKER: True})
    students.insert_one({
        "student_id": student_id,
        "name": name,
        LAB6_MARKER: True,
    })
    return student_id


def cleanup_lab6_docs(students):
    """Remove every tagged document the lab seeded."""
    return students.delete_many({LAB6_MARKER: True}).deleted_count


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Fresh mongomock client for every test — ensures test isolation."""
    return mongomock.MongoClient()


@pytest.fixture
def db(client):
    """school_db database from a fresh client."""
    return client["school_db"]


@pytest.fixture
def students(db):
    """Empty students collection."""
    return db["students"]


# ---------------------------------------------------------------------------
# 1. Notebook structure — no DB required
# ---------------------------------------------------------------------------

class TestNotebookStructure:
    def test_notebook_exists(self):
        assert NOTEBOOK_PATH.exists(), "notebook file missing"

    def test_notebook_is_valid_json(self):
        nb = load_notebook()
        assert "cells" in nb and nb.get("nbformat") == 4

    def test_first_code_cell_is_exact_install_line(self):
        cells = code_cells()
        assert cells, "notebook has no code cells"
        first = "".join(cells[0]["source"]).strip()
        assert first == INSTALL_LINE, (
            "first code cell must be the exact, pinned install line;\n"
            f"got: {first!r}"
        )

    def test_cell_ids_unique_and_non_colliding(self):
        ids = [c["id"] for c in load_notebook()["cells"]]
        assert len(ids) == len(set(ids)), "duplicate cell ids found"
        prefix = re.compile(r"^(md_lab6_\d\d|code_lab6_\d\d)$")
        for cid in ids:
            assert prefix.match(cid), f"cell id {cid!r} does not match md_lab6_NN / code_lab6_NN"

    def test_framing_cell_present(self):
        text = "\n".join(md_text_of(c) for c in markdown_cells())
        assert "We Inspect, We Do Not Provision" in text
        assert "M0" in text

    def test_sharding_step_is_markdown_only(self):
        sharding_md = [c for c in markdown_cells()
                       if "Sharding (Conceptual Only)" in md_text_of(c)]
        assert sharding_md, "Step 7 sharding header (markdown) missing"
        # No code cell may target sharding: the only Sharding content is markdown.
        code_text = "\n".join("".join(c["source"]) for c in code_cells())
        assert "shard" not in code_text.lower(), (
            "Step 7 must be conceptual-only; no code cell may mention sharding"
        )

    def test_has_summary_report_step(self):
        text = "\n".join(md_text_of(c) for c in markdown_cells())
        assert "Summary Report and Cleanup" in text

    def test_notebook_has_no_null_bytes(self):
        raw = NOTEBOOK_PATH.read_bytes()
        assert b"\x00" not in raw, "notebook contains null bytes"


def md_text_of(cell):
    src = cell["source"]
    return "".join(src) if isinstance(src, list) else src


# ---------------------------------------------------------------------------
# 2. Markdown companion — no DB required
# ---------------------------------------------------------------------------

class TestMarkdownCompanion:
    def test_md_exists(self):
        assert MD_PATH.exists()

    def test_md_has_m0_inspect_framing(self):
        text = md_text()
        assert "inspect" in text.lower() and "M0" in text

    def test_md_has_mermaid(self):
        assert "```mermaid" in md_text()

    def test_md_has_what_we_learnt(self):
        assert "What We Learnt" in md_text()

    def test_md_has_step_walkthrough(self):
        assert "Step 1" in md_text() and "Step 8" in md_text()


# ---------------------------------------------------------------------------
# 3. Assignment companion — no DB required
# ---------------------------------------------------------------------------

class TestAssignment:
    def test_assignment_exists(self):
        assert ASSIGNMENT_PATH.exists()

    def test_assignment_has_answer_key(self):
        assert "Answer Key" in ASSIGNMENT_PATH.read_text(encoding="utf-8")

    def test_assignment_covers_required_topics(self):
        text = ASSIGNMENT_PATH.read_text(encoding="utf-8")
        for topic in ["replica set", "secondary", "read preference",
                      "TLS", "built-in role", "shard"]:
            assert topic.lower() in text.lower(), f"assignment missing topic: {topic}"


# ---------------------------------------------------------------------------
# 4. Data-logic helpers — mongomock
# ---------------------------------------------------------------------------

class TestSeedAndCleanup:
    def test_seed_inserts_tagged_doc(self, students):
        seed_lab6_doc(students)
        doc = students.find_one({"student_id": "LAB6TAG001"})
        assert doc is not None
        assert doc[LAB6_MARKER] is True
        assert doc["name"] == "Replica Read Test"

    def test_seed_is_idempotent(self, students):
        seed_lab6_doc(students)
        seed_lab6_doc(students)
        desc = seed_lab6_doc(students)
        assert students.count_documents({}) == 1
        assert desc == "LAB6TAG001"

    def test_cleanup_removes_all_tagged_docs(self, students):
        seed_lab6_doc(students)
        students.insert_one({"student_id": "X", LAB6_MARKER: True})
        removed = cleanup_lab6_docs(students)
        assert removed == 2
        assert students.count_documents({LAB6_MARKER: True}) == 0

    def test_cleanup_leaves_untagged_docs(self, students):
        seed_lab6_doc(students)
        students.insert_one({"student_id": "STU001", "name": "Alice"})
        cleanup_lab6_docs(students)
        assert students.count_documents({}) == 1
        assert students.find_one({"student_id": "STU001", "name": "Alice"}) is not None

    def test_cleanup_on_empty_collection_returns_zero(self, students):
        assert cleanup_lab6_docs(students) == 0


# ---------------------------------------------------------------------------
# 5. Live replica-set / TLS assertions
#
# These CANNOT be exercised through mongomock, so they are gated behind a
# live MONGODB_URI. When no live URI is configured, they SKIP cleanly with an
# explicit reason (the same honest-skip pattern the Audit-DB tests use) —
# they never fail simply because there is no live cluster to run against.
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


class TestLiveReplicaSetAndTLS:
    def test_live_hello_reports_replica_set(self):
        client = live_client()
        if client is None:
            pytest.skip("MONGODB_URI not configured (.env missing at module "
                        "root) -- live replica-set tests skipped honestly, "
                        "not failed")
        try:
            hello = client["school_db"].command("hello")
            assert hello.get("setName"), "hello must report a replica-set name"
            assert len(hello.get("hosts", [])) >= 2, (
                "a replica set must have at least 2 hosts"
            )
            assert hello.get("primary"), "hello must name a primary"
        finally:
            client.close()

    def test_live_client_sees_multiple_nodes(self):
        client = live_client()
        if client is None:
            pytest.skip("MONGODB_URI not configured -- live replica-set tests "
                        "skipped honestly, not failed")
        try:
            client.admin.command("ping")
            assert len(client.nodes) >= 2, (
                "driver should discover multiple replica-set nodes"
            )
        finally:
            client.close()

    def test_live_connection_uses_tls(self):
        client = live_client()
        if client is None:
            pytest.skip("MONGODB_URI not configured -- live TLS tests skipped "
                        "honestly, not failed")
        try:
            client.admin.command("ping")
            scheme = get_uri().split("://", 1)[0]
            assert scheme == "mongodb+srv", (
                "mongodb+srv scheme is what requires and enforces TLS"
            )
        finally:
            client.close()
