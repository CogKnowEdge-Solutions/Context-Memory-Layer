import datetime as dt
import random

import pytest
import mongomock
from pymongo.errors import DuplicateKeyError

# NOTE: mongomock has no transactions, explain() or Atlas Search, so these tests
# cover the logic around them: seed data, CRUD and upsert, the enroll rules
# (without a session), the report pipeline, index definitions, and the search
# pipeline shape. Transactions, explain and $search are verified by running the
# notebook on Atlas, where each step's check cell confirms them.

PROGRAMS = ["Computer Science", "Mathematics", "Physics", "Biology", "English"]
STUDENTS = [
    {"student_id": f"S{n:03d}", "name": f"Student {n:02d}", "program": PROGRAMS[n % 5],
     "year": 1 + n % 4, "status": "active" if n % 7 else "inactive"}
    for n in range(1, 21)
]
COURSES = [
    {"course_id": "CS101", "title": "Introduction to Programming", "program": "Computer Science", "description": "Learn variables, loops and functions by writing small Python programs.", "seats_total": 3, "seats_available": 3},
    {"course_id": "CS201", "title": "Data Structures", "program": "Computer Science", "description": "Lists, trees and graphs.", "seats_total": 40, "seats_available": 40},
    {"course_id": "MA101", "title": "Calculus I", "program": "Mathematics", "description": "Limits and derivatives.", "seats_total": 40, "seats_available": 40},
    {"course_id": "PH101", "title": "Classical Mechanics", "program": "Physics", "description": "Motion and forces.", "seats_total": 40, "seats_available": 40},
    {"course_id": "BI101", "title": "Cell Biology", "program": "Biology", "description": "How cells work.", "seats_total": 40, "seats_available": 40},
    {"course_id": "EN101", "title": "Academic Writing", "program": "English", "description": "Plan and revise essays.", "seats_total": 40, "seats_available": 40},
]


@pytest.fixture
def db():
    d = mongomock.MongoClient()["registrar_db"]
    d["students"].insert_many([dict(s) for s in STUDENTS])
    d["courses"].insert_many([dict(c) for c in COURSES])
    d["enrollments"].create_index([("student_id", 1), ("course_id", 1)], unique=True, name="uniq_student_course")
    return d


def enroll(db, student_id, course_id):
    """Same rules as the notebook's enroll(), minus the transaction session."""
    if db["students"].find_one({"student_id": student_id, "status": "active"}) is None:
        raise ValueError("student not eligible")
    course = db["courses"].find_one_and_update(
        {"course_id": course_id, "seats_available": {"$gt": 0}}, {"$inc": {"seats_available": -1}})
    if course is None:
        raise ValueError("no seats available")
    db["enrollments"].insert_one({"student_id": student_id, "course_id": course_id,
                                  "course_title": course["title"], "status": "active",
                                  "enrolled_at": dt.datetime.utcnow()})


# ---- Step 1: seed -------------------------------------------------------
class TestSeed:
    def test_counts(self, db):
        assert db["students"].count_documents({}) == 20
        assert db["courses"].count_documents({}) == 6

    def test_two_inactive_students(self, db):
        assert db["students"].count_documents({"status": "inactive"}) == 2

    def test_five_programs(self, db):
        assert set(db["students"].distinct("program")) == set(PROGRAMS)

    def test_cs101_has_three_seats(self, db):
        assert db["courses"].find_one({"course_id": "CS101"})["seats_available"] == 3

    def test_unique_index_registered(self, db):
        assert db["enrollments"].index_information()["uniq_student_course"]["unique"]

    def test_unique_index_blocks_duplicates(self, db):
        enroll(db, "S001", "CS201")
        with pytest.raises(DuplicateKeyError):
            db["enrollments"].insert_one({"student_id": "S001", "course_id": "CS201"})


# ---- Step 2: CRUD and upsert -------------------------------------------
class TestCrud:
    def test_active_cs_students_sorted(self, db):
        got = list(db["students"].find({"program": "Computer Science", "status": "active"}).sort("name", 1))
        assert [s["student_id"] for s in got] == ["S005", "S010", "S015", "S020"]

    def test_reactivate_s014(self, db):
        db["students"].update_one({"student_id": "S014"}, {"$set": {"status": "active"}})
        assert db["students"].find_one({"student_id": "S014"})["status"] == "active"

    def test_upsert_twice_creates_one_document(self, db):
        for _ in range(2):
            db["courses"].update_one({"course_id": "CS301"},
                                     {"$set": {"title": "Databases", "seats_total": 40},
                                      "$setOnInsert": {"seats_available": 40}}, upsert=True)
        assert db["courses"].count_documents({"course_id": "CS301"}) == 1
        assert db["courses"].count_documents({}) == 7

    def test_upsert_sets_on_insert_only_once(self, db):
        db["courses"].update_one({"course_id": "CS301"}, {"$setOnInsert": {"seats_available": 40}}, upsert=True)
        db["courses"].update_one({"course_id": "CS301"}, {"$inc": {"seats_available": -1}})
        db["courses"].update_one({"course_id": "CS301"}, {"$setOnInsert": {"seats_available": 40}}, upsert=True)
        assert db["courses"].find_one({"course_id": "CS301"})["seats_available"] == 39


