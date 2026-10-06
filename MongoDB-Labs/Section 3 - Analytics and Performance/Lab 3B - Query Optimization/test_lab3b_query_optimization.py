import random
import datetime as dt

import pytest
import mongomock

# NOTE: mongomock cannot produce real execution plans, so these tests cover
# everything *around* explain(): data generation, query correctness, index
# definitions, the ESR helper, covered-query projections and aggregation results.
# The explain() output itself is verified by running the notebook against Atlas.


# ---------------------------------------------------------------------------
# Re-implementation of the notebook helpers (same logic, smaller N for speed)
# ---------------------------------------------------------------------------

COURSES = ["Computer Science", "Mathematics", "Physics", "English", "Biology"]
STATUSES = ["active", "completed", "withdrawn", "pending"]
WEIGHTS = [60, 25, 10, 5]
SEMESTERS = ["2024-Fall", "2025-Spring", "2025-Fall", "2026-Spring"]
START = dt.datetime(2024, 9, 1)


def generate(n, seed=42):
    rng = random.Random(seed)
    docs = []
    for i in range(n):
        docs.append({
            "record_id": i,
            "student_id": f"STU{rng.randint(1, 5000):05d}",
            "course": rng.choice(COURSES),
            "semester": rng.choice(SEMESTERS),
            "status": rng.choices(STATUSES, weights=WEIGHTS)[0],
            "grade": rng.randint(35, 100),
            "credits": rng.choice([2, 3, 4]),
            "submitted_at": START + dt.timedelta(minutes=rng.randint(0, 60 * 24 * 600)),
            "notes": "x" * 40,
        })
    return docs


def esr_index(equality, sort, range_fields=()):
    return [(f, 1) for f in equality] + list(sort) + [(f, 1) for f in range_fields]


def collect_stages(node, found=None):
    found = [] if found is None else found
    if isinstance(node, dict):
        if "stage" in node:
            found.append(node["stage"])
        for value in node.values():
            collect_stages(value, found)
    elif isinstance(node, list):
        for value in node:
            collect_stages(value, found)
    return found


@pytest.fixture
def log():
    client = mongomock.MongoClient()
    coll = client["school_db"]["enrollment_log"]
    coll.insert_many(generate(3000))
    return coll


# ---------------------------------------------------------------------------
# 1. Data generation
# ---------------------------------------------------------------------------

class TestDataGeneration:
    def test_count(self, log):
        assert log.count_documents({}) == 3000

    def test_required_fields(self, log):
        required = {"record_id", "student_id", "course", "semester", "status",
                    "grade", "credits", "submitted_at", "notes"}
        assert required.issubset(log.find_one().keys())

    def test_generation_is_deterministic(self):
        assert generate(200) == generate(200)

    def test_different_seed_differs(self):
        assert generate(200, seed=1) != generate(200, seed=2)

    def test_values_within_expected_domains(self, log):
        for d in log.find():
            assert d["course"] in COURSES
            assert d["status"] in STATUSES
            assert d["semester"] in SEMESTERS
            assert 35 <= d["grade"] <= 100
            assert d["credits"] in (2, 3, 4)

    def test_status_distribution_roughly_matches_weights(self, log):
        active = log.count_documents({"status": "active"})
        assert 0.52 * 3000 < active < 0.68 * 3000

    def test_record_ids_unique(self, log):
        assert len(log.distinct("record_id")) == 3000


# ---------------------------------------------------------------------------
# 2. ESR helper
# ---------------------------------------------------------------------------

class TestEsrHelper:
    def test_equality_then_sort(self):
        assert esr_index(["course", "status"], [("grade", -1)]) == [("course", 1), ("status", 1), ("grade", -1)]

    def test_equality_sort_range_order(self):
        keys = esr_index(["course"], [("submitted_at", -1)], ["grade"])
        assert [k for k, _ in keys] == ["course", "submitted_at", "grade"]

    def test_range_always_last(self):
        keys = esr_index(["a", "b"], [("c", 1)], ["d", "e"])
        assert [k for k, _ in keys][-2:] == ["d", "e"]

    def test_sort_direction_preserved(self):
        keys = esr_index(["a"], [("b", -1)])
        assert keys[-1] == ("b", -1)

    def test_no_sort_no_range(self):
        assert esr_index(["a"], []) == [("a", 1)]


