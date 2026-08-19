import pytest
import mongomock


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
def empty_collection(db):
    """Empty students collection — no documents inserted."""
    return db["students"]


STUDENT_RECORDS = [
    {"name": "Alice Johnson",  "student_id": "STU001", "course": "Computer Science", "grade": 95, "enrollment_date": "2024-09-01", "status": "active"},
    {"name": "Bob Smith",      "student_id": "STU002", "course": "Mathematics",      "grade": 78, "enrollment_date": "2024-09-01", "status": "active"},
    {"name": "Charlie Brown",  "student_id": "STU003", "course": "Physics",          "grade": 55, "enrollment_date": "2024-09-02", "status": "active"},
    {"name": "Diana Prince",   "student_id": "STU004", "course": "English",          "grade": 48, "enrollment_date": "2024-09-01", "status": "active"},
    {"name": "Eve Torres",     "student_id": "STU005", "course": "Biology",          "grade": 88, "enrollment_date": "2024-09-03", "status": "active"},
    {"name": "Frank Castle",   "student_id": "STU006", "course": "Mathematics",      "grade": 52, "enrollment_date": "2024-09-01", "status": "inactive"},
    {"name": "Grace Hopper",   "student_id": "STU007", "course": "Computer Science", "grade": 91, "enrollment_date": "2024-09-02", "status": "active"},
    {"name": "Hank Pym",       "student_id": "STU008", "course": "Physics",          "grade": 73, "enrollment_date": "2024-09-01", "status": "active"},
    {"name": "Ivan Petrov",    "student_id": "STU009", "course": "Computer Science", "grade": 84, "enrollment_date": "2024-09-03", "status": "active"},
    {"name": "Julia Child",    "student_id": "STU010", "course": "English",          "grade": 90, "enrollment_date": "2024-09-02", "status": "graduated"},
    {"name": "Karl Marx",      "student_id": "STU011", "course": "Mathematics",      "grade": 67, "enrollment_date": "2024-09-01", "status": "active"},
    {"name": "Laura Palmer",   "student_id": "STU012", "course": "Biology",          "grade": 45, "enrollment_date": "2024-09-02", "status": "active"},
    {"name": "Marco Polo",     "student_id": "STU013", "course": "Physics",          "grade": 82, "enrollment_date": "2024-09-03", "status": "active"},
    {"name": "Nina Simone",    "student_id": "STU014", "course": "English",          "grade": 76, "enrollment_date": "2024-09-01", "status": "active"},
    {"name": "Oscar Wilde",    "student_id": "STU015", "course": "Mathematics",      "grade": 93, "enrollment_date": "2024-09-02", "status": "active"},
    {"name": "Pia Zadora",     "student_id": "STU016", "course": "Biology",          "grade": 71, "enrollment_date": "2024-09-01", "status": "active"},
    {"name": "Quincy Adams",   "student_id": "STU017", "course": "Computer Science", "grade": 87, "enrollment_date": "2024-09-03", "status": "active"},
    {"name": "Rosa Parks",     "student_id": "STU018", "course": "English",          "grade": 58, "enrollment_date": "2024-09-02", "status": "inactive"},
    {"name": "Sam Wilson",     "student_id": "STU019", "course": "Physics",          "grade": 98, "enrollment_date": "2024-09-01", "status": "active"},
    {"name": "Tina Turner",    "student_id": "STU020", "course": "Mathematics",      "grade": 79, "enrollment_date": "2024-09-03", "status": "active"},
    {"name": "Uma Thurman",    "student_id": "STU021", "course": "Computer Science", "grade": 62, "enrollment_date": "2024-09-02", "status": "active"},
    {"name": "Vera Wang",      "student_id": "STU022", "course": "Biology",          "grade": 85, "enrollment_date": "2024-09-01", "status": "graduated"},
    {"name": "Walt Disney",    "student_id": "STU023", "course": "Physics",          "grade": 56, "enrollment_date": "2024-09-02", "status": "active"},
    {"name": "Xena Warrior",   "student_id": "STU024", "course": "English",          "grade": 94, "enrollment_date": "2024-09-03", "status": "active"},
    {"name": "Yusuf Islam",    "student_id": "STU025", "course": "Computer Science", "grade": 70, "enrollment_date": "2024-09-01", "status": "active"},
]


@pytest.fixture
def populated(empty_collection):
    """Students collection with all 25 records inserted."""
    result = empty_collection.insert_many(STUDENT_RECORDS)
    return empty_collection, len(result.inserted_ids)


