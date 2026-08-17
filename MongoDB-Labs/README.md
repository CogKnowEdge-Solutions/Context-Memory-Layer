# MongoDB Labs

A 7-lab series to learn MongoDB from basics to production. Each lab builds on the previous one.

| # | Lab | Level | What You Learn |
|---|-----|-------|----------------|
| 1 | MongoDB Basics: How to Query Data | Beginner | Connect, insert, filter, sort, aggregate |
| 2 | MongoDB Basics: How to Write, Update & Delete Data | Beginner | Full CRUD lifecycle, upserts, re-query after mutations |
| 3 | Sales Analytics Pipeline | Intermediate | Aggregation pipelines, indexing, `.explain()` |
| 4 | Multi-Tenant Blog Backend | Intermediate | Schema design, embedding vs referencing, `$lookup`, text search |
| 5 | Reliable Order Processing System | Advanced | Transactions, change streams, backup/restore |
| 6 | Scaling and Securing a Cluster | Advanced | Replica sets, sharding, RBAC, TLS |
| 7 | End-to-End Mini App | Capstone | Full-stack: schema + CRUD + analytics + indexing |

**Prerequisites:** Basic Python knowledge. No MongoDB experience needed for Labs 1-2.

**Setup:** Each lab uses `pymongo==4.10.1` and `mongomock` (no MongoDB server required). Run the first code cell in any notebook to install dependencies.
