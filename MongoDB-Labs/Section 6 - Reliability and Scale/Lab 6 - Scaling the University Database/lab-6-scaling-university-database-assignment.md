# MongoDB Advanced: How to Inspect a Replica Set and Secure Access

## Scaling the University Database — Assignment

Test your understanding of replica sets, read preferences, TLS, role-based access control, and sharding by answering the following questions and completing the short code tasks.

---

## Exercises

### Exercise 1 — Concept Question
What is a **replica set**? Why is every MongoDB Atlas cluster a replica set, including the free M0 tier? Name the two different kinds of member nodes and what each one does.

### Exercise 2 — Concept Question
A replica set's primary node fails. Describe what happens next. What is the **oplog**'s role in this process, and why is no data lost when the primary goes down?

### Exercise 3 — Code Task
Using `db.command("hello")`, write a pymongo snippet that prints the number of `hosts` in the replica set and the `setName`. Assume `db` is already connected.

### Exercise 4 — Concept Question
Why might a read served by a **secondary** return slightly stale data, while a read served by the primary does not? What is the trade-off you make when you use `ReadPreference.SECONDARY_PREFERRED`?

### Exercise 5 — Concept Question
How does **TLS** protect the university database's data? Give two concrete ways to confirm in code or configuration that an Atlas connection is encrypted.

### Exercise 6 — Concept Question
What is **RBAC**, and what does **least privilege** mean? Name two built-in MongoDB roles and describe what each allows.

### Exercise 7 — Concept Question (Applied)
A data-analysis dashboard needs to **read** (but never write) every collection in `school_db`. **Which single built-in role** would you grant its database user, and why would you NOT grant `dbOwner`? (Answer in prose; no code required.)

---

## Answer Key

### Exercise 1
A **replica set** is a group of MongoDB servers holding synchronized copies of the same data. One member is the **primary**, which accepts all client writes (keeping the data consistent across the set); the others are **secondaries**, which maintain synchronized copies and cannot accept client writes directly. Every Atlas cluster is a replica set — including the free M0 tier — because a database that exists on only one machine is a single point of failure. Replicating the data across several nodes is what lets an Atlas database survive the loss of a single machine.

### Exercise 2
When the primary node fails, the remaining secondaries detect that it is unreachable and hold an **election**, promoting one of them to become the new primary. No data is lost because every secondary already holds a full synchronized copy of the data. The **oplog** (operations log) is the mechanism that keeps the copies synchronized: the primary records every write it performs in the oplog, and each secondary tails the oplog and replays those operations onto its own copy. Because the secondaries were continuously replaying the oplog, they are already up to date with the writes the old primary accepted, so when it goes down the promoted secondary starts from that same state.

### Exercise 3
```python
hello = db.command("hello")
print("setName:", hello.get("setName"))
print("Number of hosts:", len(hello.get("hosts", [])))
```
`db.command("hello")` asks the node about itself and its cluster. `setName` names the replica set, and `hosts` is the list of all membership nodes, so `len(hello["hosts"])` gives the member count — 3 on the free tier.

### Exercise 4
The primary records each write in its oplog and then replicates it to the secondaries. Replication is fast but not instantaneous, so a secondary can lag behind the primary by a fraction of a second — it may not yet have replayed the very latest writes. A secondary read therefore reflects the data as of the last oplog entry that secondary has replayed, which can be momentarily **stale**; a primary read always reflects the latest committed write. The trade-off when you use `ReadPreference.SECONDARY_PREFERRED` is that you **scale reads** across all members (reducing load on the primary) in exchange for **eventual consistency** — occasional tiny staleness, which is fine for analytics, reporting, and dashboards but not for reads that must reflect the very latest write.

### Exercise 5
**TLS (Transport Layer Security)** encrypts every byte sent between the driver and the cluster, so even if an attacker intercepts the traffic they only see ciphertext, not the students' grades or passwords. Two ways to confirm an Atlas connection is encrypted: (1) the connection string uses the `mongodb+srv` scheme, which **requires** TLS by the MongoDB driver spec (a driver refuses to connect over `mongodb+srv` without encryption); and (2) the client is constructed with `tlsCAFile=certifi.where()`, which supplies a trusted CA bundle so the driver can verify the cluster's server certificate. On Atlas, TLS is enforced on every connection and cannot be turned off.

### Exercise 6
**RBAC (role-based access control)** means the database decides what each authenticated user may do based on **roles**, rather than letting every connection do anything. **Least privilege** means granting each user only the access they actually need and nothing more, so that if one set of credentials is compromised the damage is limited. Two built-in roles: **`read`** (read any collection in the database) and **`readWrite`** (read and write — insert, update, delete). Other built-in roles include `dbAdmin`, `userAdmin`, `readAnyDatabase` / `readWriteAnyDatabase`, and `dbOwner`.

### Exercise 7
Grant the dashboard user the **`read`** role on `school_db`. It needs to read every collection but never write to any of them, so `read` is exactly the least privilege that satisfies the requirement. You would NOT grant `dbOwner` because `dbOwner` grants **full control** of the database — read AND write plus administrative privileges — which is far more access than a read-only dashboard needs. Granting the least privilege keeps the blast radius small: if the dashboard's credentials leak, the worst an attacker can do is read, not modify or destroy data.
