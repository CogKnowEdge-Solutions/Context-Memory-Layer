import pytest
import mongomock
import re


@pytest.fixture
def db_setup():
    client = mongomock.MongoClient()
    db = client["blog_platform"]
    tenants = db["tenants"]
    posts = db["posts"]
    comments = db["comments"]
    return tenants, posts, comments


@pytest.fixture
def populated_db(db_setup):
    tenants, posts, comments = db_setup

    tenant_data = [
        {"tenant_id": "T001", "name": "Alice", "blog_title": "Alice's Tech Blog", "created_at": "2024-06-01"},
        {"tenant_id": "T002", "name": "Bob", "blog_title": "Bob's Data Corner", "created_at": "2024-08-15"},
        {"tenant_id": "T003", "name": "Charlie", "blog_title": "Charlie's Code World", "created_at": "2025-01-10"},
    ]
    tenants.insert_many(tenant_data)

    post_data = [
        {"post_id": "P001", "tenant_id": "T001", "title": "Getting Started with MongoDB",
         "body": "MongoDB is a document database that stores data as JSON.", "tags": ["mongodb", "nosql", "beginner"], "created_at": "2024-07-01"},
        {"post_id": "P002", "tenant_id": "T001", "title": "Advanced Aggregation Pipelines",
         "body": "Aggregation pipelines let you transform data step by step.", "tags": ["mongodb", "aggregation", "advanced"], "created_at": "2024-09-10"},
        {"post_id": "P003", "tenant_id": "T001", "title": "Python for Data Science",
         "body": "Python is the go-to language for data analysis and ML.", "tags": ["python", "data"], "created_at": "2025-02-01"},
        {"post_id": "P004", "tenant_id": "T002", "title": "Schema Design Patterns",
         "body": "Choosing between embedding and referencing is a key design decision.", "tags": ["mongodb", "schema", "design"], "created_at": "2024-10-05"},
        {"post_id": "P005", "tenant_id": "T002", "title": "Indexing Strategies",
         "body": "Indexes speed up reads but slow down writes.", "tags": ["mongodb", "indexing", "performance"], "created_at": "2024-12-20"},
        {"post_id": "P006", "tenant_id": "T002", "title": "Building Data Pipelines",
         "body": "ETL pipelines move data from source to destination.", "tags": ["data", "etl", "pipeline"], "created_at": "2025-03-15"},
        {"post_id": "P007", "tenant_id": "T003", "title": "REST API Design",
         "body": "A good REST API is predictable and consistent.", "tags": ["api", "rest", "design"], "created_at": "2025-01-20"},
        {"post_id": "P008", "tenant_id": "T003", "title": "Docker for Developers",
         "body": "Containers package your app with all its dependencies.", "tags": ["docker", "devops", "containers"], "created_at": "2025-04-01"},
    ]
    posts.insert_many(post_data)

    comment_data = [
        {"comment_id": "C001", "post_id": "P001", "author": "Eve", "text": "Great intro to MongoDB!", "created_at": "2024-07-05"},
        {"comment_id": "C002", "post_id": "P001", "author": "Grace", "text": "Very helpful for beginners.", "created_at": "2024-07-06"},
        {"comment_id": "C003", "post_id": "P001", "author": "Hank", "text": "Thanks for sharing.", "created_at": "2024-07-10"},
        {"comment_id": "C004", "post_id": "P002", "author": "Eve", "text": "The $lookup examples were eye-opening.", "created_at": "2024-09-12"},
        {"comment_id": "C005", "post_id": "P002", "author": "Alice", "text": "Can you cover $graphLookup next?", "created_at": "2024-09-15"},
        {"comment_id": "C006", "post_id": "P004", "author": "Charlie", "text": "Embedding vs referencing explained well.", "created_at": "2024-10-08"},
        {"comment_id": "C007", "post_id": "P004", "author": "Grace", "text": "I chose embedding for my project after reading this.", "created_at": "2024-10-10"},
        {"comment_id": "C008", "post_id": "P005", "author": "Hank", "text": "Compound indexes are a game changer.", "created_at": "2024-12-22"},
        {"comment_id": "C009", "post_id": "P007", "author": "Bob", "text": "Clear and concise API guide.", "created_at": "2025-01-25"},
        {"comment_id": "C010", "post_id": "P008", "author": "Alice", "text": "Docker made deployment so much easier.", "created_at": "2025-04-03"},
    ]
    comments.insert_many(comment_data)

    return tenants, posts, comments


