# Assignment - How to Query Data

Practise what you learned in **How to Query Data**. In the lesson you connected to Atlas, stored 25 student records in a `students` collection and answered questions with queries. In these tasks you will run similar queries yourself, one small step at a time.

**How to work:** Use the connection and the `students` collection from the lesson (`client`, `db`, `students`). Each student has `name`, `student_id`, `course`, `grade`, `enrollment_date` and `status`. Do each task in your own notebook cell, run it, and read what it prints. Answers are in a separate file; try each task first.

---

**1.** Count how many students are stored in the collection and print the number.

**2.** Find every student in the `"Computer Science"` course and print each one's `name` and `grade`.

**3.** Find every student whose grade is below 60 and print their names.

**4.** Find the students whose grade is between 70 and 80, including both 70 and 80. Show only `name`, `course` and `grade`, and hide `_id`.

**5.** Find every student whose `status` is `"inactive"`, with the earliest `enrollment_date` first.

**6.** Find the three students with the highest grades. Print their names and grades, best first. *Hint:* combine a sort with a limit.

**7.** Count how many students are in each course. Print the course name and the count.

**8.** Work out the average grade of each course and print the courses with the highest average first.

**9.** Insert one new student of your own (with all six fields), then find that student again by `student_id` and print the record to confirm it was saved.
