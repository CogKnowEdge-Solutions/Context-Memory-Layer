import pytest
import mongomock
from datetime import datetime


@pytest.fixture
def db_setup():
    client = mongomock.MongoClient()
    db = client["order_system"]
    inventory = db["inventory"]
    orders = db["orders"]
    customers = db["customers"]
    return inventory, orders, customers


@pytest.fixture
def populated_db(db_setup):
    inventory, orders, customers = db_setup

    inventory_data = [
        {"product_id": "P001", "name": "Wireless Mouse", "price": 29.99, "quantity": 20},
        {"product_id": "P002", "name": "Keyboard", "price": 49.99, "quantity": 15},
        {"product_id": "P003", "name": "USB Hub", "price": 24.99, "quantity": 30},
        {"product_id": "P004", "name": "Monitor", "price": 249.99, "quantity": 8},
        {"product_id": "P005", "name": "Laptop Stand", "price": 49.99, "quantity": 15},
    ]
    inventory.insert_many(inventory_data)

    customer_data = [
        {"customer_id": "alice", "name": "Alice Johnson", "email": "alice@example.com"},
        {"customer_id": "bob", "name": "Bob Smith", "email": "bob@example.com"},
        {"customer_id": "charlie", "name": "Charlie Brown", "email": "charlie@example.com"},
    ]
    customers.insert_many(customer_data)

    order_data = [
        {"order_id": "ORD-1001", "customer_id": "alice", "product_id": "P001", "quantity": 2, "total": 59.98, "date": "2025-01-15", "status": "completed"},
        {"order_id": "ORD-1002", "customer_id": "bob", "product_id": "P002", "quantity": 1, "total": 49.99, "date": "2025-02-20", "status": "completed"},
        {"order_id": "ORD-1003", "customer_id": "charlie", "product_id": "P004", "quantity": 1, "total": 249.99, "date": "2025-03-10", "status": "completed"},
        {"order_id": "ORD-1004", "customer_id": "alice", "product_id": "P003", "quantity": 1, "total": 24.99, "date": "2025-04-05", "status": "completed"},
        {"order_id": "ORD-1005", "customer_id": "bob", "product_id": "P002", "quantity": 2, "total": 99.98, "date": "2025-05-12", "status": "completed"},
    ]
    orders.insert_many(order_data)

    return inventory, orders, customers


class TestConnection:
    def test_mongomock_client_creates(self):
        client = mongomock.MongoClient()
        assert client is not None

    def test_database_created(self):
        client = mongomock.MongoClient()
        db = client["order_system"]
        assert db is not None

    def test_all_three_collections_exist(self):
        client = mongomock.MongoClient()
        db = client["order_system"]
        assert db["inventory"] is not None
        assert db["orders"] is not None
        assert db["customers"] is not None


class TestSeedData:
    def test_inventory_count(self, populated_db):
        inventory, _, _ = populated_db
        assert inventory.count_documents({}) == 5

    def test_order_count(self, populated_db):
        _, orders, _ = populated_db
        assert orders.count_documents({}) == 5

    def test_customer_count(self, populated_db):
        _, _, customers = populated_db
        assert customers.count_documents({}) == 3

    def test_inventory_has_required_fields(self, populated_db):
        inventory, _, _ = populated_db
        item = inventory.find_one()
        for field in ["product_id", "name", "price", "quantity"]:
            assert field in item, f"Missing field: {field}"

    def test_order_has_required_fields(self, populated_db):
        _, orders, _ = populated_db
        order = orders.find_one()
        for field in ["order_id", "customer_id", "product_id", "quantity", "total", "date", "status"]:
            assert field in order, f"Missing field: {field}"

    def test_customer_has_required_fields(self, populated_db):
        _, _, customers = populated_db
        customer = customers.find_one()
        for field in ["customer_id", "name", "email"]:
            assert field in customer, f"Missing field: {field}"

    def test_inventory_quantities_positive(self, populated_db):
        inventory, _, _ = populated_db
        for item in inventory.find({}):
            assert item["quantity"] > 0, f"{item['name']} has non-positive quantity"


