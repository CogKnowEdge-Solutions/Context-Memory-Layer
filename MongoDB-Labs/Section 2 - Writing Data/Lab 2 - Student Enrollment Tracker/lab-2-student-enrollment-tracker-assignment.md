# Assignment - How to Write, Update & Delete Data

Practise what you learned in **How to Write, Update & Delete Data**. The lesson covered the four basic operations on data: create, read, update and delete. In these tasks you change records in the `students` collection and check each change.

**How to work:** Use the connection and the `students` collection from the lesson. Each student has `name`, `student_id`, `course`, `grade` and `status`. After every change, print something that proves it worked. Answers are in a separate file; try each task first.

---

**1.** Insert one new student with `insert_one`, using the id `"STU026"`. Print how many students exist before and after.

**2.** Insert three more students at once with `insert_many`. Print how many students exist now.

**3.** Change the `status` of the student with `student_id` `"STU012"` (Laura Palmer) to `"inactive"`, then read her record and print her status.

**4.** Add 5 points to Laura Palmer's grade with `$inc`. Read her record again and print her new grade.

**5.** Add the field `"email"` with the value `"unknown@university.edu"` to every student in the `"Physics"` course. Print how many documents were changed.

**6.** Run the update below **twice** and print `students.count_documents({"student_id": "STU999"})` after each run. Then say in a comment why the count is 1 both times.

```python
students.update_one({"student_id": "STU999"},
                    {"$set": {"name": "Test Student", "course": "English"}},
                    upsert=True)
```

**7.** Use `find_one_and_update` to add 3 points to the grade of student `"STU001"` and print the grade of the **updated** document. *Hint:* ask for the document after the change with `return_document=ReturnDocument.AFTER`.

**8.** Delete the student `"STU999"` with `delete_one` and print how many documents were deleted.

**9.** Delete every student whose status is `"inactive"` with `delete_many`. Print how many were deleted and how many students remain.
