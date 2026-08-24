# Lab 1 Assignment — Recording Agent Activity

*Companion to `lab-recording-agent-activity.md` / `.ipynb`. Every exercise is answerable from the lab alone. Attempt all seven before scrolling to the answer key.*

---

## Exercises

### Exercise 1 — Two databases, two questions (concept)

Your app database holds a `students` table that currently says Alice's balance is $0. Your audit database holds rows recording every change ever made to that balance. In one or two sentences each: what question does each database answer, and why can't either one do the other's job?

### Exercise 2 — The append-only rule and its exceptions (concept)

State the append-only rule for event rows. Then list precisely:
1. The one further write a `run` header row is allowed after creation — which fields, and when?
2. The one exception that lets an *event* row's contents change — and the mandatory companion action that makes it lawful?

### Exercise 3 — Why log the redaction? (concept)

A teammate proposes: "Just run `UPDATE event SET payload = '[REDACTED]' WHERE ...` — done." Explain, using the lab's reasoning, what this one-liner gets wrong even though it removes the secret.

### Exercise 4 — Write a correction (short code)

An event was mislogged for run 42:

```
event_type: db_query
payload:    'Counted refunds issued: 3'
```

The true count was 30. Write the SQL INSERT (with `%s` placeholders) your harness should execute to fix this the audit-correct way, and state what must happen to the original row.

### Exercise 5 — Newest-first history (short code)

Write a single SELECT that returns all events for run 42, newest first, with a deterministic order when timestamps tie. Name the tiebreaker column and explain in one sentence why it's needed.

### Exercise 6 — Applied: an email where it shouldn't be (applied)

Your harness logged this event during run 77:

```
(901, 'user_profile', 'Profile fetched: email=jane@example.com, plan=pro')
```

A privacy reviewer requires the email removed from the log. Walk through the exact steps you would execute, in order, to comply with the lab's rules — and state what the log must show afterwards.

### Exercise 7 — Applied: crash mid-run (applied)

A harness inserts a `run` row, then three `event` rows, then loses its connection **before** reaching `commit()`. What does the audit database contain for that run, and why is that the *correct* outcome rather than a bug?

---

## Answer Key

**Exercise 1.** The app database answers *"what is true right now?"* (Alice's current balance), while the audit database answers *"what happened, when, and in what order?"* (every change that produced that balance). Each keeps only half the picture: the current photo without its history, or the film reel without a convenient snapshot of today's state — so neither can substitute for the other. *(See the lab's **Underlying Concepts** section — "audit vs normal".)*

**Exercise 2.** Event rows are **append-only**: once written, they are never silently updated or deleted. Exceptions: (1) the `run` header may receive exactly **one** lifecycle write when the run finishes — setting `ended_at`, `status`, and `total_cost` once — because at creation time those facts genuinely didn't exist yet, so nothing is misrepresented; (2) an event field may be changed only by a **scoped redaction**, and it is lawful only because a **new event row logging the redaction** (which event, which field, when) is inserted alongside it. *(Lab Steps 4, 7; README Section 3.)*

**Exercise 3.** Three things go wrong. It **overwrites more than the secret** if the payload held anything besides the sensitive value (the lab uses `REPLACE` to blank only the secret); it leaves **no trace of what happened** — the fact that data was hidden becomes itself hidden, destroying accountability; and it treats the event like normal mutable state instead of history. The rule requires the scoped replacement *plus* a new event recording which event, which field, and when. *(Lab Step 7; README Section 3.2.)*

**Exercise 4.**

```sql
INSERT INTO event (run_id, event_type, payload)
VALUES (%s, %s, %s);
-- params: (42, 'correction',
--          'Correction: event naming the mislogged row said refunds = 3; true count was 30.')
```

The correcting row should reference the original event (by id, as the lab does) so auditors can pair them, and the original mislogged row **must remain untouched** — corrections are appended, never applied to the old row. *(Lab Step 6.)*

**Exercise 5.**

```sql
SELECT event_id, event_type, payload, created_at
FROM event
WHERE run_id = %s
ORDER BY created_at DESC, event_id DESC;
```

Tiebreaker: `event_id` (descending here, to keep newest-first consistent). It's needed because events committed inside one transaction share an identical `created_at` — Postgres's `now()` returns the transaction's start time — so tied rows would otherwise come back in arbitrary, non-deterministic order. *(Lab Step 5.)*

**Exercise 6.** In order: (1) identify the offending event's `event_id`; (2) scoped-redact just the email value: `UPDATE event SET payload = REPLACE(payload, %s, %s) WHERE event_id = %s` with `('jane@example.com', '[REDACTED]', 901)`; (3) insert a new redaction-log event on run 77 whose payload names event 901, the field `'payload'`, and the UTC time of the redaction; (4) commit once so both writes land together. Afterwards the log shows event 901 still present with `email=[REDACTED]`, everything else in its payload intact, plus the new redaction row proving when and what was hidden. Deleting row 901 or silently blanking it without the log row would both violate the rules. *(Lab Step 7; README Section 3.2.)*

**Exercise 7.** The database contains **nothing** from that attempt — no run row and no events. All four inserts were inside one open transaction, and until `commit()` arrives no other observer (including a reconnecting client) can see any of them; losing the connection rolls the transaction back. This is correct because a half-recorded run — a header with missing events, or events with no header — would be an untrustworthy, unreconstructable history. All-or-nothing is exactly what transactions guarantee (README Section 4.1). The correct behavior on recovery is to start the run again from its first insert.
