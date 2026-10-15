# Assignment - How to Analyze Data at Scale

Practise what you learned in **How to Analyze Data at Scale**. The lesson summarised student data with aggregation pipelines and then used an index to make a query faster. In these tasks you build small pipelines and look at what an index changes.

**How to work:** Use the connection and the `students` collection from the lesson. Each student has `name`, `course`, `grade` and `status`. Run each pipeline with `students.aggregate(pipeline)` and print the rows. Answers are in a separate file; try each task first.

---

**1.** Count how many students are in each course. Show the course name and the count.

**2.** Work out the average grade of each course and list the highest average first.

**3.** Find the highest and the lowest grade in each course in one pipeline.

**4.** Keep only the courses whose average grade is above 75. *Hint:* the filter goes after the grouping step.

**5.** Work out the average grade of each course for **active students only**. *Hint:* here the filter goes before the grouping step.

**6.** Count how many students fall into each grade band: 0–59, 60–69, 70–79, 80–89 and 90–100. *Hint:* use the `$bucket` stage.

**7.** Count how many students there are for each `status`.

**8.** Run `students.find({"course": "Physics"}).explain()` and print `executionStats` fields `totalDocsExamined` and `nReturned`.

**9.** Create an index on `course`, run the same explain again, and print the same two numbers. Compare them with Task 8 in a comment.