# ---------------------------------------------------------------------------
# 3. Query 1 correctness (with and without the index)
# ---------------------------------------------------------------------------

FILTER_Q1 = {"course": "Computer Science", "status": "active"}


def query1(log):
    return list(log.find(FILTER_Q1, {"_id": 0, "student_id": 1, "grade": 1}).sort("grade", -1).limit(20))


class TestQuery1:
    def test_returns_twenty(self, log):
        assert len(query1(log)) == 20

    def test_sorted_descending(self, log):
        grades = [d["grade"] for d in query1(log)]
        assert grades == sorted(grades, reverse=True)

    def test_matches_python_reference(self, log):
        expected = sorted((d["grade"] for d in log.find(FILTER_Q1)), reverse=True)[:20]
        assert [d["grade"] for d in query1(log)] == expected

    def test_same_grades_before_and_after_index(self, log):
        before = [d["grade"] for d in query1(log)]
        log.create_index(esr_index(["course", "status"], [("grade", -1)]), name="esr_course_status_grade")
        after = [d["grade"] for d in query1(log)]
        assert before == after

    def test_index_registered_with_expected_keys(self, log):
        log.create_index(esr_index(["course", "status"], [("grade", -1)]), name="esr_course_status_grade")
        info = log.index_information()
        assert "esr_course_status_grade" in info
        assert info["esr_course_status_grade"]["key"] == [("course", 1), ("status", 1), ("grade", -1)]

    def test_projection_excludes_id(self, log):
        assert "_id" not in query1(log)[0]


# ---------------------------------------------------------------------------
# 4. Query 2 and index field order
# ---------------------------------------------------------------------------

FILTER_Q2 = {"course": "Physics", "grade": {"$gte": 90}}


class TestQuery2:
    def test_only_physics_and_high_grades(self, log):
        for d in log.find(FILTER_Q2).sort("submitted_at", -1).limit(10):
            assert d["course"] == "Physics" and d["grade"] >= 90

    def test_sorted_newest_first(self, log):
        dates = [d["submitted_at"] for d in log.find(FILTER_Q2).sort("submitted_at", -1).limit(10)]
        assert dates == sorted(dates, reverse=True)

    def test_both_index_orders_return_identical_results(self, log):
        base = [d["record_id"] for d in log.find(FILTER_Q2).sort("submitted_at", -1).limit(10)]
        log.create_index([("course", 1), ("grade", 1), ("submitted_at", -1)], name="ers")
        a = [d["record_id"] for d in log.find(FILTER_Q2).sort("submitted_at", -1).limit(10)]
        log.drop_index("ers")
        log.create_index([("course", 1), ("submitted_at", -1), ("grade", 1)], name="esr")
        b = [d["record_id"] for d in log.find(FILTER_Q2).sort("submitted_at", -1).limit(10)]
        assert base == a == b

    def test_drop_index_removes_it(self, log):
        log.create_index([("course", 1), ("grade", 1)], name="tmp")
        log.drop_index("tmp")
        assert "tmp" not in log.index_information()

    def test_esr_order_has_sort_before_range(self):
        keys = esr_index(["course"], [("submitted_at", -1)], ["grade"])
        names = [k for k, _ in keys]
        assert names.index("submitted_at") < names.index("grade")


# ---------------------------------------------------------------------------
# 5. Covered query
# ---------------------------------------------------------------------------

class TestCoveredQuery:
    PROJECTION = {"_id": 0, "course": 1, "status": 1, "grade": 1}

    def test_projection_only_indexed_fields(self, log):
        docs = list(log.find({"course": "Biology", "status": "completed"}, self.PROJECTION))
        assert docs
        for d in docs:
            assert set(d.keys()) == {"course", "status", "grade"}

    def test_uncovered_projection_returns_extra_field(self, log):
        d = log.find_one({"course": "Biology"}, {"_id": 0, "course": 1, "notes": 1})
        assert "notes" in d

    def test_covered_query_filter_is_respected(self, log):
        for d in log.find({"course": "Biology", "status": "completed"}, self.PROJECTION):
            assert d["course"] == "Biology" and d["status"] == "completed"

    def test_count_matches_python(self, log):
        expected = sum(1 for d in log.find() if d["course"] == "Biology" and d["status"] == "completed")
        assert len(list(log.find({"course": "Biology", "status": "completed"}, self.PROJECTION))) == expected


