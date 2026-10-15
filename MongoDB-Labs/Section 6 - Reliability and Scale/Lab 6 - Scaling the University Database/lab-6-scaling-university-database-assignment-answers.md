# Assignment Answers - How to Inspect a Replica Set and Secure Access

Sample answers for the tasks. Your wording and code may differ; what matters is that the result is right.

---

## Task 1

```python
info = db.command("hello")
print(info["setName"])
```

## Task 2

```python
print(info["hosts"], len(info["hosts"]))
```
A free Atlas cluster shows three hosts.

## Task 3

```python
print(info["isWritablePrimary"])
```
`True` means you are talking to the primary.

## Task 4

```python
print(info["primary"])
```

## Task 5

```python
from pymongo import ReadPreference
rc = db.get_collection("students", read_preference=ReadPreference.SECONDARY_PREFERRED)
print(rc.find_one()["name"])
```

## Task 6

```python
cursor = rc.find({}).limit(1)
list(cursor)
print(cursor.address)
```
The address is usually one of the secondary servers, which is how the read is spread away from the primary.

## Task 7

```python
print(uri.split("//")[0])   # mongodb+srv:
# The mongodb+srv scheme always uses TLS, so the data is encrypted in transit.
```

## Task 8

```python
status = db.command("connectionStatus")
print(status["authInfo"]["authenticatedUserRoles"])
```

## Task 9

```python
# Give the dashboard the built-in `read` role on school_db.
# It can only read, which is least privilege. dbOwner also allows writing,
# changing indexes and managing users, so a mistake or a leaked password
# could damage the database.
```

## Task 10

```python
# Sharding splits one collection's data across several replica sets, each a
# "shard", using a shard key so storage and write throughput grow past what a
# single server can hold. It is a provisioning step (enabling sharding and
# picking the shard key), not a query you can run, so a free M0 cluster — which
# is a single 3-node replica set — cannot shard and can only be inspected.
```
