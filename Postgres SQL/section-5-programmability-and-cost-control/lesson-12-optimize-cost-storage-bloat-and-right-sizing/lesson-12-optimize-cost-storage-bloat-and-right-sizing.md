# Optimize Cost: Storage, Bloat and Right-Sizing

---

# Problem Statement / Use Case Overview

_To be written._

| | |
|---|---|
| **Section** | 5 - Programmability and Cost Control |
| **Level** | Intermediate to Advanced |
| **Estimated time** | ~60 min |
| **Requires** | Labs 8-10 |
| **Covers** | table and index size analysis; bloat, VACUUM and autovacuum tuning; unused and duplicate indexes (pg_stat_user_indexes); efficient data types and column order; retention with partition drop and archiving; TOAST and compression; right-sizing CPU, memory and connections from metrics; PgBouncer pooling; managed-cloud cost levers (instance class, storage type and IOPS, read replicas vs standbys, reserved capacity, serverless trade-offs) |

---

# Input Data

_To be written._

---

# Processing

_To be written._

---

# Output

_To be written._

---

# Tech Stack

| Tool | Role |
|------|------|
| PostgreSQL 18 | The database every lesson runs against |
| psycopg 3 | Python driver the notebook uses to talk to PostgreSQL |
| python-dotenv | Loads the connection settings from the global `.env` |
| Jupyter | Runs the notebook |

---

# Underlying Concepts (Summarized)

_To be written._

---

# Pre-requisites

Requires: Labs 8-10. Read the Introduction (lessons 0.1 to 0.3) first.

---

# Environment / Dependencies Setup

All connection settings live in **one global `.env` file at the course root** (`PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`, `PGSSLMODE`). Every notebook loads it with `load_dotenv("../../.env")`, so Jupyter must be started from inside this lesson folder.

One command installs the Python packages:

```
pip install -U "psycopg[binary]" python-dotenv
```

Installing and starting PostgreSQL itself is covered in lesson 0.3 (Setup Guide).

---

# Step-wise Instructions - Development

_To be written._

---

# What We Learnt

_To be written._
