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
def empty_courses(db):
    """Empty courses collection."""
    return db["courses"]


@pytest.fixture
def empty_instructors(db):
    """Empty instructors collection."""
    return db["instructors"]


INSTRUCTOR_RECORDS = [
    {"instructor_id": "INS001", "name": "Dr. Sarah Thorne",  "department": "Computer Science", "bio": "Specializes in algorithms and data structures with 15 years of teaching experience."},
    {"instructor_id": "INS002", "name": "Prof. James Reed",  "department": "Mathematics",      "bio": "Research focus on applied statistics and linear algebra in machine learning."},
    {"instructor_id": "INS003", "name": "Dr. Maria Chen",    "department": "Physics",           "bio": "Expert in computational physics and quantum mechanics simulation."},
]

COURSE_RECORDS = [
    {"course_id": "CS101",   "title": "Introduction to Computer Science",
     "description": "Fundamentals of programming, algorithms, and computational thinking",
     "instructor_id": "INS001", "seats": 120,
     "schedule": {"meeting_times": "MWF 9:00-9:50", "location": "Hamilton Hall Room 204"}},
    {"course_id": "CS201",   "title": "Data Structures and Algorithms",
     "description": "Advanced data structures including trees, graphs, and algorithm analysis",
     "instructor_id": "INS001", "seats": 80,
     "schedule": {"meeting_times": "TTh 10:30-11:45", "location": "Science Building Room 105"}},
    {"course_id": "MATH201", "title": "Linear Algebra",
     "description": "Vectors, matrices, eigenvalues, and applications to data science",
     "instructor_id": "INS002", "seats": 100,
     "schedule": {"meeting_times": "MWF 11:00-11:50", "location": "Math Building Room 301"}},
    {"course_id": "MATH301", "title": "Probability and Statistics",
     "description": "Probability distributions, hypothesis testing, and statistical inference",
     "instructor_id": "INS002", "seats": 75,
     "schedule": {"meeting_times": "TTh 1:00-2:15", "location": "Math Building Room 205"}},
    {"course_id": "PHYS101", "title": "General Physics I",
     "description": "Classical mechanics, thermodynamics, and wave phenomena",
     "instructor_id": "INS003", "seats": 90,
     "schedule": {"meeting_times": "MWF 2:00-2:50", "location": "Physics Lab Room 110"}},
    {"course_id": "PHYS301", "title": "Computational Physics",
     "description": "Numerical methods, scientific computing, and algorithm simulation",
     "instructor_id": "INS003", "seats": 45,
     "schedule": {"meeting_times": "TTh 3:30-4:45", "location": "Physics Lab Room 202"}},
]


@pytest.fixture
def populated(db):
    """Both courses and instructors collections populated with all records."""
    courses = db["courses"]
    instructors = db["instructors"]
    courses.insert_many(COURSE_RECORDS)
    instructors.insert_many(INSTRUCTOR_RECORDS)
    return courses, instructors


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

    def test_instructors_collection_accessible(self, empty_instructors):
        assert empty_instructors is not None


# ---------------------------------------------------------------------------
# 2. Insert Records
# ---------------------------------------------------------------------------

class TestInsertRecords:
    def test_six_courses_inserted(self, populated):
        courses, _ = populated
        assert courses.count_documents({}) == 6

    def test_three_instructors_inserted(self, populated):
        _, instructors = populated
        assert instructors.count_documents({}) == 3

    def test_course_has_all_required_fields(self, populated):
        courses, _ = populated
        first = courses.find_one()
        required = {"course_id", "title", "description", "instructor_id", "seats", "schedule"}
        assert required.issubset(first.keys())

    def test_instructor_has_all_required_fields(self, populated):
        _, instructors = populated
        first = instructors.find_one()
        required = {"instructor_id", "name", "department", "bio"}
        assert required.issubset(first.keys())


# ---------------------------------------------------------------------------
# 3. Embedded Schedule
# ---------------------------------------------------------------------------

