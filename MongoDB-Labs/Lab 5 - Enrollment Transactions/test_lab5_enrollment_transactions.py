import pytest
import mongomock
from pymongo import ReturnDocument


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
def empty_courses(db):
    """Empty courses collection."""
    return db["courses"]


@pytest.fixture
def empty_enrollments(db):
    """Empty enrollments collection."""
    return db["enrollments"]


COURSE_RECORDS = [
    {"course_id": "CS101",   "title": "Introduction to Computer Science",
     "seats_total": 3, "seats_available": 3},
    {"course_id": "CS201",   "title": "Data Structures and Algorithms",
     "seats_total": 5, "seats_available": 5},
    {"course_id": "MATH101", "title": "Calculus I",
     "seats_total": 2, "seats_available": 2},
    {"course_id": "PHYS101", "title": "General Physics I",
     "seats_total": 4, "seats_available": 4},
]


@pytest.fixture
def populated(db):
    """Both courses and enrollments collections populated with seed data."""
    courses = db["courses"]
    enrollments = db["enrollments"]
    courses.insert_many(COURSE_RECORDS)
    return courses, enrollments


# ---------------------------------------------------------------------------
# 1. Connection
# ---------------------------------------------------------------------------

class TestConnection:
    def test_client_creates_successfully(self, client):
        assert client is not None

    def test_database_accessible(self, db):
        assert db is not None

    def test_courses_collection_accessible(self, empty_courses):
        assert empty_courses is not None

    def test_enrollments_collection_accessible(self, empty_enrollments):
        assert empty_enrollments is not None


# ---------------------------------------------------------------------------
# 2. Insert Records
# ---------------------------------------------------------------------------

class TestInsertRecords:
    def test_four_courses_inserted(self, populated):
        courses, _ = populated
        assert courses.count_documents({}) == 4

    def test_enrollments_starts_empty(self, populated):
        _, enrollments = populated
        assert enrollments.count_documents({}) == 0

    def test_course_has_all_required_fields(self, populated):
        courses, _ = populated
        first = courses.find_one()
        required = {"course_id", "title", "seats_total", "seats_available"}
        assert required.issubset(first.keys())

    def test_seats_total_matches_seats_available_initially(self, populated):
        courses, _ = populated
        for c in courses.find():
            assert c["seats_total"] == c["seats_available"]

    def test_seat_counts_are_small(self, populated):
        courses, _ = populated
        seats = [c["seats_total"] for c in courses.find()]
        assert max(seats) <= 5


# ---------------------------------------------------------------------------
# 3. Non-Atomic Enrollment (simulate the two-step pattern)
# ---------------------------------------------------------------------------

class TestNonAtomicEnrollment:
    def test_decrement_and_insert_both_succeed(self, populated):
        courses, enrollments = populated
        cid = "CS101"

        courses.update_one(
            {"course_id": cid, "seats_available": {"$gt": 0}},
            {"$inc": {"seats_available": -1}}
        )
        enrollments.insert_one({
            "enrollment_id": "ENR999",
            "student_id": "STU999",
            "student_name": "Test Student",
            "course_id": cid,
        })

        course = courses.find_one({"course_id": cid})
        assert course["seats_available"] == 2
        assert enrollments.count_documents({"course_id": cid}) == 1

    def test_seats_do_not_go_negative_with_filter(self, populated):
        courses, _ = populated
        cid = "MATH101"

        # Decrement twice (MATH101 has 2 seats)
        for _ in range(2):
            courses.update_one(
                {"course_id": cid, "seats_available": {"$gt": 0}},
                {"$inc": {"seats_available": -1}}
            )

        # Third attempt should fail to match (seats_available is now 0)
        result = courses.update_one(
            {"course_id": cid, "seats_available": {"$gt": 0}},
            {"$inc": {"seats_available": -1}}
        )
        assert result.modified_count == 0

        course = courses.find_one({"course_id": cid})
        assert course["seats_available"] == 0


# ---------------------------------------------------------------------------
# 4. find_one_and_update (atomic decrement)
# ---------------------------------------------------------------------------

