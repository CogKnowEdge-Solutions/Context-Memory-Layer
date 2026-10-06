import json
import math
import os

import pytest
import mongomock

# NOTE: $search and $vectorSearch only run on MongoDB Atlas, and the embedding model
# needs a download, so these tests cover everything that can be checked offline:
# the catalog data, the pipeline builders, Reciprocal Rank Fusion, the index
# definitions, cosine ranking (what $vectorSearch does conceptually) and the
# RAG context formatter. Live search behaviour is verified by running the notebook on Atlas.

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG_PATH = os.path.join(HERE, "course_catalog.json")

TEXT_INDEX = "course_text_index"
VECTOR_INDEX = "course_vector_index"
EMBED_DIMS = 384


# ---------------------------------------------------------------------------
# Re-implementation of notebook helpers (identical logic)
# ---------------------------------------------------------------------------

def text_pipeline(query, limit=5, fuzzy=False, level=None):
    text_clause = {"text": {"query": query, "path": ["title", "description"]}}
    if fuzzy:
        text_clause["text"]["fuzzy"] = {"maxEdits": 1}
    if level is None:
        search = {"index": TEXT_INDEX, **text_clause}
    else:
        search = {"index": TEXT_INDEX, "compound": {
            "must": [text_clause],
            "filter": [{"equals": {"path": "level", "value": level}}],
        }}
    return [
        {"$search": search},
        {"$limit": limit},
        {"$project": {"_id": 0, "course_id": 1, "title": 1, "level": 1,
                      "score": {"$meta": "searchScore"}}},
    ]


def vector_pipeline(query_vector, limit=5, level=None, num_candidates=100):
    stage = {"index": VECTOR_INDEX, "path": "embedding", "queryVector": query_vector,
             "numCandidates": num_candidates, "limit": limit}
    if level is not None:
        stage["filter"] = {"level": level}
    return [
        {"$vectorSearch": stage},
        {"$project": {"_id": 0, "course_id": 1, "title": 1, "level": 1,
                      "score": {"$meta": "vectorSearchScore"}}},
    ]


def rrf_fuse(rankings, k=60):
    scores = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)


def build_context(results):
    blocks = []
    for number, doc in enumerate(results, 1):
        blocks.append(f"[{number}] {doc['title']} ({doc['level']})\n{doc['description']}")
    return "\n\n".join(blocks)


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def brute_force_top(query_vec, docs, limit=3, level=None):
    pool = [d for d in docs if level is None or d["level"] == level]
    ranked = sorted(pool, key=lambda d: cosine(query_vec, d["embedding"]), reverse=True)
    return [d["course_id"] for d in ranked[:limit]]


@pytest.fixture(scope="module")
def courses():
    with open(CATALOG_PATH) as f:
        return json.load(f)


@pytest.fixture
def catalog(courses):
    coll = mongomock.MongoClient()["school_db"]["catalog_courses"]
    coll.insert_many([dict(c) for c in courses])
    return coll


# ---------------------------------------------------------------------------
# 1. Catalog data
# ---------------------------------------------------------------------------

class TestCatalogFile:
    def test_file_exists(self):
        assert os.path.exists(CATALOG_PATH)

    def test_twenty_two_courses(self, courses):
        assert len(courses) == 22

    def test_required_fields(self, courses):
        for c in courses:
            assert {"course_id", "title", "level", "topic", "description"} <= set(c)

    def test_ids_unique(self, courses):
        ids = [c["course_id"] for c in courses]
        assert len(ids) == len(set(ids))

    def test_levels_valid(self, courses):
        assert {c["level"] for c in courses} == {"beginner", "intermediate", "advanced"}

    def test_level_counts(self, courses):
        counts = {}
        for c in courses:
            counts[c["level"]] = counts.get(c["level"], 0) + 1
        assert counts == {"beginner": 7, "intermediate": 7, "advanced": 8}

    def test_descriptions_substantial(self, courses):
        for c in courses:
            assert len(c["description"]) > 60

    def test_target_course_exists(self, courses):
        target = next(c for c in courses if c["course_id"] == "CAT303")
        assert "Conversation" in target["title"]

    def test_semantic_gap_question_shares_no_content_words_with_target(self, courses):
        question = "make my chatbot remember what customers told it yesterday"
        target = next(c for c in courses if c["course_id"] == "CAT303")
        words = {w.strip(".,").lower() for w in (target["title"] + " " + target["description"]).split()}
        content = {"chatbot", "remember", "customers", "told", "yesterday"}
        assert not (content & words)

    def test_typo_demo_term_exists_in_catalog(self, courses):
        text = " ".join((c["title"] + " " + c["description"]).lower() for c in courses)
        assert "databases" in text
        assert "databses" not in text


# ---------------------------------------------------------------------------
# 2. Collection loading
# ---------------------------------------------------------------------------

