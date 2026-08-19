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


# ---------------------------------------------------------------------------
# 3. update_one with $set
# ---------------------------------------------------------------------------

class TestUpdateOne:
    def test_set_adds_new_field(self, populated):
        collection, _ = populated
        collection.update_one(
            {"name": "Alice Johnson"},
            {"$set": {"scholarship": "Dean's Award"}}
        )
        alice = collection.find_one({"name": "Alice Johnson"}, {"_id": 0})
        assert alice["scholarship"] == "Dean's Award"

    def test_set_does_not_affect_other_documents(self, populated):
        collection, _ = populated
        collection.update_one(
            {"name": "Alice Johnson"},
            {"$set": {"scholarship": "Dean's Award"}}
        )
        bob = collection.find_one({"name": "Bob Smith"}, {"_id": 0})
        assert "scholarship" not in bob

    def test_modified_count_is_one(self, populated):
        collection, _ = populated
        result = collection.update_one(
            {"name": "Alice Johnson"},
            {"$set": {"scholarship": "Dean's Award"}}
        )
        assert result.modified_count == 1


# ---------------------------------------------------------------------------
# 4. update_many with $inc
# ---------------------------------------------------------------------------

class TestUpdateMany:
    def test_inc_modifies_all_failing_students(self, populated):
        collection, _ = populated
        result = collection.update_many(
            {"grade": {"$lt": 60}},
            {"$inc": {"grade": 5}}
        )
        assert result.modified_count == 6

    def test_inc_increases_grade_correctly(self, populated):
        collection, _ = populated
        collection.update_many(
            {"grade": {"$lt": 60}},
            {"$inc": {"grade": 5}}
        )
        charlie = collection.find_one({"name": "Charlie Brown"}, {"_id": 0})
        assert charlie["grade"] == 60  # was 55, +5

    def test_inc_does_not_affect_passing_students(self, populated):
        collection, _ = populated
        alice_before = collection.find_one({"name": "Alice Johnson"}, {"_id": 0})["grade"]
        collection.update_many(
            {"grade": {"$lt": 60}},
            {"$inc": {"grade": 5}}
        )
        alice_after = collection.find_one({"name": "Alice Johnson"}, {"_id": 0})["grade"]
        assert alice_before == alice_after  # 95, unchanged


# ---------------------------------------------------------------------------
# 5. Upsert
# ---------------------------------------------------------------------------

class TestUpsert:
    def test_upsert_updates_existing_document(self, populated):
        collection, _ = populated
        result = collection.update_one(
            {"student_id": "STU006"},
            {"$set": {"status": "active"}},
            upsert=True
        )
        frank = collection.find_one({"student_id": "STU006"}, {"_id": 0})
        assert frank["status"] == "active"
        assert result.upserted_id is None

    def test_upsert_inserts_when_no_match(self, empty_collection):
        result = empty_collection.update_one(
            {"student_id": "STU999"},
            {"$set": {"name": "New Student", "status": "active", "grade": 75}},
            upsert=True
        )
        assert result.upserted_id is not None
        assert empty_collection.count_documents({}) == 1

    def test_upsert_no_match_without_flag_does_nothing(self, empty_collection):
        result = empty_collection.update_one(
            {"student_id": "STU999"},
            {"$set": {"name": "New Student"}},
            upsert=False
        )
        assert result.modified_count == 0
        assert result.upserted_id is None
        assert empty_collection.count_documents({}) == 0


# ---------------------------------------------------------------------------
# 6. Delete one
# ---------------------------------------------------------------------------

class TestDeleteOne:
    def test_find_one_and_delete_returns_document(self, populated):
        collection, _ = populated
        deleted = collection.find_one_and_delete(
            {"student_id": "STU010"},
            projection={"_id": 0, "name": 1}
        )
        assert deleted is not None
        assert deleted["name"] == "Julia Child"

    def test_document_removed_after_delete(self, populated):
        collection, _ = populated
        collection.find_one_and_delete({"student_id": "STU010"})
        result = collection.find_one({"student_id": "STU010"})
        assert result is None

    def test_delete_one_nonexistent_returns_none(self, populated):
        collection, _ = populated
        deleted = collection.find_one_and_delete(
            {"student_id": "STU999"},
            projection={"_id": 0, "name": 1}
        )
        assert deleted is None


# ---------------------------------------------------------------------------
# 7. Delete many
# ---------------------------------------------------------------------------

class TestDeleteMany:
    def test_delete_many_graduated(self, populated):
        collection, _ = populated
        result = collection.delete_many({"status": "graduated"})
        assert result.deleted_count == 2  # Julia Child + Vera Wang

    def test_collection_shrinks_correctly(self, populated):
        collection, _ = populated
        collection.delete_many({"status": "graduated"})
        assert collection.count_documents({}) == 23


# ---------------------------------------------------------------------------
# 8. Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_collection_update_does_nothing(self, empty_collection):
        result = empty_collection.update_one(
            {"name": "Ghost"},
            {"$set": {"grade": 100}}
        )
        assert result.modified_count == 0

    def test_empty_collection_delete_does_nothing(self, empty_collection):
        result = empty_collection.delete_many({"status": "active"})
        assert result.deleted_count == 0

    def test_drop_clears_all_documents(self, populated):
        collection, _ = populated
        assert collection.count_documents({}) == 25
        collection.drop()
        assert collection.count_documents({}) == 0

    def test_double_delete_returns_zero(self, populated):
        collection, _ = populated
        collection.find_one_and_delete({"student_id": "STU010"})
        result = collection.delete_many({"student_id": "STU010"})
        assert result.deleted_count == 0


# ---------------------------------------------------------------------------
# 9. Summary Report Logic
# ---------------------------------------------------------------------------

class TestSummaryReport:
    def test_total_count_after_graduated_deleted(self, populated):
        collection, _ = populated
        collection.delete_many({"status": "graduated"})
        assert collection.count_documents({}) == 23

    def test_scholarship_field_exists_after_set(self, populated):
        collection, _ = populated
        collection.update_one(
            {"name": "Alice Johnson"},
            {"$set": {"scholarship": "Dean's Award"}}
        )
        count = collection.count_documents({"scholarship": {"$exists": True}})
        assert count == 1

    def test_failing_count_after_inc(self, populated):
        collection, _ = populated
        collection.update_many(
            {"grade": {"$lt": 60}},
            {"$inc": {"grade": 5}}
        )
        # Charlie (55->60), Walt (56->61), Rosa (58->63) are now passing
        # Diana (48->53), Frank (52->57), Laura (45->50) are still failing
        still_failing = collection.count_documents({"grade": {"$lt": 60}})
        assert still_failing == 3

    def test_status_distribution(self, populated):
        collection, _ = populated
        pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
        counts = {doc["_id"]: doc["count"] for doc in collection.aggregate(pipeline)}
        assert counts["active"] == 21
        assert counts["inactive"] == 2
        assert counts["graduated"] == 2
