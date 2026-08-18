import pytest
import mongomock


@pytest.fixture
def db_setup():
    client = mongomock.MongoClient()
    db = client["task_db"]
    tasks = db["tasks"]
    return tasks


@pytest.fixture
def populated_db(db_setup):
    tasks = db_setup
    first_task = {
        "title": "Design login page",
        "description": "Create wireframes for the new login flow",
        "priority": "critical",
        "status": "pending",
        "due_date": "2026-01-20",
        "category": "work"
    }
    tasks.insert_one(first_task)
    remaining_tasks = [
        {"title": "Write unit tests", "description": "Add tests for auth module", "priority": "high", "status": "pending", "due_date": "2026-01-25", "category": "work"},
        {"title": "Fix navigation bug", "description": "Menu not closing on mobile", "priority": "critical", "status": "pending", "due_date": "2026-01-22", "category": "work"},
        {"title": "Deploy staging server", "description": "Push latest build to staging", "priority": "medium", "status": "pending", "due_date": "2026-02-01", "category": "work"},
        {"title": "Learn Docker basics", "description": "Complete Docker tutorial series", "priority": "low", "status": "pending", "due_date": "2026-02-10", "category": "learning"},
        {"title": "Review pull requests", "description": "Review 3 open PRs on GitHub", "priority": "high", "status": "pending", "due_date": "2026-01-28", "category": "work"},
        {"title": "Update documentation", "description": "Refresh API docs with new endpoints", "priority": "medium", "status": "pending", "due_date": "2026-02-05", "category": "work"},
        {"title": "Plan team offsite", "description": "Book venue and send invites", "priority": "low", "status": "pending", "due_date": "2026-02-15", "category": "personal"},
    ]
    tasks.insert_many(remaining_tasks)
    return tasks


class TestConnection:
    def test_mongomock_client_creates(self):
        client = mongomock.MongoClient()
        assert client is not None

    def test_database_created(self):
        client = mongomock.MongoClient()
        db = client["task_db"]
        assert db is not None

    def test_collection_created(self):
        client = mongomock.MongoClient()
        db = client["task_db"]
        tasks = db["tasks"]
        assert tasks is not None


class TestInsertOne:
    def test_insert_one_returns_id(self, db_setup):
        tasks = db_setup
        result = tasks.insert_one({"title": "Test task", "priority": "low"})
        assert result.inserted_id is not None

    def test_insert_one_increases_count(self, db_setup):
        tasks = db_setup
        assert tasks.count_documents({}) == 0
        tasks.insert_one({"title": "Test task", "priority": "low"})
        assert tasks.count_documents({}) == 1


class TestInsertMany:
    def test_insert_many_count(self, populated_db):
        tasks = populated_db
        assert tasks.count_documents({}) == 8

    def test_insert_many_returns_ids(self, populated_db):
        tasks = populated_db
        all_tasks = list(tasks.find({}, {"_id": 0}))
        assert len(all_tasks) == 8


class TestFindAll:
    def test_find_all_returns_8(self, populated_db):
        tasks = populated_db
        all_tasks = list(tasks.find({}, {"_id": 0}))
        assert len(all_tasks) == 8

    def test_find_all_has_expected_titles(self, populated_db):
        tasks = populated_db
        titles = [t["title"] for t in tasks.find({}, {"_id": 0})]
        assert "Design login page" in titles
        assert "Write unit tests" in titles
        assert "Learn Docker basics" in titles


class TestQueryTasksDueSoon:
    def test_due_before_jan31(self, populated_db):
        tasks = populated_db
        due = list(tasks.find(
            {"due_date": {"$lte": "2026-01-31"}, "status": {"$ne": "completed"}},
            {"_id": 0}
        ))
        for t in due:
            assert t["due_date"] <= "2026-01-31"
            assert t["status"] != "completed"

    def test_due_count(self, populated_db):
        tasks = populated_db
        due = list(tasks.find(
            {"due_date": {"$lte": "2026-01-31"}, "status": {"$ne": "completed"}},
            {"_id": 0}
        ))
        assert len(due) == 4


class TestUpdateOne:
    def test_mark_task_completed(self, populated_db):
        tasks = populated_db
        result = tasks.update_one(
            {"title": "Design login page"},
            {"$set": {"status": "completed", "completed_date": "2026-01-19"}}
        )
        assert result.matched_count == 1
        assert result.modified_count == 1

    def test_task_status_changed(self, populated_db):
        tasks = populated_db
        tasks.update_one(
            {"title": "Design login page"},
            {"$set": {"status": "completed", "completed_date": "2026-01-19"}}
        )
        task = tasks.find_one({"title": "Design login page"})
        assert task["status"] == "completed"
        assert task["completed_date"] == "2026-01-19"

    def test_other_fields_preserved(self, populated_db):
        tasks = populated_db
        tasks.update_one(
            {"title": "Design login page"},
            {"$set": {"status": "completed"}}
        )
        task = tasks.find_one({"title": "Design login page"})
        assert task["priority"] == "critical"
        assert task["category"] == "work"


