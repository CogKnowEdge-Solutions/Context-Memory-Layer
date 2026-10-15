# Assignment - How to Search by Keywords and by Meaning

Practise what you learned in **How to Search by Keywords and by Meaning**. The lesson searched a course catalog by words with `$search` and by meaning with `$vectorSearch`, then merged both rankings. In these tasks you run those searches with the functions you built in the lesson and look at the results.

**How to work:** Use the `catalog` collection and the helper functions from the lesson: `text_pipeline`, `vector_pipeline`, `embed_text`, `show`, `rrf_fuse` and `hybrid_search`. Both search indexes must be ready. Answers are in a separate file; try each task first.

---

**1.** Count the courses in `catalog` and print one course without its `embedding` field.

**2.** Search for the word `"databases"` with `text_pipeline` and show the results.

**3.** Search for the misspelled word `"databses"` twice: once with `fuzzy=False` and once with `fuzzy=True`. Which one finds courses, and why?

**4.** Search for `"data"` but keep only courses whose `level` is `"advanced"` by passing the `level` argument.

**5.** Turn the sentence `"make my chatbot remember what customers said"` into numbers with `embed_text` and print how many numbers it has.

**6.** Run a `$vectorSearch` for that sentence with `vector_pipeline` and show the top 5 courses. Do the results contain the words of your sentence?

**7.** Run the same vector search again but only for courses whose `level` is `"intermediate"`.

**8.** Run `hybrid_search` for a query that has a typo **and** describes an idea, for example `"databses for storing chat history"`, and show the results.

**9.** On paper, work out the Reciprocal Rank Fusion scores (k = 60) for the lists `["C", "A", "D"]` and `["A", "B", "C"]`. Then check your answer with `rrf_fuse([["C", "A", "D"], ["A", "B", "C"]])`.
