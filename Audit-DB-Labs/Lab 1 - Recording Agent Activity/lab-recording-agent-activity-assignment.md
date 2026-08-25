# Lab 1 — Recording Agent Activity: Knowledge Check

Complete these exercises after finishing the lab. The answer key is at the bottom — try each one before looking.

---

## Exercises

### 1. Why append-only? (concept)

Lab 1's core rule is that event rows are added, never silently edited or deleted. Why is this rule critical for an *audit* database specifically, as opposed to a normal application database? What problem would arise if an agent harness could freely UPDATE event rows after writing them?

### 2. Why does ORDER BY need a tiebreaker? (concept)

In Step 5, events committed inside one transaction all share the same `created_at` timestamp (`now()` returns the transaction's start time). Why would `ORDER BY created_at` alone return events in a non-deterministic order? What does the `, event_id` tiebreaker guarantee, and why is this important for an auditor replaying events?

### 3. What does the lifecycle update actually do? (concept)

Step 4 issues an `UPDATE` on the `run` row — the only `UPDATE` against `run` in the entire lab. What three fields does it set, and why is each one unavailable at row creation time? Why is this considered a lifecycle write rather than a rewrite of history?

### 4. Why log the redaction instead of just replacing the secret? (concept)

In Step 7, the redaction is a two-step operation: replace the secret in the payload, *then* insert a new `redaction` event recording what was changed. Why is the second step necessary? What would a compliance reviewer lose if the replacement happened without a log row?

### 5. Write a query that reads back a run's events (short code)

Write a `cursor.execute` call that returns every event for a given `run_id` (use the variable `current_run_id` already holding a valid id), ordered by `created_at` then `event_id`. Print each row's `event_id`, `event_type`, and `payload`.

```python
cursor.execute("""
    -- your query here
""", (current_run_id,))
for row in cursor.fetchall():
    print(row)
```

### 6. Write a correction event (short code)

You have a run with id in `current_run_id`. An event with `event_id = 99` logged the wrong value. Write the `cursor.execute` calls needed to:
1. Insert a `correction` event naming event 99 and stating the true value was 42.
2. Commit the transaction.
3. Query and print both the original event and the correction to prove both rows exist.

### 7. Applied: a silent edit that breaks the audit trail (applied)

A developer writes this code to "fix" a mislogged event:

```python
cursor.execute(
    "UPDATE event SET payload = 'Corrected: 42 orders shipped.' WHERE event_id = %s",
    (wrong_event_id,),
)
connection.commit()
```

This silently overwrites the original payload. What two things are wrong with this approach from an audit-log perspective? How would Lab 1's append-only pattern fix both problems?

---

## Answer Key

### 1. Why append-only?

An audit database exists to answer "what happened, when, and in what order?" If rows could be silently edited, there would be no way to prove the log wasn't tampered with after the fact — the log loses its evidentiary value. A normal application database optimizes for "what is true right now?" (current balance, current status), so edits are expected and necessary. An audit log records the film reel of what happened; silent edits corrupt the reel. Lab 1's only exceptions — the lifecycle update on `run` and the scoped `REPLACE` for redaction — are both controlled and self-logged, so a reviewer can still see that a change was made and why.

### 2. Why does ORDER BY need a tiebreaker?

`now()` returns the transaction's start time, not the time each individual `INSERT` executes. All events committed in one transaction share the same `created_at` value. When rows tie on the sort column, the database is free to return them in any order — it might be insertion order, physical order on disk, or something else. Adding `, event_id` as a tiebreaker provides a second, unique sort key that pins the order to a deterministic value. For an auditor replaying events, this matters because the narrative must be reproducible: anyone re-running the query must see the same sequence.

### 3. What does the lifecycle update actually do?

It sets `ended_at`, `status`, and `total_cost` on the `run` row. At creation time, none of these facts are known yet: the run hasn't ended (so `ended_at` is meaningless), its final status isn't decided, and the total cost hasn't been tallied. This update records facts that came into existence *after* the run started — it's a lifecycle write capturing reality, not a rewrite of a previously-recorded event. This is the only UPDATE allowed on the `run` row; event rows themselves are never updated.

### 4. Why log the redaction instead of just replacing the secret?

Without the log row, there is no record that anything was changed. A compliance reviewer looking at the log would see a payload containing `[REDACTED]` but would have no way to know *when* the redaction happened, *which field* was affected, or *who* performed it. The redaction log row makes the cleanup itself part of the audit trail: it records the event id, the field name, and the timestamp, so the reviewer can see both that a secret existed and that it was deliberately blanked out at a specific time. This is the same "nothing is silently modified" principle that governs corrections.

### 5. Write a query that reads back a run's events

```python
cursor.execute("""
    SELECT event_id, event_type, payload
    FROM event
    WHERE run_id = %s
    ORDER BY created_at, event_id
""", (current_run_id,))
for row in cursor.fetchall():
    print(row)
```

The `WHERE run_id = %s` filters to one run's events, `ORDER BY created_at` replays them in time order, and `, event_id` ensures deterministic ordering when timestamps tie.

### 6. Write a correction event

```python
cursor.execute(
    "INSERT INTO event (run_id, event_type, payload) VALUES (%s, %s, %s) RETURNING event_id",
    (current_run_id, "correction",
     "Correction: event 99 reported the wrong value; the true value was 42."),
)
connection.commit()

cursor.execute(
    "SELECT event_id, event_type, payload FROM event WHERE event_id IN (99, %s)",
    (cursor.fetchone()[0],),
)
for row in cursor.fetchall():
    print(row)
```

The correction event names the event it fixes (event 99) in its payload text. Both the original row and the correction row survive — the original is not deleted or updated. This is the append-only correction pattern from Lab 1's Step 6.

### 7. Applied: a silent edit that breaks the audit trail

Two problems:

1. **The original payload is lost.** The `UPDATE` overwrites the previous value in place. There is now no row showing what was originally logged — the auditor cannot see the mistake, only the "corrected" version. This destroys the evidentiary chain.

2. **No record that a change was made.** There is no `correction` event, no redaction log, nothing. A reviewer looking at the log has no way to know the payload was ever different. The log appears pristine, which is precisely the problem — it hides the fact that human intervention occurred.

Lab 1's append-only pattern fixes both: insert a *new* `correction` event naming what it fixes (the original stays visible), or use `REPLACE` on the payload only for redaction and log the act as a separate event. In every case, the history shows *what happened, including the corrections*.
