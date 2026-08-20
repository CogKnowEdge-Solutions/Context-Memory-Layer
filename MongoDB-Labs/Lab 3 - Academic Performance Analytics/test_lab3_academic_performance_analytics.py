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


# ---------------------------------------------------------------------------
# 3. Aggregation: Average Grade per Course
# ---------------------------------------------------------------------------

class TestAggregationAvgGrade:
    def test_all_five_courses_present(self, populated):
        collection, _ = populated
        pipeline = [
            {"$group": {"_id": "$course", "avg_grade": {"$avg": "$grade"}}},
        ]
        results = {doc["_id"]: doc["avg_grade"] for doc in collection.aggregate(pipeline)}
        assert set(results.keys()) == {"Computer Science", "English",
                                       "Mathematics", "Physics", "Biology"}

    def test_cs_average_is_81_5(self, populated):
        collection, _ = populated
        pipeline = [
            {"$group": {"_id": "$course", "avg_grade": {"$avg": "$grade"}}},
        ]
        results = {doc["_id"]: doc["avg_grade"] for doc in collection.aggregate(pipeline)}
        assert abs(results["Computer Science"] - 81.5) < 0.01

    def test_overall_average_matches_manual(self, populated):
        collection, _ = populated
        pipeline = [{"$group": {"_id": None, "avg": {"$avg": "$grade"}}}]
        result = list(collection.aggregate(pipeline))[0]
        all_grades = [s["grade"] for s in collection.find({}, {"_id": 0})]
        expected = sum(all_grades) / len(all_grades)
        assert abs(result["avg"] - expected) < 0.01

    def test_sorted_descending_by_avg(self, populated):
        collection, _ = populated
        pipeline = [
            {"$group": {"_id": "$course", "avg_grade": {"$avg": "$grade"}}},
            {"$sort": {"avg_grade": -1}}
        ]
        avgs = [doc["avg_grade"] for doc in collection.aggregate(pipeline)]
        assert avgs == sorted(avgs, reverse=True)

    def test_each_course_has_correct_student_count(self, populated):
        collection, _ = populated
        pipeline = [
            {"$group": {"_id": "$course", "count": {"$sum": 1}}}
        ]
        counts = {doc["_id"]: doc["count"] for doc in collection.aggregate(pipeline)}
        assert counts["Computer Science"] == 6
        assert counts["Mathematics"] == 5
        assert counts["Physics"] == 5
        assert counts["English"] == 5
        assert counts["Biology"] == 4


# ---------------------------------------------------------------------------
# 4. Aggregation: Grade Distribution ($bucket)
# ---------------------------------------------------------------------------

class TestGradeDistribution:
    def test_bucket_returns_five_groups(self, populated):
        collection, _ = populated
        pipeline = [
            {"$bucket": {
                "groupBy": "$grade",
                "boundaries": [0, 60, 70, 80, 90, 101],
                "output": {"count": {"$sum": 1}}
            }}
        ]
        results = list(collection.aggregate(pipeline))
        assert len(results) == 5

    def test_failing_bucket_count_is_six(self, populated):
        collection, _ = populated
        pipeline = [
            {"$bucket": {
                "groupBy": "$grade",
                "boundaries": [0, 60, 70, 80, 90, 101],
                "output": {"count": {"$sum": 1}}
            }}
        ]
        results = {doc["_id"]: doc["count"] for doc in collection.aggregate(pipeline)}
        assert results[0] == 6

    def test_a_bucket_count_is_six(self, populated):
        collection, _ = populated
        pipeline = [
            {"$bucket": {
                "groupBy": "$grade",
                "boundaries": [0, 60, 70, 80, 90, 101],
                "output": {"count": {"$sum": 1}}
            }}
        ]
        results = {doc["_id"]: doc["count"] for doc in collection.aggregate(pipeline)}
        assert results[90] == 6

    def test_total_across_buckets_is_25(self, populated):
        collection, _ = populated
        pipeline = [
            {"$bucket": {
                "groupBy": "$grade",
                "boundaries": [0, 60, 70, 80, 90, 101],
                "output": {"count": {"$sum": 1}}
            }}
        ]
        total = sum(doc["count"] for doc in collection.aggregate(pipeline))
        assert total == 25


