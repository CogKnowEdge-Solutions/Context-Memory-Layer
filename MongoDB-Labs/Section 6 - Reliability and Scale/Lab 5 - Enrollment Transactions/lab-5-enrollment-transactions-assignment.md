# Assignment - How to Guarantee Data Consistency

Practise what you learned in **How to Guarantee Data Consistency**. The lesson showed why enrolling a student needs two writes that must succeed or fail together, fixed it with a transaction and watched changes live with a change stream. In these tasks you run enrollments and see the transaction protect the data.

**How to work:** Use the connection, the `courses` and `enrollments` collections and the `enroll_student(session, cid, student_id, student_name)` function from the lesson. The courses are `CS101` (3 seats), `CS201` (5), `MATH101` (2) and `PHYS101` (4). Answers are in a separate file; try each task first.

---

**1.** Print the `course_id` and `seats_available` of every course.

**2.** Enroll student `"STU050"` named `"Eve Torres"` in `CS201` inside a transaction. Print the seats of `CS201` before and after.

**3.** Find the enrollment you just created and print it.

**4.** `MATH101` has only 2 seats. Enroll two students in it, one after the other, and print the seats left.

**5.** Now try to enroll a third student in `MATH101`. Catch the error and print its message.

**6.** After the failed attempt, print the seats of `MATH101` and the number of enrollments for `MATH101`. Do they match what you expected?

**7.** Write a version of enrollment **without** a transaction: one `update_one` that takes a seat and then one `insert_one` that saves the enrollment. In a comment, explain what could go wrong if the program stops between the two lines.

**8.** Open a change stream on `enrollments`, insert one new enrollment, and read the next event. Print the `operationType`.

**9.** From the same event, print the name of the enrolled student.