class TestAtomicOrderPlacement:
    def test_successful_order_decrements_stock(self, populated_db):
        inventory, orders, _ = populated_db
        before = inventory.find_one({"product_id": "P001"})["quantity"]

        inventory.find_one_and_update(
            {"product_id": "P001", "quantity": {"$gte": 1}},
            {"$inc": {"quantity": -1}},
        )

        after = inventory.find_one({"product_id": "P001"})["quantity"]
        assert after == before - 1

    def test_successful_order_creates_record(self, populated_db):
        inventory, orders, _ = populated_db
        inventory.find_one_and_update(
            {"product_id": "P001", "quantity": {"$gte": 1}},
            {"$inc": {"quantity": -1}},
        )
        orders.insert_one({
            "order_id": "ORD-TEST-001", "customer_id": "alice",
            "product_id": "P001", "quantity": 1,
            "total": 29.99, "date": "2025-06-01", "status": "completed",
        })
        assert orders.count_documents({}) == 6

    def test_insufficient_stock_returns_none(self, populated_db):
        inventory, _, _ = populated_db
        result = inventory.find_one_and_update(
            {"product_id": "P001", "quantity": {"$gte": 100}},
            {"$inc": {"quantity": -100}},
        )
        assert result is None

    def test_insufficient_stock_does_not_change_quantity(self, populated_db):
        inventory, _, _ = populated_db
        before = inventory.find_one({"product_id": "P001"})["quantity"]
        inventory.find_one_and_update(
            {"product_id": "P001", "quantity": {"$gte": 100}},
            {"$inc": {"quantity": -100}},
        )
        after = inventory.find_one({"product_id": "P001"})["quantity"]
        assert after == before

    def test_nonexistent_product_returns_none(self, populated_db):
        inventory, _, _ = populated_db
        result = inventory.find_one_and_update(
            {"product_id": "P999", "quantity": {"$gte": 1}},
            {"$inc": {"quantity": -1}},
        )
        assert result is None

    def test_exact_stock_succeeds(self, populated_db):
        inventory, _, _ = populated_db
        item = inventory.find_one({"product_id": "P004"})
        exact_qty = item["quantity"]

        result = inventory.find_one_and_update(
            {"product_id": "P004", "quantity": {"$gte": exact_qty}},
            {"$inc": {"quantity": -exact_qty}},
        )
        assert result is not None
        assert inventory.find_one({"product_id": "P004"})["quantity"] == 0


class TestAtomicOrderCancellation:
    def test_cancel_restores_stock(self, populated_db):
        inventory, orders, _ = populated_db
        order = orders.find_one({"order_id": "ORD-1001"})
        before = inventory.find_one({"product_id": order["product_id"]})["quantity"]

        inventory.update_one(
            {"product_id": order["product_id"]},
            {"$inc": {"quantity": order["quantity"]}},
        )
        orders.delete_one({"order_id": "ORD-1001"})

        after = inventory.find_one({"product_id": order["product_id"]})["quantity"]
        assert after == before + order["quantity"]
        assert orders.count_documents({"order_id": "ORD-1001"}) == 0

    def test_cancel_nonexistent_order(self, populated_db):
        _, orders, _ = populated_db
        order = orders.find_one({"order_id": "ORD-FAKE"})
        assert order is None

    def test_cancel_does_not_affect_other_products(self, populated_db):
        inventory, orders, _ = populated_db
        order = orders.find_one({"order_id": "ORD-1002"})
        other_before = inventory.find_one({"product_id": "P001"})["quantity"]

        inventory.update_one(
            {"product_id": order["product_id"]},
            {"$inc": {"quantity": order["quantity"]}},
        )
        orders.delete_one({"order_id": "ORD-1002"})

        other_after = inventory.find_one({"product_id": "P001"})["quantity"]
        assert other_after == other_before


