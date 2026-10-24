# Secure Postgres with Roles, RLS and TLS — Assignment

Run code exercises in a scratch Python script or SQL session connected to your test database.

## Exercises

### Exercise 1 — Roles and grants
Create roles `reporting_ro` (no login) and `reporting_user` (can login). Grant `reporting_ro` to `reporting_user`. Grant `USAGE` on schema `public` and `SELECT` on table `sales` to `reporting_ro`. Write the SQL statements.

### Exercise 2 — RLS
A table `orders(tenant_id int, order_id int, amount numeric)` needs each tenant to see only their own rows. Enable RLS and create a policy for role `tenant_user` so `USAGE`/filter uses `tenant_id = current_setting('app.tenant_id')::int`. Write the SQL.

### Exercise 3 — Authentication
What is `pg_hba.conf` used for? Name two authentication methods and say which one is preferred in modern PostgreSQL.

### Exercise 4 — TLS
Why encrypt client-server connections with TLS? How can you check if SSL is enabled on the server?

### Exercise 5 — Safe passwords and hashing
Using `pgcrypto`, write SQL to (a) create extension if needed, (b) hash a password with blowfish salt, (c) verify a password against a stored hash. Name the functions.

### Exercise 6 — Prepared statements
Why use prepared statements/parameterized queries? Write Python (psycopg) example showing parameter passing (no string formatting of values).

## Answer Key

### Exercise 1
```sql
CREATE ROLE reporting_ro;
CREATE ROLE reporting_user LOGIN PASSWORD 'temp';
GRANT reporting_ro TO reporting_user;
GRANT USAGE ON SCHEMA public TO reporting_ro;
GRANT SELECT ON sales TO reporting_ro;
```
**Why:** use role groups, grant least privilege.

### Exercise 2
```sql
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON orders
  FOR ALL TO tenant_user
  USING (tenant_id = current_setting('app.tenant_id')::int)
  WITH CHECK (tenant_id = current_setting('app.tenant_id')::int);
```
**Why:** WITH CHECK prevents inserting/updating rows for other tenants.

### Exercise 3
`pg_hba.conf` controls host-based authentication (which hosts/roles can connect and how). Common methods: `trust` (no auth), `password`/`md5`, `scram-sha-256` (preferred), `cert`. Prefer `scram-sha-256` (modern, secure); MD5 is deprecated.

### Exercise 4
Encrypts traffic to prevent eavesdropping/man-in-the-middle. Check with `SHOW ssl;` or query `pg_settings`.

### Exercise 5
```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
SELECT crypt('mypw', gen_salt('bf')) AS hash;
SELECT (crypt('mypw', hash) = hash) AS ok FROM (SELECT crypt('mypw', gen_salt('bf')) AS hash) s;
```
Functions: `gen_salt('bf')`, `crypt()`. Verify by re-hashing with stored hash.

### Exercise 6
Prevent SQL injection and allow plan reuse. 
```python
cur.execute("SELECT * FROM users WHERE email = %s", (email,))
```
Never do `f"SELECT * FROM users WHERE email = '{email}'"`.
