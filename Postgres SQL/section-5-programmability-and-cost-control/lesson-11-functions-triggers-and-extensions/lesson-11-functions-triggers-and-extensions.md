# Functions, Triggers and Extensions

---

# Problem Statement / Use Case Overview

_To be written._

| | |
|---|---|
| **Section** | 5 - Programmability and Cost Control |
| **Level** | Advanced |
| **Estimated time** | ~50 min |
| **Requires** | Labs 1-5 |
| **Covers** | SQL and PL/pgSQL functions; procedures; triggers and event triggers; LISTEN / NOTIFY; extensions (pgcrypto, pg_cron, PostGIS overview) |

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

Requires: Labs 1-5. Read the Introduction (lessons 0.1 to 0.3) first.

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