class TestEmbeddedSchedule:
    def test_schedule_is_subdocument(self, populated):
        courses, _ = populated
        cs101 = courses.find_one({"course_id": "CS101"})
        assert isinstance(cs101["schedule"], dict)

    def test_schedule_has_meeting_times(self, populated):
        courses, _ = populated
        cs101 = courses.find_one({"course_id": "CS101"})
        assert cs101["schedule"]["meeting_times"] == "MWF 9:00-9:50"

    def test_schedule_has_location(self, populated):
        courses, _ = populated
        cs101 = courses.find_one({"course_id": "CS101"})
        assert cs101["schedule"]["location"] == "Hamilton Hall Room 204"

    def test_all_six_courses_have_schedule(self, populated):
        courses, _ = populated
        for course in courses.find():
            assert "schedule" in course
            assert "meeting_times" in course["schedule"]
            assert "location" in course["schedule"]


# ---------------------------------------------------------------------------
# 4. $lookup Pipeline
# ---------------------------------------------------------------------------

class TestLookupPipeline:
    def test_lookup_returns_all_six_courses(self, populated):
        courses, _ = populated
        pipeline = [
            {"$lookup": {
                "from": "instructors",
                "localField": "instructor_id",
                "foreignField": "instructor_id",
                "as": "instructor_info"
            }}
        ]
        results = list(courses.aggregate(pipeline))
        assert len(results) == 6

    def test_lookup_adds_instructor_info_array(self, populated):
        courses, _ = populated
        pipeline = [
            {"$lookup": {
                "from": "instructors",
                "localField": "instructor_id",
                "foreignField": "instructor_id",
                "as": "instructor_info"
            }}
        ]
        cs101 = [r for r in courses.aggregate(pipeline) if r["course_id"] == "CS101"][0]
        assert "instructor_info" in cs101
        assert len(cs101["instructor_info"]) == 1
        assert cs101["instructor_info"][0]["name"] == "Dr. Sarah Thorne"

    def test_lookup_unwind_flattens_to_single_subdoc(self, populated):
        courses, _ = populated
        pipeline = [
            {"$lookup": {
                "from": "instructors",
                "localField": "instructor_id",
                "foreignField": "instructor_id",
                "as": "instructor_info"
            }},
            {"$unwind": "$instructor_info"}
        ]
        cs101 = [r for r in courses.aggregate(pipeline) if r["course_id"] == "CS101"][0]
        assert isinstance(cs101["instructor_info"], dict)
        assert cs101["instructor_info"]["name"] == "Dr. Sarah Thorne"

    def test_lookup_project_shapes_output(self, populated):
        courses, _ = populated
        pipeline = [
            {"$lookup": {
                "from": "instructors",
                "localField": "instructor_id",
                "foreignField": "instructor_id",
                "as": "instructor_info"
            }},
            {"$unwind": "$instructor_info"},
            {"$project": {
                "_id": 0,
                "course_id": 1,
                "title": 1,
                "instructor_name": "$instructor_info.name",
                "department": "$instructor_info.department"
            }}
        ]
        results = list(courses.aggregate(pipeline))
        assert len(results) == 6
        cs101 = [r for r in results if r["course_id"] == "CS101"][0]
        assert cs101["instructor_name"] == "Dr. Sarah Thorne"
        assert cs101["department"] == "Computer Science"
        assert "_id" not in cs101

    def test_thorne_teaches_two_courses(self, populated):
        courses, _ = populated
        pipeline = [
            {"$lookup": {
                "from": "instructors",
                "localField": "instructor_id",
                "foreignField": "instructor_id",
                "as": "instructor_info"
            }},
            {"$unwind": "$instructor_info"},
            {"$match": {"instructor_info.name": "Dr. Sarah Thorne"}},
            {"$project": {"_id": 0, "course_id": 1, "title": 1}}
        ]
        results = list(courses.aggregate(pipeline))
        assert len(results) == 2
        course_ids = {r["course_id"] for r in results}
        assert course_ids == {"CS101", "CS201"}