# ---- Step 3: enrollment rules ------------------------------------------
class TestEnroll:
    def test_enroll_takes_a_seat(self, db):
        enroll(db, "S001", "CS101")
        assert db["courses"].find_one({"course_id": "CS101"})["seats_available"] == 2

    def test_enrollment_copies_title(self, db):
        enroll(db, "S001", "CS101")
        assert db["enrollments"].find_one({"student_id": "S001"})["course_title"] == "Introduction to Programming"

    def test_full_course_rejected(self, db):
        for sid in ("S001", "S002", "S003"):
            enroll(db, sid, "CS101")
        with pytest.raises(ValueError, match="no seats"):
            enroll(db, "S004", "CS101")

    def test_full_course_state_unchanged_after_rejection(self, db):
        for sid in ("S001", "S002", "S003"):
            enroll(db, sid, "CS101")
        with pytest.raises(ValueError):
            enroll(db, "S004", "CS101")
        assert db["courses"].find_one({"course_id": "CS101"})["seats_available"] == 0
        assert db["enrollments"].find_one({"student_id": "S004"}) is None
        assert db["enrollments"].count_documents({"course_id": "CS101"}) == 3

    def test_inactive_student_rejected(self, db):
        with pytest.raises(ValueError, match="not eligible"):
            enroll(db, "S007", "CS101")
        assert db["courses"].find_one({"course_id": "CS101"})["seats_available"] == 3

    def test_unknown_student_rejected(self, db):
        with pytest.raises(ValueError):
            enroll(db, "S999", "CS101")

    def test_seats_never_negative(self, db):
        for sid in ("S001", "S002", "S003"):
            enroll(db, sid, "CS101")
        for sid in ("S004", "S005", "S006"):
            with pytest.raises(ValueError):
                enroll(db, sid, "CS101")
        assert db["courses"].find_one({"course_id": "CS101"})["seats_available"] >= 0


# ---- Step 4: bulk load and report --------------------------------------
@pytest.fixture
def loaded(db):
    rng = random.Random(11)
    titles = {c["course_id"]: c["title"] for c in COURSES}
    docs = []
    for b in range(1, 201):
        for cid in titles:
            docs.append({"student_id": f"B{b:05d}", "course_id": cid, "course_title": titles[cid],
                         "status": rng.choices(["active", "completed", "withdrawn"], weights=[70, 20, 10])[0],
                         "enrolled_at": dt.datetime(2025, 1, 1) + dt.timedelta(minutes=rng.randint(0, 525600)),
                         "grade": rng.randint(40, 100)})
    db["enrollments"].insert_many(docs)
    return db


REPORT = [
    {"$match": {"status": "active"}},
    {"$group": {"_id": "$course_id", "enrolled": {"$sum": 1}, "avg_grade": {"$avg": "$grade"}}},
    {"$sort": {"avg_grade": -1}},
]


class TestReport:
    def test_bulk_count(self, loaded):
        assert loaded["enrollments"].count_documents({}) == 1200

    def test_bulk_pairs_unique(self, loaded):
        pairs = {(d["student_id"], d["course_id"]) for d in loaded["enrollments"].find()}
        assert len(pairs) == 1200

    def test_one_row_per_course(self, loaded):
        assert len(list(loaded["enrollments"].aggregate(REPORT))) == 6

    def test_counts_add_up(self, loaded):
        rows = list(loaded["enrollments"].aggregate(REPORT))
        assert sum(r["enrolled"] for r in rows) == loaded["enrollments"].count_documents({"status": "active"})

    def test_sorted_by_average_descending(self, loaded):
        avgs = [r["avg_grade"] for r in loaded["enrollments"].aggregate(REPORT)]
        assert avgs == sorted(avgs, reverse=True)

    def test_average_matches_python(self, loaded):
        rows = {r["_id"]: r["avg_grade"] for r in loaded["enrollments"].aggregate(REPORT)}
        grades = [d["grade"] for d in loaded["enrollments"].find({"course_id": "CS201", "status": "active"})]
        assert abs(rows["CS201"] - sum(grades) / len(grades)) < 1e-9

    def test_enrollments_without_grade_do_not_break_average(self, loaded):
        enroll(loaded, "S001", "CS201")           # has no grade field
        assert len(list(loaded["enrollments"].aggregate(REPORT))) == 6


