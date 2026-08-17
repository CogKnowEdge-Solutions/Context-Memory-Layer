import pytest
import mongomock


@pytest.fixture
def db_setup():
    client = mongomock.MongoClient()
    db = client["ecommerce"]
    orders = db["orders"]
    products = db["products"]
    return orders, products


@pytest.fixture
def populated_db(db_setup):
    orders, products = db_setup

    product_catalog = [
        {"product_id": "P001", "name": "Wireless Mouse", "category": "Electronics", "price": 29.99},
        {"product_id": "P002", "name": "Mechanical Keyboard", "category": "Electronics", "price": 89.99},
        {"product_id": "P003", "name": "USB-C Hub", "category": "Electronics", "price": 45.00},
        {"product_id": "P004", "name": "Laptop Stand", "category": "Accessories", "price": 35.00},
        {"product_id": "P005", "name": "Noise Cancelling Headphones", "category": "Electronics", "price": 199.99},
        {"product_id": "P006", "name": "Webcam HD", "category": "Electronics", "price": 59.99},
        {"product_id": "P007", "name": "Desk Lamp", "category": "Accessories", "price": 22.50},
        {"product_id": "P008", "name": "Monitor Arm", "category": "Accessories", "price": 75.00},
        {"product_id": "P009", "name": "Notebook Set", "category": "Stationery", "price": 12.99},
        {"product_id": "P010", "name": "Pen Bundle", "category": "Stationery", "price": 8.50},
    ]
    products.insert_many(product_catalog)

    order_records = [
        {"order_id": "ORD001", "customer": "Alice", "product_id": "P001", "quantity": 2, "date": "2025-01-10", "region": "North"},
        {"order_id": "ORD002", "customer": "Bob", "product_id": "P002", "quantity": 1, "date": "2025-01-12", "region": "South"},
        {"order_id": "ORD003", "customer": "Charlie", "product_id": "P005", "quantity": 1, "date": "2025-01-15", "region": "North"},
        {"order_id": "ORD004", "customer": "Alice", "product_id": "P003", "quantity": 3, "date": "2025-01-20", "region": "North"},
        {"order_id": "ORD005", "customer": "Diana", "product_id": "P004", "quantity": 1, "date": "2025-02-01", "region": "West"},
        {"order_id": "ORD006", "customer": "Eve", "product_id": "P006", "quantity": 2, "date": "2025-02-05", "region": "East"},
        {"order_id": "ORD007", "customer": "Bob", "product_id": "P001", "quantity": 1, "date": "2025-02-10", "region": "South"},
        {"order_id": "ORD008", "customer": "Frank", "product_id": "P007", "quantity": 4, "date": "2025-02-14", "region": "West"},
        {"order_id": "ORD009", "customer": "Grace", "product_id": "P002", "quantity": 1, "date": "2025-02-20", "region": "North"},
        {"order_id": "ORD010", "customer": "Alice", "product_id": "P008", "quantity": 1, "date": "2025-03-01", "region": "North"},
        {"order_id": "ORD011", "customer": "Hank", "product_id": "P009", "quantity": 5, "date": "2025-03-05", "region": "East"},
        {"order_id": "ORD012", "customer": "Charlie", "product_id": "P010", "quantity": 10, "date": "2025-03-10", "region": "North"},
        {"order_id": "ORD013", "customer": "Diana", "product_id": "P005", "quantity": 1, "date": "2025-03-15", "region": "West"},
        {"order_id": "ORD014", "customer": "Eve", "product_id": "P003", "quantity": 2, "date": "2025-03-20", "region": "East"},
        {"order_id": "ORD015", "customer": "Frank", "product_id": "P006", "quantity": 1, "date": "2025-04-01", "region": "West"},
        {"order_id": "ORD016", "customer": "Grace", "product_id": "P001", "quantity": 3, "date": "2025-04-05", "region": "North"},
        {"order_id": "ORD017", "customer": "Hank", "product_id": "P004", "quantity": 2, "date": "2025-04-10", "region": "East"},
        {"order_id": "ORD018", "customer": "Alice", "product_id": "P002", "quantity": 1, "date": "2025-04-15", "region": "North"},
        {"order_id": "ORD019", "customer": "Bob", "product_id": "P007", "quantity": 2, "date": "2025-04-20", "region": "South"},
        {"order_id": "ORD020", "customer": "Charlie", "product_id": "P008", "quantity": 1, "date": "2025-05-01", "region": "North"},
    ]
    orders.insert_many(order_records)

    return orders, products


class TestConnection:
    def test_mongomock_client_creates(self):
        client = mongomock.MongoClient()
        assert client is not None

    def test_database_created(self):
        client = mongomock.MongoClient()
        db = client["ecommerce"]
        assert db is not None

    def test_both_collections_exist(self):
        client = mongomock.MongoClient()
        db = client["ecommerce"]
        assert db["orders"] is not None
        assert db["products"] is not None


