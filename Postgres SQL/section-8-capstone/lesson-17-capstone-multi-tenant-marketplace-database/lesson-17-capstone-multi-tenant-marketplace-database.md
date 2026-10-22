# Capstone: Multi-Tenant Marketplace Database

---

# Problem Statement / Use Case Overview

_To be written._

| | |
|---|---|
| **Section** | 8 - Capstone |
| **Level** | Capstone |
| **Estimated time** | ~120 min |
| **Requires** | Labs 1-16 |
| **Covers** | schema and constraints (Labs 1-3); seed data with COPY (7); revenue analytics with CTEs and windows (4-5); product attributes in JSONB (6); ranked, typo-tolerant product search (16); indexes, EXPLAIN and monthly partitioned orders (8-9); oversell-proof checkout and a SKIP LOCKED fulfilment queue (10); audit triggers (11); retention and cost review (12); per-seller row-level security and roles (13); backup, PITR and a replica (14); health checks (15) |

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

Requires: Labs 1-16. Read the Introduction (lessons 0.1 to 0.3) first.

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
