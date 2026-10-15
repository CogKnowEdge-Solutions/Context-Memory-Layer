# Assignment - How to Make Queries Fast

Practise what you learned in **How to Make Queries Fast**. The lesson loaded 100,000 enrollment records, read `explain` reports and used compound indexes to make queries fast. In these tasks you measure a query, add an index, and measure it again.

**How to work:** Use the `enrollment_log` collection from the lesson (`log`). Each record has `student_id`, `course`, `grade`, `credits`, `semester`, `status` and `submitted_at`. For every measurement, use `cursor.explain()["executionStats"]` and look at `nReturned`, `totalKeysExamined` and `totalDocsExamined`. Answers are in a separate file; try each task first.

---

**1.** Count how many records `log` holds and print the number.

**2.** Run `log.find({"course": "Physics", "status": "active"})` with `explain` and print `nReturned`, `totalKeysExamined` and `totalDocsExamined`. Note them in a comment.

**3.** Create an index on `course` and then `status`. Run the same query again and print the same three numbers. What changed?

**4.** Take this query: `log.find({"semester": "2025-Fall", "status": "active"}).sort("grade", -1).limit(50)`. Create the compound index that suits it best (equality fields first, then the sort field).

**5.** Run the query from Task 4 with `explain` and print whether the word `SORT` appears in `str(explain["queryPlanner"]["winningPlan"])`. *Hint:* a good index means no separate sort step.

**6.** Create a second index in the **wrong** order, `grade` first and then `semester` and `status`. Run the Task 4 query using `.hint()` with that index and print `totalKeysExamined`. Compare it with the good index.

**7.** Write a covered query: `log.find({"course": "Physics", "credits": 4}, {"_id": 0, "course": 1, "credits": 1})`. Create the index it needs and print `totalDocsExamined`. *Hint:* a covered query reads zero documents.

**8.** Print the name of every index on `log`, and how often each was used. *Hint:* the `$indexStats` aggregation stage.

**9.** Drop the badly ordered index from Task 6 with `drop_index` and print the remaining index names.