class TestSeedData:
    def test_product_count(self, populated_db):
        _, products = populated_db
        assert products.count_documents({}) == 10

    def test_order_count(self, populated_db):
        orders, _ = populated_db
        assert orders.count_documents({}) == 20

    def test_product_has_required_fields(self, populated_db):
        _, products = populated_db
        p = products.find_one()
        for field in ["product_id", "name", "category", "price"]:
            assert field in p, f"Missing field: {field}"

    def test_order_has_required_fields(self, populated_db):
        orders, _ = populated_db
        o = orders.find_one()
        for field in ["order_id", "customer", "product_id", "quantity", "date", "region"]:
            assert field in o, f"Missing field: {field}"


class TestLookupPipeline:
    def test_lookup_returns_joined_data(self, populated_db):
        orders, _ = populated_db
        pipeline = [
            {"$lookup": {"from": "products", "localField": "product_id", "foreignField": "product_id", "as": "product"}},
            {"$limit": 1}
        ]
        result = list(orders.aggregate(pipeline))
        assert len(result) == 1
        assert "product" in result[0]
        assert len(result[0]["product"]) == 1

    def test_lookup_unwind_preserves_order_count(self, populated_db):
        orders, _ = populated_db
        pipeline = [
            {"$lookup": {"from": "products", "localField": "product_id", "foreignField": "product_id", "as": "product"}},
            {"$unwind": "$product"},
        ]
        result = list(orders.aggregate(pipeline))
        assert len(result) == 20


class TestRevenueByProduct:
    def test_revenue_pipeline_returns_results(self, populated_db):
        orders, _ = populated_db
        pipeline = [
            {"$lookup": {"from": "products", "localField": "product_id", "foreignField": "product_id", "as": "product"}},
            {"$unwind": "$product"},
            {"$addFields": {"revenue": {"$multiply": ["$quantity", "$product.price"]}}},
            {"$group": {"_id": "$product.name", "total_revenue": {"$sum": "$revenue"}, "total_sold": {"$sum": "$quantity"}}},
            {"$sort": {"total_revenue": -1}}
        ]
        results = list(orders.aggregate(pipeline))
        assert len(results) > 0
        assert results[0]["total_revenue"] > 0

    def test_revenue_sorted_descending(self, populated_db):
        orders, _ = populated_db
        pipeline = [
            {"$lookup": {"from": "products", "localField": "product_id", "foreignField": "product_id", "as": "product"}},
            {"$unwind": "$product"},
            {"$addFields": {"revenue": {"$multiply": ["$quantity", "$product.price"]}}},
            {"$group": {"_id": "$product.name", "total_revenue": {"$sum": "$revenue"}}},
            {"$sort": {"total_revenue": -1}}
        ]
        results = list(orders.aggregate(pipeline))
        revenues = [r["total_revenue"] for r in results]
        assert revenues == sorted(revenues, reverse=True)


