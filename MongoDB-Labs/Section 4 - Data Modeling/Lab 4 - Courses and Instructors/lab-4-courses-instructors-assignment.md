# Assignment - How to Design Schemas & Search Data

Practise what you learned in **How to Design Schemas & Search Data**. The lesson compared embedding and referencing related data, joined two collections with `$lookup` and added a text index for keyword search. In these tasks you repeat those steps on your own.

**How to work:** Use the connection and the `courses` and `instructors` collections from the lesson. A course has `course_id`, `title`, `description`, a `schedule` (embedded) and an `instructor_id` (a reference). An instructor has `instructor_id` and `name`. Answers are in a separate file; try each task first.

---

**1.** Print one complete course document. Say in a comment which field is **embedded** and which field is a **reference**.

**2.** Find the course `"CS101"` and print where it meets (the `location` inside `schedule`).

**3.** Find out who teaches `"CS101"` using two separate queries: first read the course, then read the instructor with the course's `instructor_id`. Print the instructor's name.

**4.** Do the same job in one step: write a `$lookup` pipeline that returns every course's `title` and its instructor's `name`, and hide `_id`.

**5.** Run your pipeline from Task 4 without `$unwind` and print one result. Then add `$unwind` and print one result again. What is different?

**6.** Use a `$lookup` pipeline to list the `course_id` and `title` of every course taught by `"Dr. Maria Chen"`. *Hint:* `$match` after `$unwind`.

**7.** Count how many courses each instructor teaches. Print the `instructor_id` and the count.

**8.** Create a text index on the `description` field of `courses`. Search for courses containing the word `"data"` and print each `course_id` and `title`.

**9.** Insert a new course `"CS301"` titled `"Machine Learning"` with an embedded `schedule` and the `instructor_id` of an instructor already in the collection. Then use your `$lookup` pipeline to confirm the new course shows that instructor's name.
