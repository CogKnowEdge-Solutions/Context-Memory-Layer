import pytest
import mongomock


@pytest.fixture
def db_setup():
    client = mongomock.MongoClient()
    db = client["school_db"]
    students = db["students"]
    return students


@pytest.fixture
def populated_db(db_setup):
    students = db_setup
    student_records = [
        {"name": "Alice Johnson", "student_id": "STU001", "course": "Computer Science", "grade": 95, "enrollment_date": "2024-09-01", "status": "active"},
        {"name": "Bob Smith", "student_id": "STU002", "course": "Mathematics", "grade": 78, "enrollment_date": "2024-09-01", "status": "active"},
        {"name": "Charlie Brown", "student_id": "STU003", "course": "Physics", "grade": 55, "enrollment_date": "2024-09-02", "status": "active"},
        {"name": "Diana Prince", "student_id": "STU004", "course": "English", "grade": 48, "enrollment_date": "2024-09-01", "status": "active"},
        {"name": "Eve Torres", "student_id": "STU005", "course": "Biology", "grade": 88, "enrollment_date": "2024-09-03", "status": "active"},
        {"name": "Frank Castle", "student_id": "STU006", "course": "Mathematics", "grade": 52, "enrollment_date": "2024-09-01", "status": "inactive"},
        {"name": "Grace Hopper", "student_id": "STU007", "course": "Computer Science", "grade": 91, "enrollment_date": "2024-09-02", "status": "active"},
        {"name": "Hank Pym", "student_id": "STU008", "course": "Physics", "grade": 73, "enrollment_date": "2024-09-01", "status": "active"},
        {"name": "Ivan Petrov", "student_id": "STU009", "course": "Computer Science", "grade": 84, "enrollment_date": "2024-09-03", "status": "active"},
        {"name": "Julia Child", "student_id": "STU010", "course": "English", "grade": 90, "enrollment_date": "2024-09-02", "status": "graduated"},
        {"name": "Karl Marx", "student_id": "STU011", "course": "Mathematics", "grade": 67, "enrollment_date": "2024-09-01", "status": "active"},
        {"name": "Laura Palmer", "student_id": "STU012", "course": "Biology", "grade": 45, "enrollment_date": "2024-09-02", "status": "active"},
        {"name": "Marco Polo", "student_id": "STU013", "course": "Physics", "grade": 82, "enrollment_date": "2024-09-03", "status": "active"},
        {"name": "Nina Simone", "student_id": "STU014", "course": "English", "grade": 76, "enrollment_date": "2024-09-01", "status": "active"},
        {"name": "Oscar Wilde", "student_id": "STU015", "course": "Mathematics", "grade": 93, "enrollment_date": "2024-09-02", "status": "active"},
        {"name": "Pia Zadora", "student_id": "STU016", "course": "Biology", "grade": 71, "enrollment_date": "2024-09-01", "status": "active"},
        {"name": "Quincy Adams", "student_id": "STU017", "course": "Computer Science", "grade": 87, "enrollment_date": "2024-09-03", "status": "active"},
        {"name": "Rosa Parks", "student_id": "STU018", "course": "English", "grade": 58, "enrollment_date": "2024-09-02", "status": "inactive"},
        {"name": "Sam Wilson", "student_id": "STU019", "course": "Physics", "grade": 98, "enrollment_date": "2024-09-01", "status": "active"},
        {"name": "Tina Turner", "student_id": "STU020", "course": "Mathematics", "grade": 79, "enrollment_date": "2024-09-03", "status": "active"},
        {"name": "Uma Thurman", "student_id": "STU021", "course": "Computer Science", "grade": 62, "enrollment_date": "2024-09-02", "status": "active"},
        {"name": "Vera Wang", "student_id": "STU022", "course": "Biology", "grade": 85, "enrollment_date": "2024-09-01", "status": "graduated"},
        {"name": "Walt Disney", "student_id": "STU023", "course": "Physics", "grade": 56, "enrollment_date": "2024-09-02", "status": "active"},
        {"name": "Xena Warrior", "student_id": "STU024", "course": "English", "grade": 94, "enrollment_date": "2024-09-03", "status": "active"},
        {"name": "Yusuf Islam", "student_id": "STU025", "course": "Computer Science", "grade": 70, "enrollment_date": "2024-09-01", "status": "active"},
    ]
    result = students.insert_many(student_records)
    return students, len(result.inserted_ids)


class TestConnection:
    def test_mongomock_client_creates(self):
        client = mongomock.MongoClient()
        assert client is not None

    def test_database_created(self):
        client = mongomock.MongoClient()
        db = client["school_db"]
        assert db is not None

    def test_collection_created(self):
        client = mongomock.MongoClient()
        db = client["school_db"]
        students = db["students"]
        assert students is not None