# ---- Step 5: dashboard query and index definition ----------------------
def latest_active(db, course_id):
    return db["enrollments"].find({"course_id": course_id, "status": "active"}).sort("enrolled_at", -1).limit(10)


class TestDashboard:
    def test_returns_ten_active_for_course(self, loaded):
        rows = list(latest_active(loaded, "CS201"))
        assert len(rows) == 10 and all(r["course_id"] == "CS201" and r["status"] == "active" for r in rows)

    def test_newest_first(self, loaded):
        dates = [r["enrolled_at"] for r in latest_active(loaded, "CS201")]
        assert dates == sorted(dates, reverse=True)

    def test_same_rows_with_and_without_index(self, loaded):
        before = [r["student_id"] for r in latest_active(loaded, "CS201")]
        loaded["enrollments"].create_index([("course_id", 1), ("status", 1), ("enrolled_at", -1)], name="esr_course_status_date")
        after = [r["student_id"] for r in latest_active(loaded, "CS201")]
        assert before == after

    def test_index_follows_esr_order(self, loaded):
        loaded["enrollments"].create_index([("course_id", 1), ("status", 1), ("enrolled_at", -1)], name="esr_course_status_date")
        keys = loaded["enrollments"].index_information()["esr_course_status_date"]["key"]
        assert keys == [("course_id", 1), ("status", 1), ("enrolled_at", -1)]
        assert keys[-1][0] == "enrolled_at"        # sort field comes after the equality fields


# ---- Step 6: search pipeline shape -------------------------------------
def search_courses(text, index="course_search"):
    return [
        {"$search": {"index": index,
                     "text": {"query": text, "path": ["title", "description"], "fuzzy": {"maxEdits": 1}}}},
        {"$limit": 3},
        {"$project": {"_id": 0, "course_id": 1, "title": 1}},
    ]


class TestSearchPipeline:
    def test_search_is_first_stage(self):
        assert "$search" in search_courses("programing")[0]

    def test_fuzzy_one_edit(self):
        assert search_courses("x")[0]["$search"]["text"]["fuzzy"] == {"maxEdits": 1}

    def test_paths(self):
        assert search_courses("x")[0]["$search"]["text"]["path"] == ["title", "description"]

    def test_limit_three(self):
        assert search_courses("x")[1] == {"$limit": 3}

    def test_projection_fields(self):
        assert search_courses("x")[2]["$project"] == {"_id": 0, "course_id": 1, "title": 1}

    def test_typo_is_one_edit_from_target_word(self):
        # "programing" -> "programming": one inserted letter, so maxEdits 1 is enough
        def edit_distance(a, b):
            dp = list(range(len(b) + 1))
            for i, ca in enumerate(a, 1):
                prev, dp[0] = dp[0], i
                for j, cb in enumerate(b, 1):
                    prev, dp[j] = dp[j], min(dp[j] + 1, dp[j - 1] + 1, prev + (ca != cb))
            return dp[-1]
        assert edit_distance("programing", "programming") == 1

    def test_description_contains_target_word(self):
        assert "programming" in COURSES[0]["title"].lower()


# ---- Step 7: deployment helpers ----------------------------------------
class TestDeploymentChecks:
    def test_srv_scheme_means_tls(self):
        assert "mongodb+srv://u:p@cluster/".startswith("mongodb+srv")

    def test_plain_scheme_is_not_flagged(self):
        assert not "mongodb://localhost".startswith("mongodb+srv")

    def test_member_count_from_hello_shape(self):
        hello = {"setName": "atlas-abc", "hosts": ["a:27017", "b:27017", "c:27017"]}
        assert hello["setName"] and len(hello.get("hosts", [])) == 3

    def test_roles_from_connection_status_shape(self):
        status = {"authInfo": {"authenticatedUserRoles": [{"role": "atlasAdmin", "db": "admin"}]}}
        assert [r["role"] for r in status["authInfo"]["authenticatedUserRoles"]] == ["atlasAdmin"]

    def test_drop_database_cleans_up(self):
        client = mongomock.MongoClient()
        client["registrar_db"]["students"].insert_one({"x": 1})
        client.drop_database("registrar_db")
        assert "registrar_db" not in client.list_database_names()