class TestConnection:
    def test_mongomock_client_creates(self):
        client = mongomock.MongoClient()
        assert client is not None

    def test_database_created(self):
        client = mongomock.MongoClient()
        db = client["blog_platform"]
        assert db is not None

    def test_all_three_collections_exist(self):
        client = mongomock.MongoClient()
        db = client["blog_platform"]
        assert db["tenants"] is not None
        assert db["posts"] is not None
        assert db["comments"] is not None


class TestSeedData:
    def test_tenant_count(self, populated_db):
        tenants, _, _ = populated_db
        assert tenants.count_documents({}) == 3

    def test_post_count(self, populated_db):
        _, posts, _ = populated_db
        assert posts.count_documents({}) == 8

    def test_comment_count(self, populated_db):
        _, _, comments = populated_db
        assert comments.count_documents({}) == 10

    def test_tenant_has_required_fields(self, populated_db):
        tenants, _, _ = populated_db
        t = tenants.find_one()
        for field in ["tenant_id", "name", "blog_title", "created_at"]:
            assert field in t, f"Missing field: {field}"

    def test_post_has_required_fields(self, populated_db):
        _, posts, _ = populated_db
        p = posts.find_one()
        for field in ["post_id", "tenant_id", "title", "body", "tags", "created_at"]:
            assert field in p, f"Missing field: {field}"

    def test_comment_has_required_fields(self, populated_db):
        _, _, comments = populated_db
        c = comments.find_one()
        for field in ["comment_id", "post_id", "author", "text", "created_at"]:
            assert field in c, f"Missing field: {field}"

    def test_post_tags_is_array(self, populated_db):
        _, posts, _ = populated_db
        p = posts.find_one({"post_id": "P001"})
        assert isinstance(p["tags"], list)
        assert len(p["tags"]) > 0


class TestEmbedding:
    def test_tags_embedded_in_post(self, populated_db):
        _, posts, _ = populated_db
        post = posts.find_one({"post_id": "P001"})
        assert "mongodb" in post["tags"]
        assert "nosql" in post["tags"]
        assert "beginner" in post["tags"]

    def test_tags_vary_per_post(self, populated_db):
        _, posts, _ = populated_db
        p1 = posts.find_one({"post_id": "P001"})
        p7 = posts.find_one({"post_id": "P007"})
        assert p1["tags"] != p7["tags"]


class TestLookupPostWithTenant:
    def test_lookup_returns_tenant_info(self, populated_db):
        _, posts, _ = populated_db
        pipeline = [
            {"$lookup": {
                "from": "tenants",
                "localField": "tenant_id",
                "foreignField": "tenant_id",
                "as": "tenant"
            }},
            {"$limit": 1}
        ]
        result = list(posts.aggregate(pipeline))
        assert len(result) == 1
        assert "tenant" in result[0]
        assert len(result[0]["tenant"]) == 1

    def test_lookup_unwind_preserves_post_count(self, populated_db):
        _, posts, _ = populated_db
        pipeline = [
            {"$lookup": {
                "from": "tenants",
                "localField": "tenant_id",
                "foreignField": "tenant_id",
                "as": "tenant"
            }},
            {"$unwind": "$tenant"},
        ]
        result = list(posts.aggregate(pipeline))
        assert len(result) == 8

    def test_all_posts_have_tenant_name(self, populated_db):
        _, posts, _ = populated_db
        pipeline = [
            {"$lookup": {
                "from": "tenants",
                "localField": "tenant_id",
                "foreignField": "tenant_id",
                "as": "tenant"
            }},
            {"$unwind": "$tenant"},
            {"$project": {"_id": 0, "title": 1, "tenant_name": "$tenant.blog_title"}}
        ]
        results = list(posts.aggregate(pipeline))
        assert len(results) == 8
        for r in results:
            assert "tenant_name" in r
            assert r["tenant_name"] in ("Alice's Tech Blog", "Bob's Data Corner", "Charlie's Code World")