# ---------------------------------------------------------------------------
# 1. Connection
# ---------------------------------------------------------------------------

class TestConnection:
    def test_client_creates_successfully(self, client):
        assert client is not None

    def test_database_accessible(self, db):
        assert db is not None

    def test_collection_accessible(self, empty_collection):
        assert empty_collection is not None


# ---------------------------------------------------------------------------
# 2. Insert Records
# ---------------------------------------------------------------------------

class TestInsertRecords:
    def test_insert_count_matches(self, populated):
        collection, count = populated
        assert count == 25

    def test_total_documents_in_collection(self, populated):
        collection, _ = populated
        assert collection.count_documents({}) == 25

    def test_document_has_all_required_fields(self, populated):
        collection, _ = populated
        first = collection.find_one()
        required = {"name", "student_id", "course", "grade", "enrollment_date", "status"}
        assert required.issubset(first.keys())

    def test_student_ids_are_unique(self, populated):
        collection, _ = populated
        all_ids = [s["student_id"] for s in collection.find({}, {"_id": 0})]
        assert len(all_ids) == len(set(all_ids))

    def test_grades_within_valid_range(self, populated):
        collection, _ = populated
        grades = [s["grade"] for s in collection.find({}, {"_id": 0})]
        assert all(0 <= g <= 100 for g in grades)


# ---------------------------------------------------------------------------
# 3. Query: Failing Students (grade < 60)
# ---------------------------------------------------------------------------

class TestQueryFailingStudents:
    def test_count_of_failing_students(self, populated):
        collection, _ = populated
        failing = list(collection.find({"grade": {"$lt": 60}}, {"_id": 0}))
        assert len(failing) == 6

    def test_failing_student_names_match(self, populated):
        collection, _ = populated
        names = [s["name"] for s in collection.find({"grade": {"$lt": 60}}, {"_id": 0})]
        expected = {"Charlie Brown", "Diana Prince", "Frank Castle",
                    "Laura Palmer", "Rosa Parks", "Walt Disney"}
        assert set(names) == expected

    def test_all_failing_grades_below_60(self, populated):
        collection, _ = populated
        failing = list(collection.find({"grade": {"$lt": 60}}, {"_id": 0}))
        assert all(s["grade"] < 60 for s in failing)

    def test_grade_60_is_not_failing(self, populated):
        """Boundary: grade exactly 60 should NOT appear in failing results."""
        collection, _ = populated
        collection.insert_one(
            {"name": "Boundary Test", "student_id": "STU099",
             "course": "Math", "grade": 60, "enrollment_date": "2024-09-01",
             "status": "active"}
        )
        failing = list(collection.find({"grade": {"$lt": 60}}, {"_id": 0}))
        names = [s["name"] for s in failing]
        assert "Boundary Test" not in names


# ---------------------------------------------------------------------------
# 4. Query: CS Students Sorted by Grade
# ---------------------------------------------------------------------------

class TestQueryCSStudentsSorted:
    def test_cs_student_count(self, populated):
        collection, _ = populated
        cs = list(collection.find({"course": "Computer Science"}, {"_id": 0}))
        assert len(cs) == 6

    def test_cs_sorted_descending_by_grade(self, populated):
        collection, _ = populated
        cs = list(collection.find({"course": "Computer Science"}, {"_id": 0}).sort("grade", -1))
        grades = [s["grade"] for s in cs]
        assert grades == sorted(grades, reverse=True)

    def test_top_cs_student_is_alice(self, populated):
        collection, _ = populated
        top = collection.find({"course": "Computer Science"}, {"_id": 0}).sort("grade", -1).limit(1)[0]
        assert top["name"] == "Alice Johnson"
        assert top["grade"] == 95

    def test_nonexistent_course_returns_empty(self, populated):
        """Querying a course that doesn't exist should return no results."""
        collection, _ = populated
        results = list(collection.find({"course": "Chemistry"}, {"_id": 0}))
        assert len(results) == 0


# ---------------------------------------------------------------------------
# 5. Aggregation: Enrollment Count by Course
# ---------------------------------------------------------------------------

