import random

import pytest
import mongomock
from bson import BSON


def doc_size(document):
    return len(BSON.encode(document))


@pytest.fixture
def db():
    return mongomock.MongoClient()["school_db"]


def make_submission(n):
    return {"student_id": f"STU{n % 500:05d}", "assignment": f"A{n % 8 + 1}",
            "score": 50 + n % 50, "submitted_at": "2026-01-15T10:00:00"}


def make_grade(n):
    return {"course": ["Math", "Physics", "English", "Biology", "CS"][n % 5],
            "grade": 50 + (n * 7) % 50, "term": f"T{n // 100}", "comment": "graded " * 8}


# ---------------------------------------------------------------------------
# 1. Document size measurement and the unbounded array
# ---------------------------------------------------------------------------

class TestDocumentSize:
    def test_size_grows_with_array(self):
        doc = {"_id": "C", "items": []}
        sizes = []
        for n in range(1, 301):
            doc["items"].append(make_submission(n))
            if n in (10, 100, 300):
                sizes.append(doc_size(doc))
        assert sizes[0] < sizes[1] < sizes[2]

    def test_growth_is_roughly_linear(self):
        doc = {"_id": "C", "items": []}
        marks = {}
        for n in range(1, 2001):
            doc["items"].append(make_submission(n))
            if n in (1000, 2000):
                marks[n] = doc_size(doc)
        first_half = marks[1000]
        second_half = marks[2000] - marks[1000]
        assert abs(first_half - second_half) / first_half < 0.05

    def test_limit_estimate_is_in_the_expected_range(self):
        doc = {"_id": "C", "items": []}
        marks = {}
        for n in range(1, 2001):
            doc["items"].append(make_submission(n))
            if n in (1000, 2000):
                marks[n] = doc_size(doc)
        per_entry = (marks[2000] - marks[1000]) / 1000
        limit = int(16 * 1024 * 1024 / per_entry)
        assert 100_000 < limit < 250_000

    def test_small_course_document_is_tiny(self):
        assert doc_size({"_id": "CS101", "title": "Introduction to Programming"}) < 100

    def test_referenced_submissions_query_returns_ten(self, db):
        subs = db["pat_submissions"]
        subs.create_index([("course_id", 1), ("submitted_at", -1)])
        subs.insert_many([{**make_submission(n), "course_id": "CS101"} for n in range(1, 301)])
        recent = list(subs.find({"course_id": "CS101"}).sort("submitted_at", -1).limit(10))
        assert len(recent) == 10

    def test_adding_submission_is_single_insert(self, db):
        subs = db["pat_submissions"]
        subs.insert_many([{**make_submission(n), "course_id": "CS101"} for n in range(1, 11)])
        subs.insert_one({**make_submission(11), "course_id": "CS101"})
        assert subs.count_documents({"course_id": "CS101"}) == 11


# ---------------------------------------------------------------------------
# 2. Subset pattern
# ---------------------------------------------------------------------------

HISTORY_LEN = 1500


@pytest.fixture
def student_setup(db):
    fat = {"_id": "STU00001", "name": "Alice", "major": "CS",
           "grade_history": [make_grade(n) for n in range(HISTORY_LEN)]}
    db["pat_students_fat"].insert_one(fat)
    db["pat_grade_history"].insert_many([{**make_grade(n), "student_id": "STU00001", "seq": n}
                                         for n in range(HISTORY_LEN)])
    slim = {"_id": "STU00001", "name": "Alice", "major": "CS",
            "recent_grades": [make_grade(n) for n in range(HISTORY_LEN - 5, HISTORY_LEN)]}
    db["pat_students"].insert_one(slim)
    seed_total = sum(g["grade"] for g in db["pat_grade_history"].find({"student_id": "STU00001"}))
    db["pat_students"].update_one({"_id": "STU00001"},
                                  {"$set": {"grade_count": HISTORY_LEN, "grade_sum": seed_total}})
    return fat, slim


def record_grade(db, student_id, course, grade):
    seq = db["pat_grade_history"].count_documents({"student_id": student_id})
    entry = {"course": course, "grade": grade, "term": "T-new", "comment": "graded " * 8}
    db["pat_grade_history"].insert_one({**entry, "student_id": student_id, "seq": seq})
    db["pat_students"].update_one(
        {"_id": student_id},
        {"$push": {"recent_grades": {"$each": [entry], "$slice": -5}},
         "$inc": {"grade_count": 1, "grade_sum": grade}},
    )