class TestLoading:
    def test_count(self, catalog):
        assert catalog.count_documents({}) == 22

    def test_filter_by_level(self, catalog):
        assert catalog.count_documents({"level": "advanced"}) == 8

    def test_embedding_update_pattern(self, catalog):
        catalog.update_one({"course_id": "CAT301"}, {"$set": {"embedding": [0.1] * EMBED_DIMS}})
        doc = catalog.find_one({"course_id": "CAT301"})
        assert len(doc["embedding"]) == EMBED_DIMS

    def test_documents_without_embedding_detectable(self, catalog):
        catalog.update_one({"course_id": "CAT301"}, {"$set": {"embedding": [0.1] * EMBED_DIMS}})
        assert catalog.count_documents({"embedding": {"$exists": True}}) == 1


# ---------------------------------------------------------------------------
# 3. Pipeline builders
# ---------------------------------------------------------------------------

class TestTextPipeline:
    def test_search_is_first_stage(self):
        assert "$search" in text_pipeline("data")[0]

    def test_index_name(self):
        assert text_pipeline("data")[0]["$search"]["index"] == TEXT_INDEX

    def test_paths_include_title_and_description(self):
        assert text_pipeline("data")[0]["$search"]["text"]["path"] == ["title", "description"]

    def test_no_fuzzy_by_default(self):
        assert "fuzzy" not in text_pipeline("data")[0]["$search"]["text"]

    def test_fuzzy_flag_adds_max_edits_one(self):
        assert text_pipeline("data", fuzzy=True)[0]["$search"]["text"]["fuzzy"] == {"maxEdits": 1}

    def test_limit_stage(self):
        assert text_pipeline("data", limit=3)[1] == {"$limit": 3}

    def test_project_exposes_search_score(self):
        assert text_pipeline("data")[2]["$project"]["score"] == {"$meta": "searchScore"}

    def test_level_uses_compound_with_filter(self):
        search = text_pipeline("data", level="advanced")[0]["$search"]
        assert "compound" in search and "text" not in search
        assert search["compound"]["filter"] == [{"equals": {"path": "level", "value": "advanced"}}]
        assert len(search["compound"]["must"]) == 1

    def test_compound_must_keeps_fuzzy(self):
        search = text_pipeline("data", fuzzy=True, level="beginner")[0]["$search"]
        assert search["compound"]["must"][0]["text"]["fuzzy"] == {"maxEdits": 1}


class TestVectorPipeline:
    VEC = [0.0] * EMBED_DIMS

    def test_vector_search_first_stage(self):
        assert "$vectorSearch" in vector_pipeline(self.VEC)[0]

    def test_required_keys(self):
        stage = vector_pipeline(self.VEC)[0]["$vectorSearch"]
        assert {"index", "path", "queryVector", "numCandidates", "limit"} <= set(stage)

    def test_path_is_embedding(self):
        assert vector_pipeline(self.VEC)[0]["$vectorSearch"]["path"] == "embedding"

    def test_query_vector_dimensions(self):
        assert len(vector_pipeline(self.VEC)[0]["$vectorSearch"]["queryVector"]) == EMBED_DIMS

    def test_no_filter_by_default(self):
        assert "filter" not in vector_pipeline(self.VEC)[0]["$vectorSearch"]

    def test_level_filter(self):
        assert vector_pipeline(self.VEC, level="advanced")[0]["$vectorSearch"]["filter"] == {"level": "advanced"}

    def test_num_candidates_at_least_limit(self):
        stage = vector_pipeline(self.VEC, limit=5)[0]["$vectorSearch"]
        assert stage["numCandidates"] >= stage["limit"]

    def test_score_meta(self):
        assert vector_pipeline(self.VEC)[1]["$project"]["score"] == {"$meta": "vectorSearchScore"}


# ---------------------------------------------------------------------------
# 4. Index definitions
# ---------------------------------------------------------------------------

class TestIndexDefinitions:
    TEXT_DEF = {"mappings": {"dynamic": False, "fields": {
        "title": {"type": "string"}, "description": {"type": "string"}, "level": {"type": "token"}}}}
    VECTOR_DEF = {"fields": [
        {"type": "vector", "path": "embedding", "numDimensions": EMBED_DIMS, "similarity": "cosine"},
        {"type": "filter", "path": "level"}]}

    def test_text_index_not_dynamic(self):
        assert self.TEXT_DEF["mappings"]["dynamic"] is False

    def test_level_is_token(self):
        assert self.TEXT_DEF["mappings"]["fields"]["level"]["type"] == "token"

    def test_text_fields_are_strings(self):
        f = self.TEXT_DEF["mappings"]["fields"]
        assert f["title"]["type"] == f["description"]["type"] == "string"

    def test_vector_dimensions_match_model(self):
        assert self.VECTOR_DEF["fields"][0]["numDimensions"] == 384

    def test_vector_similarity(self):
        assert self.VECTOR_DEF["fields"][0]["similarity"] == "cosine"

    def test_filter_field_declared_for_level(self):
        assert {"type": "filter", "path": "level"} in self.VECTOR_DEF["fields"]

    def test_filter_in_pipeline_matches_declared_filter_field(self):
        declared = {f["path"] for f in self.VECTOR_DEF["fields"] if f["type"] == "filter"}
        used = set(vector_pipeline([0.0] * EMBED_DIMS, level="advanced")[0]["$vectorSearch"]["filter"])
        assert used <= declared

    def test_search_index_model_importable(self):
        from pymongo.operations import SearchIndexModel
        model = SearchIndexModel(definition=self.VECTOR_DEF, name=VECTOR_INDEX, type="vectorSearch")
        assert model.document["name"] == VECTOR_INDEX