# ---------------------------------------------------------------------------
# 6. Aggregation: slice vs all
# ---------------------------------------------------------------------------

GROUP = {"$group": {"_id": "$course", "avg_grade": {"$avg": "$grade"}, "n": {"$sum": 1}}}


class TestAggregation:
    def test_all_courses_present(self, log):
        result = {d["_id"] for d in log.aggregate([GROUP])}
        assert result == set(COURSES)

    def test_counts_sum_to_total(self, log):
        assert sum(d["n"] for d in log.aggregate([GROUP])) == 3000

    def test_sorted_descending(self, log):
        avgs = [d["avg_grade"] for d in log.aggregate([GROUP, {"$sort": {"avg_grade": -1}}])]
        assert avgs == sorted(avgs, reverse=True)

    def test_matched_slice_counts_correct(self, log):
        pipeline = [{"$match": {"semester": "2026-Spring", "status": "completed"}}, GROUP]
        got = sum(d["n"] for d in log.aggregate(pipeline))
        expected = sum(1 for d in log.find() if d["semester"] == "2026-Spring" and d["status"] == "completed")
        assert got == expected

    def test_slice_is_smaller_than_whole(self, log):
        whole = sum(d["n"] for d in log.aggregate([GROUP]))
        part = sum(d["n"] for d in log.aggregate([{"$match": {"semester": "2026-Spring", "status": "completed"}}, GROUP]))
        assert 0 < part < whole

    def test_average_matches_python(self, log):
        pipeline = [{"$match": {"course": "Physics"}}, {"$group": {"_id": None, "avg": {"$avg": "$grade"}}}]
        got = list(log.aggregate(pipeline))[0]["avg"]
        grades = [d["grade"] for d in log.find({"course": "Physics"})]
        assert abs(got - sum(grades) / len(grades)) < 1e-9


# ---------------------------------------------------------------------------
# 7. Plan-reading helper
# ---------------------------------------------------------------------------

class TestCollectStages:
    def test_flat_plan(self):
        assert collect_stages({"stage": "COLLSCAN"}) == ["COLLSCAN"]

    def test_nested_plan_outermost_first(self):
        plan = {"stage": "SORT", "inputStage": {"stage": "FETCH", "inputStage": {"stage": "IXSCAN"}}}
        assert collect_stages(plan) == ["SORT", "FETCH", "IXSCAN"]

    def test_plan_with_list_of_inputs(self):
        plan = {"stage": "OR", "inputStages": [{"stage": "IXSCAN"}, {"stage": "IXSCAN"}]}
        assert collect_stages(plan) == ["OR", "IXSCAN", "IXSCAN"]

    def test_empty_plan(self):
        assert collect_stages({}) == []

    def test_detects_sort(self):
        stages = collect_stages({"stage": "SORT", "inputStage": {"stage": "COLLSCAN"}})
        assert any("SORT" in s for s in stages)


# ---------------------------------------------------------------------------
# 8. Index-usage helpers (pure logic on $indexStats-shaped rows)
# ---------------------------------------------------------------------------

def unused(rows):
    return [r["name"] for r in rows if r["accesses"]["ops"] == 0 and r["name"] != "_id_"]


class TestUnusedIndexLogic:
    ROWS = [
        {"name": "_id_", "accesses": {"ops": 0}},
        {"name": "esr_course_status_grade", "accesses": {"ops": 12}},
        {"name": "idx_notes_unused", "accesses": {"ops": 0}},
    ]

    def test_finds_unused(self):
        assert unused(self.ROWS) == ["idx_notes_unused"]

    def test_never_flags_id_index(self):
        assert "_id_" not in unused(self.ROWS)

    def test_none_unused(self):
        rows = [{"name": "a", "accesses": {"ops": 3}}]
        assert unused(rows) == []