class TestSubsetPattern:
    def test_slim_document_is_much_smaller(self, student_setup):
        fat, slim = student_setup
        assert doc_size(fat) > 50 * doc_size(slim)

    def test_slim_has_exactly_five_recent_grades(self, student_setup):
        _, slim = student_setup
        assert len(slim["recent_grades"]) == 5

    def test_full_history_still_available(self, db, student_setup):
        assert db["pat_grade_history"].count_documents({"student_id": "STU00001"}) == HISTORY_LEN

    def test_recent_grades_are_last_five_of_history(self, db, student_setup):
        _, slim = student_setup
        expected = [make_grade(n)["grade"] for n in range(HISTORY_LEN - 5, HISTORY_LEN)]
        assert [g["grade"] for g in slim["recent_grades"]] == expected

    def test_slice_keeps_five_after_new_grades(self, db, student_setup):
        for g in (88, 92, 79):
            record_grade(db, "STU00001", "CS", g)
        doc = db["pat_students"].find_one({"_id": "STU00001"})
        assert len(doc["recent_grades"]) == 5
        assert [x["grade"] for x in doc["recent_grades"]][-3:] == [88, 92, 79]

    def test_history_grows_with_each_grade(self, db, student_setup):
        record_grade(db, "STU00001", "CS", 70)
        assert db["pat_grade_history"].count_documents({"student_id": "STU00001"}) == HISTORY_LEN + 1


# ---------------------------------------------------------------------------
# 3. Computed pattern
# ---------------------------------------------------------------------------

class TestComputedPattern:
    def test_counters_seeded(self, db, student_setup):
        doc = db["pat_students"].find_one({"_id": "STU00001"})
        assert doc["grade_count"] == HISTORY_LEN

    def test_counters_match_aggregation_after_updates(self, db, student_setup):
        for g in (88, 92, 79, 61):
            record_grade(db, "STU00001", "CS", g)
        doc = db["pat_students"].find_one({"_id": "STU00001"})
        stored = doc["grade_sum"] / doc["grade_count"]
        agg = list(db["pat_grade_history"].aggregate([
            {"$match": {"student_id": "STU00001"}},
            {"$group": {"_id": None, "avg": {"$avg": "$grade"}}},
        ]))[0]["avg"]
        assert abs(stored - agg) < 1e-9

    def test_count_increments_by_one(self, db, student_setup):
        record_grade(db, "STU00001", "CS", 50)
        assert db["pat_students"].find_one({"_id": "STU00001"})["grade_count"] == HISTORY_LEN + 1

    def test_sum_increments_by_grade(self, db, student_setup):
        before = db["pat_students"].find_one({"_id": "STU00001"})["grade_sum"]
        record_grade(db, "STU00001", "CS", 77)
        assert db["pat_students"].find_one({"_id": "STU00001"})["grade_sum"] == before + 77


# ---------------------------------------------------------------------------
# 4. Bucket pattern
# ---------------------------------------------------------------------------

@pytest.fixture
def attendance(db):
    rng = random.Random(7)
    students = [f"STU{n:05d}" for n in range(1, 51)]
    daily = db["pat_attendance_daily"]
    monthly = db["pat_attendance_monthly"]
    monthly.create_index([("student_id", 1), ("month", 1)], unique=True)
    docs = []
    for sid in students:
        for day in range(1, 31):
            docs.append({"student_id": sid, "date": f"2026-09-{day:02d}", "present": rng.random() > 0.15})
    daily.insert_many(docs)
    for rec in docs:
        monthly.update_one(
            {"student_id": rec["student_id"], "month": "2026-09"},
            {"$push": {"days": {"date": rec["date"], "present": rec["present"]}},
             "$inc": {"present_count": 1 if rec["present"] else 0, "total_count": 1}},
            upsert=True,
        )
    return daily, monthly, docs


class TestBucketPattern:
    def test_daily_document_count(self, attendance):
        daily, _, _ = attendance
        assert daily.count_documents({}) == 1500

    def test_bucket_document_count(self, attendance):
        _, monthly, _ = attendance
        assert monthly.count_documents({}) == 50

    def test_each_bucket_has_thirty_days(self, attendance):
        _, monthly, _ = attendance
        for b in monthly.find():
            assert len(b["days"]) == 30 and b["total_count"] == 30

    def test_present_count_matches_days_array(self, attendance):
        _, monthly, _ = attendance
        for b in monthly.find():
            assert b["present_count"] == sum(1 for d in b["days"] if d["present"])

    def test_bucket_totals_match_daily_totals(self, attendance):
        daily, monthly, _ = attendance
        daily_present = daily.count_documents({"present": True})
        bucket_present = sum(b["present_count"] for b in monthly.find())
        assert daily_present == bucket_present

    def test_one_read_returns_whole_month(self, attendance):
        _, monthly, _ = attendance
        bucket = monthly.find_one({"student_id": "STU00001", "month": "2026-09"})
        assert bucket is not None and len(bucket["days"]) == 30

    def test_unique_index_blocks_duplicate_bucket(self, attendance):
        _, monthly, _ = attendance
        with pytest.raises(Exception):
            monthly.insert_one({"student_id": "STU00001", "month": "2026-09"})


