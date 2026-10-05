# Move Map — topic folders → TOC sections

| TOC # | Old location | New location |
|---|---|---|
| 1 | `Classical-RAG/` | `section-1-classical-rag/lab-01-classical-rag/` |
| 2 | `HybridRAG/` | `section-2-retrieval-variations/lab-02-hybrid-rag/` |
| 3 | `MultiVector-RAG/lab1_langchain.*`, `lab-parent-child-multi-vector-rag-assignment.*` | `section-2-retrieval-variations/lab-03-multivector-parent-child/` |
| 4 | `MultiVector-RAG/lab2_colbert.*`, `lab-colbert-late-interaction-assignment.*` | `section-2-retrieval-variations/lab-04-colbert-late-interaction/` |
| 5 | `OCR-RAG/Lab 1/` | `section-3-structure-and-multimodal/lab-05-structured-ocr-rag/` |
| 6 | `OCR-RAG/Lab 2/` | `section-3-structure-and-multimodal/lab-06-ocr-scanned-pdf-rag/` |
| 7 | `LLM-Wiki/` | `section-3-structure-and-multimodal/lab-07-llm-wiki/` |
| 8 | `Graph-RAG/graph_rag_1.*`, `lab-generalized-graph-rag-assignment.*` | `section-4-knowledge-graphs/lab-08-graph-rag-networkx/` |
| 9 | `Graph-RAG/graph_rag_2.*`, `lab-graph-rag-neo4j-assignment.*` | `section-4-knowledge-graphs/lab-09-graph-rag-neo4j/` |
| 10 | `Graph-and-Vector/` | `section-4-knowledge-graphs/lab-10-graph-vector-hybrid/` |
| 11 | `Vectorless-RAG/lab1/` | `section-5-vectorless/lab-11-vectorless-reasoning-retrieval/` |
| 12 | `Vectorless-RAG/lab2/` | `section-5-vectorless/lab-12-vectorless-multihop/` |
| 13 | `Vectorless-RAG/lab3/` | `section-5-vectorless/lab-13-vectorless-table-retrieval/` |
| 14 | `Agentic-RAG/agentic_lab_1.*`, `lab-agentic-rag-self-correction-assignment.*` | `section-6-adaptive-and-agentic/lab-14-agentic-rag-self-correction/` |
| 15 | `Agentic-RAG/agentic_lab_2.*`, `lab-agentic-hybrid-rag-routing-assignment.*` | `section-6-adaptive-and-agentic/lab-15-agentic-hybrid-routing/` |
| 16 | `Capstone-Agentic-Research-Assistant/` | `section-7-capstone/lab-16-agentic-research-assistant/` |

Notes: the shared `.gitignore` of a split folder was copied into each lab folder. Empty `OCR-RAG/README.md` moved to `section-3-structure-and-multimodal/README.md`. Untouched: `learnyst-html/`, `.html-cache/`, `RAG-Labs-Table-of-Contents.html`.
Leftover folders `MultiVector-RAG/`, `Graph-RAG/`, `Agentic-RAG/`, `Vectorless-RAG/`, `OCR-RAG/` now hold only a duplicate `.gitignore` (or nothing) and can be deleted.