class TestInsertRecords:
    def test_insert_count(self, populated_db):
        students, count = populated_db
        assert count == 25

    def test_total_documents(self, populated_db):
        students, _ = populated_db
        assert students.count_documents({}) == 25

    def test_document_has_required_fields(self, populated_db):
        students, _ = populated_db
        first = students.find_one()
        for field in ["name", "student_id", "course", "grade", "enrollment_date", "status"]:
            assert field in first, f"Missing field: {field}"

    def test_student_ids_unique(self, populated_db):
        students, _ = populated_db
        all_ids = [s["student_id"] for s in students.find({}, {"_id": 0})]
        assert len(all_ids) == len(set(all_ids))

    def test_grade_range(self, populated_db):
        students, _ = populated_db
        grades = [s["grade"] for s in students.find({}, {"_id": 0})]
        assert all(0 <= g <= 100 for g in grades)


class TestQueryFailingStudents:
    def test_count_failing(self, populated_db):
        students, _ = populated_db
        failing = list(students.find({"grade": {"$lt": 60}}, {"_id": 0}))
        assert len(failing) == 6

    def test_failing_names(self, populated_db):
        students, _ = populated_db
        failing = [s["name"] for s in students.find({"grade": {"$lt": 60}}, {"_id": 0})]
        expected = ["Charlie Brown", "Diana Prince", "Frank Castle", "Laura Palmer", "Rosa Parks", "Walt Disney"]
        assert sorted(failing) == sorted(expected)

    def test_all_failing_grades_below_60(self, populated_db):
        students, _ = populated_db
        failing = list(students.find({"grade": {"$lt": 60}}, {"_id": 0}))
        assert all(s["grade"] < 60 for s in failing)


class TestQueryCSStudentsSorted:
    def test_cs_student_count(self, populated_db):
        students, _ = populated_db
        cs = list(students.find({"course": "Computer Science"}, {"_id": 0}))
        assert len(cs) == 6

    def test_cs_sorted_descending(self, populated_db):
        students, _ = populated_db
        cs = list(students.find({"course": "Computer Science"}, {"_id": 0}).sort("grade", -1))
        grades = [s["grade"] for s in cs]
        assert grades == sorted(grades, reverse=True)

    def test_top_cs_student(self, populated_db):
        students, _ = populated_db
        top = students.find({"course": "Computer Science"}, {"_id": 0}).sort("grade", -1).limit(1)[0]
        assert top["name"] == "Alice Johnson"
        assert top["grade"] == 95


class TestAggregationEnrollment:
    def test_course_count_keys(self, populated_db):
        students, _ = populated_db
        pipeline = [
            {"$group": {"_id": "$course", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        results = {doc["_id"]: doc["count"] for doc in students.aggregate(pipeline)}
        expected_courses = {"Computer Science", "English", "Mathematics", "Physics", "Biology"}
        assert set(results.keys()) == expected_courses

    def test_cs_enrollment_count(self, populated_db):
        students, _ = populated_db
        pipeline = [{"$group": {"_id": "$course", "count": {"$sum": 1}}}]
        results = {doc["_id"]: doc["count"] for doc in students.aggregate(pipeline)}
        assert results["Computer Science"] == 6

    def test_total_enrollment(self, populated_db):
        students, _ = populated_db
        pipeline = [{"$group": {"_id": "$course", "count": {"$sum": 1}}}]
        total = sum(doc["count"] for doc in students.aggregate(pipeline))
        assert total == 25


class TestProjection:
    def test_id_excluded(self, populated_db):
        students, _ = populated_db
        result = students.find_one({}, {"_id": 0})
        assert "_id" not in result

    def test_specific_fields(self, populated_db):
        students, _ = populated_db
        result = students.find_one({}, {"_id": 0, "name": 1, "grade": 1})
        assert "name" in result
        assert "grade" in result
        assert "course" not in result


class TestSummaryReport:
    def test_report_total_count(self, populated_db):
        students, _ = populated_db
        total = students.count_documents({})
        assert total == 25

    def test_report_failing_count(self, populated_db):
        students, _ = populated_db
        failing = list(students.find({"grade": {"$lt": 60}}, {"_id": 0}))
        assert len(failing) == 6

    def test_report_top_cs(self, populated_db):
        students, _ = populated_db
        top_cs = list(students.find({"course": "Computer Science"}, {"_id": 0}).sort("grade", -1))
        assert len(top_cs) > 0
        assert top_cs[0]["name"] == "Alice Johnson"


class TestStatusValues:
    def test_only_valid_statuses(self, populated_db):
        students, _ = populated_db
        valid = {"active", "inactive", "graduated"}
        statuses = set(s["status"] for s in students.find({}, {"_id": 0}))
        assert statuses.issubset(valid)