# ---------------------------------------------------------------------------
# 5. Extended reference pattern
# ---------------------------------------------------------------------------

@pytest.fixture
def enrollments(db):
    courses = db["pat_courses"]
    courses.insert_many([
        {"_id": "CS101", "title": "Intro to Programming", "instructor_id": "I1", "instructor_name": "Dr. Rao", "credits": 4},
        {"_id": "MA101", "title": "Calculus I", "instructor_id": "I2", "instructor_name": "Dr. Singh", "credits": 4},
        {"_id": "PH101", "title": "Mechanics", "instructor_id": "I1", "instructor_name": "Dr. Rao", "credits": 3},
        {"_id": "EN101", "title": "Academic Writing", "instructor_id": "I3", "instructor_name": "Dr. Mehta", "credits": 2},
    ])
    cmap = {c["_id"]: c for c in courses.find()}
    for i in range(200):
        sid = f"STU{i % 40 + 1:05d}"
        cid = ["CS101", "MA101", "PH101", "EN101"][i % 4]
        c = cmap[cid]
        db["pat_enrollments_ref"].insert_one({"student_id": sid, "course_id": cid})
        db["pat_enrollments_ext"].insert_one({
            "student_id": sid, "course_id": cid,
            "course": {"title": c["title"], "instructor_id": c["instructor_id"], "instructor_name": c["instructor_name"]},
        })
    return courses


class TestExtendedReference:
    def test_same_row_count_both_designs(self, db, enrollments):
        ref = db["pat_enrollments_ref"].count_documents({"student_id": "STU00001"})
        ext = db["pat_enrollments_ext"].count_documents({"student_id": "STU00001"})
        assert ref == ext and ref > 0

    def test_lookup_returns_course_title(self, db, enrollments):
        result = list(db["pat_enrollments_ref"].aggregate([
            {"$match": {"student_id": "STU00001"}},
            {"$lookup": {"from": "pat_courses", "localField": "course_id", "foreignField": "_id", "as": "course"}},
            {"$unwind": "$course"},
        ]))
        assert all("title" in r["course"] for r in result)

    def test_extended_reference_has_title_without_lookup(self, db, enrollments):
        doc = db["pat_enrollments_ext"].find_one({"student_id": "STU00001"})
        assert doc["course"]["title"]

    def test_extended_reference_omits_large_fields(self, db, enrollments):
        doc = db["pat_enrollments_ext"].find_one({"student_id": "STU00001"})
        assert "credits" not in doc["course"]

    def test_designs_agree_on_titles(self, db, enrollments):
        lookup = {r["course_id"]: r["course"]["title"] for r in db["pat_enrollments_ref"].aggregate([
            {"$match": {"student_id": "STU00001"}},
            {"$lookup": {"from": "pat_courses", "localField": "course_id", "foreignField": "_id", "as": "course"}},
            {"$unwind": "$course"}])}
        ext = {r["course_id"]: r["course"]["title"] for r in db["pat_enrollments_ext"].find({"student_id": "STU00001"})}
        assert lookup == ext

    def test_copies_go_stale_then_propagate(self, db, enrollments):
        enrollments.update_many({"instructor_id": "I1"}, {"$set": {"instructor_name": "Dr. Rao-Verma"}})
        stale = db["pat_enrollments_ext"].count_documents({"course.instructor_id": "I1",
                                                           "course.instructor_name": "Dr. Rao"})
        assert stale == 100
        res = db["pat_enrollments_ext"].update_many({"course.instructor_id": "I1"},
                                                    {"$set": {"course.instructor_name": "Dr. Rao-Verma"}})
        assert res.modified_count == 100
        assert db["pat_enrollments_ext"].count_documents({"course.instructor_name": "Dr. Rao"}) == 0

    def test_other_instructors_untouched(self, db, enrollments):
        db["pat_enrollments_ext"].update_many({"course.instructor_id": "I1"},
                                              {"$set": {"course.instructor_name": "X"}})
        assert db["pat_enrollments_ext"].count_documents({"course.instructor_name": "Dr. Singh"}) == 50


# ---------------------------------------------------------------------------
# 6. Cleanup
# ---------------------------------------------------------------------------

class TestCleanup:
    def test_drop_removes_collection(self, db):
        db["pat_students"].insert_one({"_id": 1})
        db["pat_students"].drop()
        assert "pat_students" not in db.list_collection_names()