# ---------------------------------------------------------------------------
# 5. Reciprocal Rank Fusion
# ---------------------------------------------------------------------------

class TestRRF:
    def test_single_list_preserves_order(self):
        assert [i for i, _ in rrf_fuse([["a", "b", "c"]])] == ["a", "b", "c"]

    def test_score_formula(self):
        scores = dict(rrf_fuse([["a"]]))
        assert abs(scores["a"] - 1 / 61) < 1e-12

    def test_item_in_both_lists_beats_item_in_one(self):
        fused = rrf_fuse([["x", "y"], ["z", "x"]])
        assert fused[0][0] == "x"

    def test_assignment_example_ranking(self):
        fused = rrf_fuse([["C", "A", "D"], ["A", "B", "C"]])
        assert [i for i, _ in fused] == ["A", "C", "B", "D"]

    def test_assignment_example_scores(self):
        scores = dict(rrf_fuse([["C", "A", "D"], ["A", "B", "C"]]))
        assert round(scores["A"], 4) == 0.0325
        assert round(scores["C"], 4) == 0.0323
        assert round(scores["B"], 4) == 0.0161
        assert round(scores["D"], 4) == 0.0159

    def test_lab4_quiz_example(self):
        # Rank 1 in one list and rank 3 in the other, k = 60
        assert round(1 / 61 + 1 / 63, 4) == 0.0323

    def test_smaller_k_increases_rank_one_advantage(self):
        gap60 = 1 / 61 - 1 / 65
        gap5 = 1 / 6 - 1 / 10
        assert gap5 > gap60

    def test_empty_lists(self):
        assert rrf_fuse([[], []]) == []

    def test_scores_sorted_descending(self):
        fused = rrf_fuse([["a", "b", "c", "d"], ["d", "c", "b", "a"]])
        values = [s for _, s in fused]
        assert values == sorted(values, reverse=True)

    def test_union_of_ids(self):
        fused = rrf_fuse([["a", "b"], ["c"]])
        assert {i for i, _ in fused} == {"a", "b", "c"}


# ---------------------------------------------------------------------------
# 6. Nearest-neighbour logic (what $vectorSearch does conceptually)
# ---------------------------------------------------------------------------

class TestCosineRanking:
    DOCS = [
        {"course_id": "memory", "level": "advanced", "embedding": [1.0, 0.9, 0.0]},
        {"course_id": "sql", "level": "beginner", "embedding": [0.0, 0.1, 1.0]},
        {"course_id": "rag", "level": "advanced", "embedding": [0.9, 1.0, 0.1]},
        {"course_id": "html", "level": "beginner", "embedding": [0.1, 0.0, 0.9]},
    ]

    def test_identical_vectors_have_cosine_one(self):
        assert abs(cosine([1, 2, 3], [1, 2, 3]) - 1.0) < 1e-12

    def test_orthogonal_vectors_have_cosine_zero(self):
        assert abs(cosine([1, 0], [0, 1])) < 1e-12

    def test_cosine_ignores_length(self):
        assert abs(cosine([1, 1], [5, 5]) - 1.0) < 1e-12

    def test_nearest_to_ai_query_is_ai_course(self):
        top = brute_force_top([1.0, 1.0, 0.0], self.DOCS, limit=2)
        assert set(top) == {"memory", "rag"}

    def test_nearest_to_database_query(self):
        top = brute_force_top([0.0, 0.0, 1.0], self.DOCS, limit=2)
        assert set(top) == {"sql", "html"}

    def test_level_prefilter(self):
        top = brute_force_top([0.0, 0.0, 1.0], self.DOCS, limit=5, level="advanced")
        assert set(top) == {"memory", "rag"}

    def test_limit_respected(self):
        assert len(brute_force_top([1, 1, 1], self.DOCS, limit=3)) == 3


# ---------------------------------------------------------------------------
# 7. RAG context block
# ---------------------------------------------------------------------------

class TestContextBlock:
    RESULTS = [
        {"title": "Alpha", "level": "advanced", "description": "First description."},
        {"title": "Beta", "level": "beginner", "description": "Second description."},
    ]

    def test_numbering(self):
        ctx = build_context(self.RESULTS)
        assert ctx.startswith("[1] Alpha (advanced)")
        assert "[2] Beta (beginner)" in ctx

    def test_descriptions_included(self):
        ctx = build_context(self.RESULTS)
        assert "First description." in ctx and "Second description." in ctx

    def test_blocks_separated_by_blank_line(self):
        assert "\n\n[2]" in build_context(self.RESULTS)

    def test_empty_results(self):
        assert build_context([]) == ""

    def test_single_result_has_no_separator(self):
        assert "\n\n" not in build_context(self.RESULTS[:1])