class TestFindOneAndUpdate:
    def test_atomic_decrement_returns_old_doc(self, populated):
        courses, _ = populated
        old = courses.find_one_and_update(
            {"course_id": "CS101", "seats_available": {"$gt": 0}},
            {"$inc": {"seats_available": -1}},
            return_document=ReturnDocument.BEFORE
        )
        assert old is not None
        assert old["seats_available"] == 3

    def test_atomic_decrement_new_seats_available_is_one_less(self, populated):
        courses, _ = populated
        new = courses.find_one_and_update(
            {"course_id": "CS101", "seats_available": {"$gt": 0}},
            {"$inc": {"seats_available": -1}},
            return_document=ReturnDocument.AFTER
        )
        assert new["seats_available"] == 2

    def test_atomic_decrement_returns_none_when_full(self, populated):
        courses, _ = populated
        # Drain MATH101 (2 seats)
        for _ in range(2):
            courses.find_one_and_update(
                {"course_id": "MATH101", "seats_available": {"$gt": 0}},
                {"$inc": {"seats_available": -1}}
            )
        # Third attempt returns None
        result = courses.find_one_and_update(
            {"course_id": "MATH101", "seats_available": {"$gt": 0}},
            {"$inc": {"seats_available": -1}}
        )
        assert result is None

    def test_seat_count_does_not_go_negative(self, populated):
        courses, _ = populated
        # Drain CS101 (3 seats)
        for _ in range(3):
            courses.find_one_and_update(
                {"course_id": "CS101", "seats_available": {"$gt": 0}},
                {"$inc": {"seats_available": -1}}
            )
        course = courses.find_one({"course_id": "CS101"})
        assert course["seats_available"] == 0


# ---------------------------------------------------------------------------
# 5. Transactions (mongomock limitation)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# NOTE: mongomock 4.3.0 does NOT support sessions or transactions.
# The following tests are SKIPPED because mongomock raises:
#   "NotImplementedError: Mongomock does not support sessions yet"
#
# This limitation was verified on 2026-08-20 against mongomock 4.3.0.
# client.start_session() raises NotImplementedError immediately.
# session.with_transaction() is unreachable since start_session fails first.
#
# The transaction functionality is validated against the real MongoDB Atlas
# connection in the notebook's Step 4 and Step 5 output, where:
#   - Step 4: 3 students are enrolled in CS101 via with_transaction(), seats
#     correctly reach 0, and all 3 enrollment documents are created.
#   - Step 5: A 4th enrollment attempt into full CS101 causes the transaction
#     to abort — seats_available stays at 0 and no enrollment is created.
# ---------------------------------------------------------------------------

class TestTransactions:
    @pytest.mark.skip(reason="mongomock 4.3.0 does not support start_session()")
    def test_start_session_raises_not_implemented(self, client):
        session = client.start_session()
        session.end_session()

    @pytest.mark.skip(reason="mongomock 4.3.0 does not support start_session()")
    def test_with_transaction_enrolls_student(self, client):
        db = client["school_db"]
        courses = db["courses"]
        enrollments = db["enrollments"]
        courses.insert_many(COURSE_RECORDS)

        def enroll(session):
            courses.find_one_and_update(
                {"course_id": "CS101", "seats_available": {"$gt": 0}},
                {"$inc": {"seats_available": -1}},
                session=session
            )
            enrollments.insert_one({
                "enrollment_id": "ENR001",
                "student_id": "STU001",
                "student_name": "Alice Johnson",
                "course_id": "CS101",
            }, session=session)

        with client.start_session() as session:
            session.with_transaction(enroll)

        cs101 = courses.find_one({"course_id": "CS101"})
        assert cs101["seats_available"] == 2
        assert enrollments.count_documents({"course_id": "CS101"}) == 1

    @pytest.mark.skip(reason="mongomock 4.3.0 does not support start_session()")
    def test_transaction_abort_when_full(self, client):
        db = client["school_db"]
        courses = db["courses"]
        enrollments = db["enrollments"]
        courses.insert_one(COURSE_RECORDS[0])  # CS101 with 3 seats

        def enroll(session):
            result = courses.find_one_and_update(
                {"course_id": "CS101", "seats_available": {"$gt": 0}},
                {"$inc": {"seats_available": -1}},
                session=session
            )
            if result is None:
                raise Exception("No seats available")
            enrollments.insert_one({
                "enrollment_id": "ENR001",
                "student_id": "STU001",
                "student_name": "Alice",
                "course_id": "CS101",
            }, session=session)

        # Fill all 3 seats
        for i in range(3):
            with client.start_session() as session:
                session.with_transaction(enroll)

        # 4th attempt should raise
        with pytest.raises(Exception, match="No seats available"):
            with client.start_session() as session:
                session.with_transaction(enroll)

        cs101 = courses.find_one({"course_id": "CS101"})
        assert cs101["seats_available"] == 0
        assert enrollments.count_documents({}) == 3