class TestMonthlyRevenue:
    def test_monthly_groups(self, populated_db):
        orders, _ = populated_db
        pipeline = [
            {"$lookup": {"from": "products", "localField": "product_id", "foreignField": "product_id", "as": "product"}},
            {"$unwind": "$product"},
            {"$addFields": {"revenue": {"$multiply": ["$quantity", "$product.price"]}, "month": {"$substr": ["$date", 0, 7]}}},
            {"$group": {"_id": "$month", "monthly_revenue": {"$sum": "$revenue"}, "order_count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        results = list(orders.aggregate(pipeline))
        months = [r["_id"] for r in results]
        assert "2025-01" in months
        assert "2025-03" in months

    def test_monthly_total_revenue(self, populated_db):
        orders, _ = populated_db
        pipeline = [
            {"$lookup": {"from": "products", "localField": "product_id", "foreignField": "product_id", "as": "product"}},
            {"$unwind": "$product"},
            {"$addFields": {"revenue": {"$multiply": ["$quantity", "$product.price"]}}},
            {"$group": {"_id": None, "total": {"$sum": "$revenue"}}}
        ]
        results = list(orders.aggregate(pipeline))
        assert len(results) == 1
        assert results[0]["total"] > 0


class TestTopCustomers:
    def test_top_customer_is_alice(self, populated_db):
        orders, _ = populated_db
        pipeline = [
            {"$lookup": {"from": "products", "localField": "product_id", "foreignField": "product_id", "as": "product"}},
            {"$unwind": "$product"},
            {"$addFields": {"revenue": {"$multiply": ["$quantity", "$product.price"]}}},
            {"$group": {"_id": "$customer", "total_spend": {"$sum": "$revenue"}}},
            {"$sort": {"total_spend": -1}},
            {"$limit": 1}
        ]
        results = list(orders.aggregate(pipeline))
        assert results[0]["_id"] == "Charlie"

    def test_top5_limit(self, populated_db):
        orders, _ = populated_db
        pipeline = [
            {"$lookup": {"from": "products", "localField": "product_id", "foreignField": "product_id", "as": "product"}},
            {"$unwind": "$product"},
            {"$addFields": {"revenue": {"$multiply": ["$quantity", "$product.price"]}}},
            {"$group": {"_id": "$customer", "total_spend": {"$sum": "$revenue"}}},
            {"$sort": {"total_spend": -1}},
            {"$limit": 5}
        ]
        results = list(orders.aggregate(pipeline))
        assert len(results) == 5


class TestRevenueByRegion:
    def test_all_four_regions(self, populated_db):
        orders, _ = populated_db
        pipeline = [
            {"$lookup": {"from": "products", "localField": "product_id", "foreignField": "product_id", "as": "product"}},
            {"$unwind": "$product"},
            {"$addFields": {"revenue": {"$multiply": ["$quantity", "$product.price"]}}},
            {"$group": {"_id": "$region", "total_revenue": {"$sum": "$revenue"}}},
            {"$sort": {"total_revenue": -1}}
        ]
        results = list(orders.aggregate(pipeline))
        regions = {r["_id"] for r in results}
        assert regions == {"North", "South", "East", "West"}

    def test_north_highest_revenue(self, populated_db):
        orders, _ = populated_db
        pipeline = [
            {"$lookup": {"from": "products", "localField": "product_id", "foreignField": "product_id", "as": "product"}},
            {"$unwind": "$product"},
            {"$addFields": {"revenue": {"$multiply": ["$quantity", "$product.price"]}}},
            {"$group": {"_id": "$region", "total_revenue": {"$sum": "$revenue"}}},
            {"$sort": {"total_revenue": -1}}
        ]
        results = list(orders.aggregate(pipeline))
        assert results[0]["_id"] == "North"


class TestCategoryBreakdown:
    def test_electronics_category(self, populated_db):
        orders, _ = populated_db
        pipeline = [
            {"$lookup": {"from": "products", "localField": "product_id", "foreignField": "product_id", "as": "product"}},
            {"$unwind": "$product"},
            {"$match": {"product.category": "Electronics"}},
            {"$group": {"_id": "$product.name", "units_sold": {"$sum": "$quantity"}}},
        ]
        results = list(orders.aggregate(pipeline))
        assert len(results) > 0
        product_names = {r["_id"] for r in results}
        assert "Wireless Mouse" in product_names

    def test_match_filters_correctly(self, populated_db):
        orders, _ = populated_db
        pipeline = [
            {"$lookup": {"from": "products", "localField": "product_id", "foreignField": "product_id", "as": "product"}},
            {"$unwind": "$product"},
            {"$match": {"product.category": "Stationery"}},
            {"$count": "total"}
        ]
        results = list(orders.aggregate(pipeline))
        assert results[0]["total"] == 2


class TestIndexes:
    def test_create_product_id_index(self, populated_db):
        orders, _ = populated_db
        orders.create_index("product_id")
        assert "product_id_1" in orders.index_information()

    def test_create_unique_product_index(self, populated_db):
        _, products = populated_db
        products.create_index("product_id", unique=True)
        info = products.index_information()
        assert any("product_id" in k for k in info.keys())

    def test_create_compound_index(self, populated_db):
        orders, _ = populated_db
        orders.create_index([("region", 1), ("date", 1)])
        info = orders.index_information()
        has_compound = any("region" in k and "date" in k for k in info.keys())
        assert has_compound

    def test_index_information_returns_dict(self, populated_db):
        orders, _ = populated_db
        info = orders.index_information()
        assert isinstance(info, dict)
        assert "_id_" in info


class TestExplain:
    def test_find_with_filter_returns_results(self, populated_db):
        orders, _ = populated_db
        results = list(orders.find({"region": "North"}))
        assert len(results) > 0

    def test_find_with_compound_filter(self, populated_db):
        orders, _ = populated_db
        results = list(orders.find({"region": "North", "date": {"$gte": "2025-02-01"}}))
        for r in results:
            assert r["region"] == "North"
            assert r["date"] >= "2025-02-01"


class TestSummaryReport:
    def test_total_revenue_positive(self, populated_db):
        orders, _ = populated_db
        pipeline = [
            {"$lookup": {"from": "products", "localField": "product_id", "foreignField": "product_id", "as": "product"}},
            {"$unwind": "$product"},
            {"$addFields": {"revenue": {"$multiply": ["$quantity", "$product.price"]}}},
            {"$group": {"_id": None, "total": {"$sum": "$revenue"}}}
        ]
        results = list(orders.aggregate(pipeline))
        assert results[0]["total"] > 0

    def test_order_count_matches(self, populated_db):
        orders, _ = populated_db
        assert orders.count_documents({}) == 20