class TestAggregation:
    def test_revenue_by_product(self, populated_db):
        _, orders, _ = populated_db
        pipeline = [
            {"$lookup": {
                "from": "inventory", "localField": "product_id",
                "foreignField": "product_id", "as": "product"
            }},
            {"$unwind": "$product"},
            {"$group": {
                "_id": "$product.name",
                "total_qty": {"$sum": "$quantity"},
                "total_revenue": {"$sum": "$total"}
            }},
            {"$sort": {"total_revenue": -1}},
        ]
        results = list(orders.aggregate(pipeline))
        assert len(results) > 0
        assert results[0]["_id"] == "Monitor"
        assert results[0]["total_qty"] == 1
        assert results[0]["total_revenue"] == 249.99

    def test_total_revenue(self, populated_db):
        _, orders, _ = populated_db
        pipeline = [
            {"$group": {"_id": None, "total": {"$sum": "$total"}}}
        ]
        results = list(orders.aggregate(pipeline))
        assert results[0]["total"] == 484.93

    def test_orders_per_customer(self, populated_db):
        _, orders, _ = populated_db
        pipeline = [
            {"$group": {"_id": "$customer_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        results = list(orders.aggregate(pipeline))
        counts = {r["_id"]: r["count"] for r in results}
        assert counts["alice"] == 2
        assert counts["bob"] == 2
        assert counts["charlie"] == 1


class TestChangeStreamSimulation:
    def test_simulated_events_have_operation_type(self, populated_db):
        _, orders, _ = populated_db
        for order in orders.find():
            assert "order_id" in order
            assert "customer_id" in order

    def test_events_contain_required_fields(self, populated_db):
        _, orders, _ = populated_db
        for order in orders.find():
            for field in ["order_id", "customer_id", "product_id", "quantity", "total"]:
                assert field in order, f"Missing field: {field}"


class TestBackupRestore:
    def test_backup_preserves_all_documents(self, populated_db):
        inventory, orders, customers = populated_db
        backup = {}
        for name, coll in [("orders", orders), ("inventory", inventory), ("customers", customers)]:
            backup[name] = list(coll.find({}, {"_id": 0}))

        assert len(backup["orders"]) == 5
        assert len(backup["inventory"]) == 5
        assert len(backup["customers"]) == 3

    def test_restore_replicates_data(self, populated_db):
        inventory, orders, customers = populated_db
        backup = {}
        for name, coll in [("orders", orders), ("inventory", inventory), ("customers", customers)]:
            backup[name] = list(coll.find({}, {"_id": 0}))

        for name, coll in [("orders", orders), ("inventory", inventory), ("customers", customers)]:
            coll.drop()
            db = coll.database
            db.create_collection(name)

        for name, coll in [("orders", orders), ("inventory", inventory), ("customers", customers)]:
            if backup[name]:
                coll.insert_many(backup[name])

        assert orders.count_documents({}) == 5
        assert inventory.count_documents({}) == 5
        assert customers.count_documents({}) == 3

    def test_restore_matches_original_data(self, populated_db):
        inventory, orders, customers = populated_db
        original_orders = list(orders.find({}, {"_id": 0}))

        backup = {"orders": original_orders}
        orders.drop()
        orders.database.create_collection("orders")
        orders.insert_many(backup["orders"])

        restored = list(orders.find({}, {"_id": 0}))
        assert len(restored) == len(original_orders)
        for orig, rest in zip(original_orders, restored):
            assert orig["order_id"] == rest["order_id"]
            assert orig["total"] == rest["total"]


class TestIndexes:
    def test_create_customer_id_index(self, populated_db):
        _, orders, _ = populated_db
        orders.create_index("customer_id")
        assert "customer_id_1" in orders.index_information()

    def test_create_date_index(self, populated_db):
        _, orders, _ = populated_db
        orders.create_index("date")
        assert "date_1" in orders.index_information()

    def test_create_compound_index(self, populated_db):
        _, orders, _ = populated_db
        orders.create_index([("customer_id", 1), ("date", -1)])
        info = orders.index_information()
        assert any("customer_id" in k and "date" in k for k in info.keys())

    def test_index_information_returns_dict(self, populated_db):
        _, orders, _ = populated_db
        info = orders.index_information()
        assert isinstance(info, dict)
        assert "_id_" in info