class TestUpdateMany:
    def test_bump_high_to_critical(self, populated_db):
        tasks = populated_db
        result = tasks.update_many(
            {"priority": "high", "status": {"$ne": "completed"}},
            {"$set": {"priority": "critical"}}
        )
        assert result.matched_count == 2
        assert result.modified_count == 2

    def test_no_high_priority_remaining(self, populated_db):
        tasks = populated_db
        tasks.update_many(
            {"priority": "high", "status": {"$ne": "completed"}},
            {"$set": {"priority": "critical"}}
        )
        high = list(tasks.find({"priority": "high"}))
        assert len(high) == 0


class TestUpsert:
    def test_upsert_inserts_new(self, populated_db):
        tasks = populated_db
        before_count = tasks.count_documents({})
        result = tasks.update_one(
            {"title": "Update user profile"},
            {"$set": {"title": "Update user profile", "description": "Add profile photo",
                      "priority": "medium", "status": "pending", "due_date": "2026-02-20",
                      "category": "personal"}},
            upsert=True
        )
        assert result.matched_count == 0
        assert result.upserted_id is not None
        assert tasks.count_documents({}) == before_count + 1

    def test_upsert_updates_existing(self, populated_db):
        tasks = populated_db
        tasks.update_one(
            {"title": "Update user profile"},
            {"$set": {"title": "Update user profile", "description": "Add profile photo",
                      "priority": "medium", "status": "pending", "due_date": "2026-02-20",
                      "category": "personal"}},
            upsert=True
        )
        before_count = tasks.count_documents({})
        result = tasks.update_one(
            {"title": "Update user profile"},
            {"$set": {"priority": "high"}},
            upsert=True
        )
        assert result.matched_count == 1
        assert result.upserted_id is None
        assert tasks.count_documents({}) == before_count


class TestDeleteOne:
    def test_delete_one_removes_task(self, populated_db):
        tasks = populated_db
        before_count = tasks.count_documents({})
        result = tasks.delete_one({"title": "Learn Docker basics"})
        assert result.deleted_count == 1
        assert tasks.count_documents({}) == before_count - 1

    def test_deleted_task_not_found(self, populated_db):
        tasks = populated_db
        tasks.delete_one({"title": "Learn Docker basics"})
        task = tasks.find_one({"title": "Learn Docker basics"})
        assert task is None


class TestDeleteMany:
    def test_delete_completed_tasks(self, populated_db):
        tasks = populated_db
        tasks.update_one(
            {"title": "Design login page"},
            {"$set": {"status": "completed"}}
        )
        result = tasks.delete_many({"status": "completed"})
        assert result.deleted_count == 1
        assert tasks.count_documents({"status": "completed"}) == 0

    def test_delete_many_nonexistent(self, populated_db):
        tasks = populated_db
        before_count = tasks.count_documents({})
        result = tasks.delete_many({"status": "completed"})
        assert result.deleted_count == 0
        assert tasks.count_documents({}) == before_count


class TestQueryOperators:
    def test_ne_operator(self, populated_db):
        tasks = populated_db
        not_completed = list(tasks.find({"status": {"$ne": "completed"}}, {"_id": 0}))
        assert all(t["status"] != "completed" for t in not_completed)

    def test_combined_filter(self, populated_db):
        tasks = populated_db
        critical_pending = list(tasks.find(
            {"priority": "critical", "status": "pending"}, {"_id": 0}
        ))
        for t in critical_pending:
            assert t["priority"] == "critical"
            assert t["status"] == "pending"


class TestSummaryReport:
    def test_report_counts(self, populated_db):
        tasks = populated_db
        all_tasks = list(tasks.find({}, {"_id": 0}))
        assert len(all_tasks) == 8

    def test_high_priority_filter(self, populated_db):
        tasks = populated_db
        all_tasks = list(tasks.find({}, {"_id": 0}))
        high = [t for t in all_tasks if t["priority"] in ("critical", "high")]
        assert len(high) == 4

    def test_overdue_filter(self, populated_db):
        tasks = populated_db
        all_tasks = list(tasks.find({}, {"_id": 0}))
        overdue = [t for t in all_tasks if t["due_date"] < "2026-01-31" and t["status"] != "completed"]
        assert len(overdue) == 4

    def test_sorted_by_due_date(self, populated_db):
        tasks = populated_db
        all_tasks = list(tasks.find({}, {"_id": 0}))
        sorted_tasks = sorted(all_tasks, key=lambda x: x["due_date"])
        dates = [t["due_date"] for t in sorted_tasks]
        assert dates == sorted(dates)


class TestDocumentIntegrity:
    def test_all_tasks_have_required_fields(self, populated_db):
        tasks = populated_db
        required = {"title", "description", "priority", "status", "due_date", "category"}
        for t in tasks.find({}, {"_id": 0}):
            assert required.issubset(t.keys())

    def test_valid_priority_values(self, populated_db):
        tasks = populated_db
        valid = {"critical", "high", "medium", "low"}
        priorities = set(t["priority"] for t in tasks.find({}, {"_id": 0}))
        assert priorities.issubset(valid)

    def test_valid_status_values(self, populated_db):
        tasks = populated_db
        valid = {"pending", "in_progress", "completed"}
        statuses = set(t["status"] for t in tasks.find({}, {"_id": 0}))
        assert statuses.issubset(valid)
