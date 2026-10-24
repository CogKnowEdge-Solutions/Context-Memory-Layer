# Back Up, Recover and Replicate Postgres — Assignment

## Exercises

### Exercise 1 — WAL and checkpoints
What is WAL and why is it important for durability? What does a checkpoint do?

### Exercise 2 — Logical vs physical backup
Compare `pg_dump` (logical) and `pg_basebackup` (physical). Give one use case for each.

### Exercise 3 — PITR
Define RPO and RTO. What two things do you need for Point-In-Time Recovery?

### Exercise 4 — Streaming replication
What is a hot standby? What is a replication slot and why use it?

### Exercise 5 — Logical replication
How is logical replication different from streaming replication? Give one advantage.

### Exercise 6 — Restore test plan
Write a short checklist for testing a backup restore (at least 4 items).

## Answer Key

### Exercise 1
WAL (Write-Ahead Log) records changes before writing data files so PostgreSQL can recover on crash. A checkpoint flushes dirty pages to disk and marks a consistent recovery point.

### Exercise 2
`pg_dump` produces SQL/portable logical backup of schema/data (good for migrations, selective restore). `pg_basebackup` copies cluster files physically (needed for streaming replication and PITR).

### Exercise 3
RPO = max acceptable data loss (time). RTO = max acceptable downtime. For PITR need a base backup and continuous archived WAL files to replay.

### Exercise 4
Hot standby = standby server that can serve read queries while applying WAL. Replication slot prevents primary from removing WAL segments the standby still needs.

### Exercise 5
Streaming replicates all changes at block/WAL level; logical replicates changes at table level via publications/subscriptions. Advantage: replicate selected tables or to different major versions in some setups.

### Exercise 6
- Take backup and verify file integrity/size
- Restore to isolated test environment
- Check schema and row counts match expected
- Test application queries
- Verify point-in-time recovery to a known event
- Document restore time (RTO)
