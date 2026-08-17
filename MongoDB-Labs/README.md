# MongoDB Labs

This is a hands-on lab series to learn MongoDB from scratch. You start with the basics — connecting to a database, inserting data, and running simple queries — and work your way up to building real applications with transactions, indexing, and production-grade security.

Each lab uses a small, self-contained project (a student database, a task tracker, a sales pipeline) so you learn by building something real, not by reading theory. Every lab has a Jupyter notebook with code you can run, a markdown guide that explains what's happening, and an assignment to test what you learned.

No prior MongoDB experience is needed. The first two labs cover the fundamentals — how to read and write data. Labs 3-4 move into intermediate territory with aggregation pipelines and schema design. Labs 5-6 cover advanced topics like transactions and cluster management. Lab 7 ties everything together into a working app.

All labs use `pymongo` (the Python driver for MongoDB) and `mongomock` (an in-memory mock so you don't need to install a MongoDB server). Just run the first cell in any notebook and you're good to go.

## Labs

| # | Lab | Level | What You Learn |
|---|-----|-------|----------------|
| 1 | MongoDB Basics: How to Query Data | Beginner | Connect, insert, filter, sort, aggregate |
| 2 | MongoDB Basics: How to Write, Update & Delete Data | Beginner | Full CRUD lifecycle, upserts, re-query after mutations |
| 3 | Sales Analytics Pipeline | Intermediate | Aggregation pipelines, indexing, `.explain()` |
| 4 | Multi-Tenant Blog Backend | Intermediate | Schema design, embedding vs referencing, `$lookup`, text search |
| 5 | Reliable Order Processing System | Advanced | Transactions, change streams, backup/restore |
| 6 | Scaling and Securing a Cluster | Advanced | Replica sets, sharding, RBAC, TLS |
| 7 | End-to-End Mini App | Capstone | Full-stack: schema + CRUD + analytics + indexing |

## Getting Started

Start with Lab 1. Each notebook has a `!pip install` cell at the top — run that first, then follow the steps. Labs 1-2 are beginner-friendly and need no prior MongoDB knowledge. From Lab 3 onwards, you should be comfortable with the basics covered in the first two labs.