# ---------------------------------------------------------------------------
# 5. Text Search (mongomock limitation)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# NOTE: mongomock 4.3.0 does NOT support the $text operator.
# The following test is SKIPPED because mongomock raises:
#   "The $text operator is not implemented in mongomock yet"
#
# This limitation was verified on 2026-08-20 against mongomock 4.3.0.
# The text index creation (create_index([("description", "text")])) succeeds
# silently without error, but any find() query using {"$text": {"$search": ...}}
# raises NotImplementedError.
#
# The text search functionality is validated against the real MongoDB Atlas
# connection in the notebook's Step 5 and Step 6 output, where it correctly
# returns 3 courses for the query 'algorithms' (MongoDB stemming matches both
# "algorithms" and "algorithm"):
#   - CS101: Introduction to Computer Science  (description contains "algorithms")
#   - PHYS301: Computational Physics           (description contains "algorithm")
#   - CS201: Data Structures and Algorithms    (description contains "Algorithms")
# ---------------------------------------------------------------------------

class TestTextSearch:
    @pytest.mark.skip(reason="mongomock 4.3.0 does not support $text operator")
    def test_text_search_algorithms_returns_three_results(self, populated):
        courses, _ = populated
        courses.create_index([("description", "text")])
        results = list(courses.find(
            {"$text": {"$search": "algorithms"}},
            {"_id": 0, "course_id": 1, "title": 1}
        ))
        # MongoDB stemming matches "algorithms", "Algorithms", and "algorithm"
        assert len(results) == 3
        course_ids = {r["course_id"] for r in results}
        assert course_ids == {"CS101", "CS201", "PHYS301"}


# ---------------------------------------------------------------------------
# 6. Aggregation: Average Seats
# ---------------------------------------------------------------------------

class TestAggregation:
    def test_average_seats_is_85(self, populated):
        courses, _ = populated
        pipeline = [{"$group": {"_id": None, "avg_seats": {"$avg": "$seats"}}}]
        result = list(courses.aggregate(pipeline))[0]
        assert abs(result["avg_seats"] - 85.0) < 0.01

    def test_instructor_course_count(self, populated):
        courses, _ = populated
        pipeline = [
            {"$group": {"_id": "$instructor_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        results = {doc["_id"]: doc["count"] for doc in courses.aggregate(pipeline)}
        assert results["INS001"] == 2
        assert results["INS002"] == 2
        assert results["INS003"] == 2


# ---------------------------------------------------------------------------
# 7. Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_courses_aggregation_returns_nothing(self, empty_courses):
        pipeline = [{"$group": {"_id": "$instructor_id", "count": {"$sum": 1}}}]
        results = list(empty_courses.aggregate(pipeline))
        assert len(results) == 0

    def test_drop_courses_clears_all_documents(self, populated):
        courses, _ = populated
        assert courses.count_documents({}) == 6
        courses.drop()
        assert courses.count_documents({}) == 0

    def test_drop_instructors_clears_all_documents(self, populated):
        _, instructors = populated
        assert instructors.count_documents({}) == 3
        instructors.drop()
        assert instructors.count_documents({}) == 0

    def test_drop_and_reinsert_gives_same_count(self, populated):
        courses, instructors = populated
        courses.drop()
        instructors.drop()
        courses.insert_many(COURSE_RECORDS)
        instructors.insert_many(INSTRUCTOR_RECORDS)
        assert courses.count_documents({}) == 6
        assert instructors.count_documents({}) == 3

    def test_all_instructor_ids_are_valid(self, populated):
        courses, instructors = populated
        valid_ids = {ins["instructor_id"] for ins in instructors.find()}
        course_ids = {c["instructor_id"] for c in courses.find()}
        assert course_ids.issubset(valid_ids)

    def test_seats_within_valid_range(self, populated):
        courses, _ = populated
        seats = [c["seats"] for c in courses.find()]
        assert all(0 < s <= 200 for s in seats)