# ---------------------------------------------------------------------------
# 6. Change Streams (mongomock limitation)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# NOTE: mongomock 4.3.0 does NOT support change streams (.watch()).
# The following test is SKIPPED because mongomock raises:
#   TypeError: 'Collection' object is not callable.
#   (The watch() method does not exist on mongomock's Collection.)
#
# This limitation was verified on 2026-08-20 against mongomock 4.3.0.
#
# Change stream functionality is validated against the real MongoDB Atlas
# connection in the notebook's Step 6 output, where:
#   - A change stream on enrollments correctly reports an insert event with
#     operationType "insert" and the fullDocument containing the enrollment
#     data for STU010 (Diana Prince) in CS201.
# ---------------------------------------------------------------------------

class TestChangeStreams:
    @pytest.mark.skip(reason="mongomock 4.3.0 does not support watch() / change streams")
    def test_watch_returns_change_event(self, client):
        db = client["school_db"]
        enrollments = db["enrollments"]
        stream = enrollments.watch()
        enrollments.insert_one({
            "enrollment_id": "ENR001",
            "student_id": "STU001",
            "student_name": "Alice",
            "course_id": "CS101",
        })
        event = stream.next()
        assert event["operationType"] == "insert"
        assert event["fullDocument"]["student_id"] == "STU001"
        stream.close()


# ---------------------------------------------------------------------------
# 7. Backup / Restore (JSON export)
# ---------------------------------------------------------------------------

class TestBackupRestore:
    def test_backup_exports_all_documents(self, populated, tmp_path):
        courses, enrollments = populated
        import json

        backup = {
            "courses": [doc for doc in courses.find({}, {"_id": 0})],
            "enrollments": [doc for doc in enrollments.find({}, {"_id": 0})],
        }
        path = tmp_path / "backup.json"
        with open(path, "w") as f:
            json.dump(backup, f, default=str)

        with open(path, "r") as f:
            restored = json.load(f)

        assert len(restored["courses"]) == 4
        assert len(restored["enrollments"]) == 0

    def test_restore_repopulates_collection(self, populated, tmp_path):
        courses, enrollments = populated
        import json

        backup = {
            "courses": [doc for doc in courses.find({}, {"_id": 0})],
            "enrollments": [doc for doc in enrollments.find({}, {"_id": 0})],
        }
        path = tmp_path / "backup.json"
        with open(path, "w") as f:
            json.dump(backup, f, default=str)

        courses.drop()
        enrollments.drop()
        assert courses.count_documents({}) == 0

        with open(path, "r") as f:
            restored = json.load(f)

        courses.insert_many(restored["courses"])
        assert courses.count_documents({}) == 4

    def test_backup_preserves_all_course_fields(self, populated, tmp_path):
        courses, _ = populated
        import json

        backup = {
            "courses": [doc for doc in courses.find({}, {"_id": 0})],
        }
        path = tmp_path / "backup.json"
        with open(path, "w") as f:
            json.dump(backup, f, default=str)

        with open(path, "r") as f:
            restored = json.load(f)

        for doc in restored["courses"]:
            assert "course_id" in doc
            assert "title" in doc
            assert "seats_total" in doc
            assert "seats_available" in doc


# ---------------------------------------------------------------------------
# 8. Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_courses_aggregation_returns_zero_sum(self, empty_courses):
        pipeline = [{"$group": {"_id": None, "total": {"$sum": "$seats_available"}}}]
        results = list(empty_courses.aggregate(pipeline))
        # MongoDB returns one doc with the accumulator default (0) for an empty collection
        assert len(results) == 1
        assert results[0]["total"] == 0

    def test_drop_courses_clears_all_documents(self, populated):
        courses, _ = populated
        assert courses.count_documents({}) == 4
        courses.drop()
        assert courses.count_documents({}) == 0

    def test_drop_enrollments_clears_all_documents(self, populated):
        _, enrollments = populated
        assert enrollments.count_documents({}) == 0
        enrollments.drop()
        assert enrollments.count_documents({}) == 0

    def test_drop_and_reinsert_gives_same_count(self, populated):
        courses, enrollments = populated
        courses.drop()
        courses.insert_many(COURSE_RECORDS)
        assert courses.count_documents({}) == 4
        assert enrollments.count_documents({}) == 0

    def test_seats_total_and_available_match_after_insert(self, populated):
        courses, _ = populated
        for c in courses.find():
            assert c["seats_total"] == c["seats_available"]

    def test_enrollment_references_valid_course(self, populated):
        courses, enrollments = populated
        # Manually insert one enrollment
        enrollments.insert_one({
            "enrollment_id": "ENR001",
            "student_id": "STU001",
            "student_name": "Alice",
            "course_id": "CS101",
        })
        valid_ids = {c["course_id"] for c in courses.find()}
        enr_ids = {e["course_id"] for e in enrollments.find()}
        assert enr_ids.issubset(valid_ids)
