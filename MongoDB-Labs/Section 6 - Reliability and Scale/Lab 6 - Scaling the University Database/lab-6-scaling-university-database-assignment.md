# Assignment - How to Inspect a Replica Set and Secure Access

Practise what you learned in **How to Inspect a Replica Set and Secure Access**. The lesson looked at the replica set behind a free Atlas cluster, read from a secondary, checked encryption and looked at who is allowed to do what. In these tasks you ask the cluster about itself.

**How to work:** Use the connection (`client`, `db`) from the lesson. Never print your connection string or password. Answers are in a separate file; try each task first.

---

**1.** Run the `hello` command on `db` and print the name of the replica set (`setName`).

**2.** Print the list of member servers (`hosts`) and how many there are.

**3.** Print whether the server you are connected to is the primary (`isWritablePrimary`).

**4.** Print which member is the primary (the `primary` field).

**5.** Get the `students` collection with the read preference `SECONDARY_PREFERRED`, read one document with it and print the student's name.

**6.** Run `find` on that collection with the same read preference and print `cursor.address` after reading one result. Which server answered?

**7.** Show that the connection is encrypted: print the **scheme** of your connection string (the part before `//`) without printing the rest, and add a comment saying why that scheme means TLS is on.

**8.** Run the `connectionStatus` command and print the roles of the user you are connected as.

**9.** In a comment, write which built-in role you would give a dashboard that must read all collections in `school_db` but never write, and why you would not give it `dbOwner`.

**10.** In a comment, explain what **sharding** would add to this database once it outgrows a single replica set, and why the free **M0** tier cannot shard.

---

**Answer Key:** sample answers for every task are in `lab-6-scaling-university-database-assignment-answers.md`.