# ---------------------------------------------------------------------------
# 5. Indexing
# ---------------------------------------------------------------------------

class TestIndexing:
    def test_create_index_on_course(self, populated):
        collection, _ = populated
        collection.create_index("course")
        indexes = collection.index_information()
        # mongomock creates an index entry; verify at least one non-_id index exists
        non_id = [k for k in indexes if k != "_id_"]
        assert len(non_id) >= 1

    def test_query_with_index_returns_correct_results(self, populated):
        collection, _ = populated
        collection.create_index("course")
        results = list(collection.find({"course": "Physics"}, {"_id": 0}))
        assert len(results) == 5
        assert all(s["course"] == "Physics" for s in results)

    def test_drop_index_reduces_count(self, populated):
        collection, _ = populated
        idx = collection.create_index("course")
        before = len(collection.index_information())
        collection.drop_index(idx)
        after = len(collection.index_information())
        assert after < before


# ---------------------------------------------------------------------------
# 6. Pipeline Filtering ($match after $group)
# ---------------------------------------------------------------------------

class TestPipelineFilter:
    def test_courses_above_75_average(self, populated):
        collection, _ = populated
        pipeline = [
            {"$group": {"_id": "$course", "avg_grade": {"$avg": "$grade"}}},
            {"$match": {"avg_grade": {"$gt": 75}}}
        ]
        results = list(collection.aggregate(pipeline))
        assert all(doc["avg_grade"] > 75 for doc in results)

    def test_cs_above_75_is_included(self, populated):
        collection, _ = populated
        pipeline = [
            {"$group": {"_id": "$course", "avg_grade": {"$avg": "$grade"}}},
            {"$match": {"avg_grade": {"$gt": 75}}}
        ]
        names = [doc["_id"] for doc in collection.aggregate(pipeline)]
        assert "Computer Science" in names


# ---------------------------------------------------------------------------
# 7. Max/Min per Course
# ---------------------------------------------------------------------------

class TestMaxMinPerCourse:
    def test_cs_max_is_95(self, populated):
        collection, _ = populated
        pipeline = [
            {"$group": {"_id": "$course", "max_grade": {"$max": "$grade"}}}
        ]
        results = {doc["_id"]: doc["max_grade"] for doc in collection.aggregate(pipeline)}
        assert results["Computer Science"] == 95

    def test_cs_min_is_62(self, populated):
        collection, _ = populated
        pipeline = [
            {"$group": {"_id": "$course", "min_grade": {"$min": "$grade"}}}
        ]
        results = {doc["_id"]: doc["min_grade"] for doc in collection.aggregate(pipeline)}
        assert results["Computer Science"] == 62


# ---------------------------------------------------------------------------
# 8. Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_collection_aggregation_returns_nothing(self, empty_collection):
        pipeline = [
            {"$group": {"_id": "$course", "avg_grade": {"$avg": "$grade"}}}
        ]
        results = list(empty_collection.aggregate(pipeline))
        assert len(results) == 0

    def test_empty_collection_bucket_returns_nothing(self, empty_collection):
        pipeline = [
            {"$bucket": {
                "groupBy": "$grade",
                "boundaries": [0, 60, 70, 80, 90, 101],
                "output": {"count": {"$sum": 1}}
            }}
        ]
        results = list(empty_collection.aggregate(pipeline))
        assert len(results) == 0

    def test_drop_clears_all_documents(self, populated):
        collection, _ = populated
        assert collection.count_documents({}) == 25
        collection.drop()
        assert collection.count_documents({}) == 0

    def test_drop_and_reinsert_gives_same_count(self, populated):
        collection, _ = populated
        collection.drop()
        collection.insert_many(STUDENT_RECORDS)
        assert collection.count_documents({}) == 25

    def test_status_values_are_valid(self, populated):
        collection, _ = populated
        valid = {"active", "inactive", "graduated"}
        statuses = set(s["status"] for s in collection.find({}, {"_id": 0}))
        assert statuses.issubset(valid)

    def test_grades_within_valid_range(self, populated):
        collection, _ = populated
        grades = [s["grade"] for s in collection.find({}, {"_id": 0})]
        assert all(0 <= g <= 100 for g in grades)