class TestAggregationEnrollment:
    def test_all_five_courses_present(self, populated):
        collection, _ = populated
        pipeline = [
            {"$group": {"_id": "$course", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        results = {doc["_id"]: doc["count"] for doc in collection.aggregate(pipeline)}
        assert set(results.keys()) == {"Computer Science", "English",
                                       "Mathematics", "Physics", "Biology"}

    def test_cs_enrollment_is_six(self, populated):
        collection, _ = populated
        pipeline = [{"$group": {"_id": "$course", "count": {"$sum": 1}}}]
        results = {doc["_id"]: doc["count"] for doc in collection.aggregate(pipeline)}
        assert results["Computer Science"] == 6

    def test_total_enrollment_sums_to_25(self, populated):
        collection, _ = populated
        pipeline = [{"$group": {"_id": "$course", "count": {"$sum": 1}}}]
        total = sum(doc["count"] for doc in collection.aggregate(pipeline))
        assert total == 25

    def test_each_course_has_at_least_one_student(self, populated):
        collection, _ = populated
        pipeline = [{"$group": {"_id": "$course", "count": {"$sum": 1}}}]
        for doc in collection.aggregate(pipeline):
            assert doc["count"] >= 1, f"{doc['_id']} has {doc['count']} students"


# ---------------------------------------------------------------------------
# 6. Projection
# ---------------------------------------------------------------------------

class TestProjection:
    def test_id_excluded_from_results(self, populated):
        collection, _ = populated
        result = collection.find_one({}, {"_id": 0})
        assert "_id" not in result

    def test_specific_fields_only(self, populated):
        collection, _ = populated
        result = collection.find_one({}, {"_id": 0, "name": 1, "grade": 1})
        assert "name" in result
        assert "grade" in result
        assert "course" not in result
        assert "status" not in result


# ---------------------------------------------------------------------------
# 7. Summary Report Logic
# ---------------------------------------------------------------------------

class TestSummaryReport:
    def test_total_count_is_25(self, populated):
        collection, _ = populated
        assert collection.count_documents({}) == 25

    def test_failing_count_is_6(self, populated):
        collection, _ = populated
        failing = list(collection.find({"grade": {"$lt": 60}}, {"_id": 0}))
        assert len(failing) == 6

    def test_top_cs_is_alice_with_95(self, populated):
        collection, _ = populated
        top_cs = list(collection.find({"course": "Computer Science"}, {"_id": 0}).sort("grade", -1))
        assert len(top_cs) > 0
        assert top_cs[0]["name"] == "Alice Johnson"
        assert top_cs[0]["grade"] == 95


# ---------------------------------------------------------------------------
# 8. Status Values
# ---------------------------------------------------------------------------

class TestStatusValues:
    def test_only_valid_statuses_exist(self, populated):
        collection, _ = populated
        valid = {"active", "inactive", "graduated"}
        statuses = set(s["status"] for s in collection.find({}, {"_id": 0}))
        assert statuses.issubset(valid)

    def test_active_is_majority(self, populated):
        collection, _ = populated
        active_count = collection.count_documents({"status": "active"})
        assert active_count > 10  # most students should be active


# ---------------------------------------------------------------------------
# 9. Edge Cases & Idempotency
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_collection_query_returns_nothing(self, empty_collection):
        results = list(empty_collection.find({}, {"_id": 0}))
        assert len(results) == 0

    def test_empty_collection_count_is_zero(self, empty_collection):
        assert empty_collection.count_documents({}) == 0

    def test_drop_clears_all_documents(self, populated):
        """Reproduces the notebook's drop() + re-insert idempotency pattern."""
        collection, _ = populated
        assert collection.count_documents({}) == 25
        collection.drop()
        assert collection.count_documents({}) == 0

    def test_drop_and_reinsert_gives_same_count(self, populated):
        """Drop then re-insert should produce exactly 25 documents, not 50."""
        collection, _ = populated
        collection.drop()
        collection.insert_many(STUDENT_RECORDS)
        assert collection.count_documents({}) == 25

    def test_query_after_drop_returns_empty(self, populated):
        collection, _ = populated
        collection.drop()
        failing = list(collection.find({"grade": {"$lt": 60}}, {"_id": 0}))
        assert len(failing) == 0

    def test_insert_one_and_query(self, empty_collection):
        """Single insert should be queryable."""
        empty_collection.insert_one(
            {"name": "Solo Student", "student_id": "STU100",
             "course": "Physics", "grade": 75, "enrollment_date": "2024-09-01",
             "status": "active"}
        )
        result = empty_collection.find_one({"name": "Solo Student"}, {"_id": 0})
        assert result is not None
        assert result["grade"] == 75