class TestLookupCommentsPerPost:
    def test_comments_joined_to_posts(self, populated_db):
        _, posts, _ = populated_db
        pipeline = [
            {"$lookup": {
                "from": "comments",
                "localField": "post_id",
                "foreignField": "post_id",
                "as": "post_comments"
            }},
            {"$limit": 1}
        ]
        result = list(posts.aggregate(pipeline))
        assert len(result) == 1
        assert "post_comments" in result[0]

    def test_post_with_most_comments(self, populated_db):
        _, posts, _ = populated_db
        pipeline = [
            {"$lookup": {
                "from": "comments",
                "localField": "post_id",
                "foreignField": "post_id",
                "as": "post_comments"
            }},
            {"$addFields": {"comment_count": {"$size": "$post_comments"}}},
            {"$sort": {"comment_count": -1}},
            {"$limit": 1}
        ]
        result = list(posts.aggregate(pipeline))
        assert result[0]["post_id"] == "P001"
        assert result[0]["comment_count"] == 3

    def test_posts_without_comments_filtered(self, populated_db):
        _, posts, _ = populated_db
        pipeline = [
            {"$lookup": {
                "from": "comments",
                "localField": "post_id",
                "foreignField": "post_id",
                "as": "post_comments"
            }},
            {"$match": {"post_comments": {"$ne": []}}},
            {"$count": "total"}
        ]
        result = list(posts.aggregate(pipeline))
        posts_with_comments = result[0]["total"]
        assert posts_with_comments == 6


class TestKeywordSearch:
    def test_regex_finds_matching_posts(self, populated_db):
        _, posts, _ = populated_db
        pattern = re.compile("python", re.IGNORECASE)
        matching = list(posts.find({
            "$or": [
                {"title": {"$regex": pattern}},
                {"body": {"$regex": pattern}}
            ]
        }))
        assert len(matching) >= 1
        titles = [m["title"] for m in matching]
        assert "Python for Data Science" in titles

    def test_regex_case_insensitive(self, populated_db):
        _, posts, _ = populated_db
        pattern = re.compile("DOCKER", re.IGNORECASE)
        matching = list(posts.find({
            "$or": [
                {"title": {"$regex": pattern}},
                {"body": {"$regex": pattern}}
            ]
        }))
        assert len(matching) >= 1
        assert any("Docker" in m["title"] for m in matching)

    def test_regex_no_match(self, populated_db):
        _, posts, _ = populated_db
        pattern = re.compile("kubernetes", re.IGNORECASE)
        matching = list(posts.find({
            "$or": [
                {"title": {"$regex": pattern}},
                {"body": {"$regex": pattern}}
            ]
        }))
        assert len(matching) == 0


class TestAggregation:
    def test_posts_per_tenant(self, populated_db):
        _, posts, _ = populated_db
        pipeline = [
            {"$group": {"_id": "$tenant_id", "post_count": {"$sum": 1}}},
            {"$sort": {"post_count": -1}}
        ]
        results = list(posts.aggregate(pipeline))
        counts = {r["_id"]: r["post_count"] for r in results}
        assert counts["T001"] == 3
        assert counts["T002"] == 3
        assert counts["T003"] == 2

    def test_tags_unwind_count(self, populated_db):
        _, posts, _ = populated_db
        pipeline = [
            {"$unwind": "$tags"},
            {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        results = list(posts.aggregate(pipeline))
        assert len(results) > 0
        tag_counts = {r["_id"]: r["count"] for r in results}
        assert "mongodb" in tag_counts
        assert tag_counts["mongodb"] == 4

    def test_total_tags_count(self, populated_db):
        _, posts, _ = populated_db
        pipeline = [
            {"$unwind": "$tags"},
            {"$count": "total"}
        ]
        results = list(posts.aggregate(pipeline))
        assert results[0]["total"] == 23


class TestIndexes:
    def test_create_tenant_id_index(self, populated_db):
        _, posts, _ = populated_db
        posts.create_index("tenant_id")
        assert "tenant_id_1" in posts.index_information()

    def test_create_post_id_index(self, populated_db):
        _, posts, _ = populated_db
        posts.create_index("post_id")
        assert "post_id_1" in posts.index_information()

    def test_create_comments_post_id_index(self, populated_db):
        _, _, comments = populated_db
        comments.create_index("post_id")
        assert "post_id_1" in comments.index_information()

    def test_create_unique_tenant_index(self, populated_db):
        tenants, _, _ = populated_db
        tenants.create_index("tenant_id", unique=True)
        info = tenants.index_information()
        assert any("tenant_id" in k for k in info.keys())

    def test_index_information_returns_dict(self, populated_db):
        _, posts, _ = populated_db
        info = posts.index_information()
        assert isinstance(info, dict)
        assert "_id_" in info
