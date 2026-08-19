# Context-Memory-Layer

A persistent, context-aware memory layer for AI agents and applications.

## The Problem

Large language models (LLMs) are stateless by nature. Every new prompt is processed in isolation — the model forgets what it said moments ago, what it learned in prior sessions, and what worked or failed before. This forces applications to re-inject context manually, results in fragmented and repetitive reasoning, and makes agents incapable of building on past experience.

## The Solution

The Context Memory Layer bridges this gap by giving AI agents a **persistent, structured memory** that is actively retrieved and injected at inference time. Instead of a single stateless prompt, agents get a curated slice of relevant context drawn from everything the system has ever seen or learned — just like how a human draws on working memory, experience, and learned facts to make decisions.

## Memory & Context Layer

The memory layer is organized into four complementary memory types:

- **Short-term**: Current conversation context, working memory
- **Long-term**: Vector embeddings, knowledge bases, conversation history
- **Episodic**: Past interactions and outcomes
- **Semantic**: Facts, skills, world knowledge

These are complemented by **retrieval mechanisms** that select and surface the most relevant context for any given query.

## Why It Matters

- **Continuity**: Agents maintain coherent, informed behavior across sessions
- **Contextual relevance**: Retrieval surfaces the right knowledge at the right time
- **Learning over time**: Systems improve by accumulating and applying past outcomes
- **Reduced redundancy**: Relevant context is injected once, precisely, rather than dumped wholesale

## Repository Structure

```
RAG-Labs/
├── Agentic-RAG/           # Agentic RAG with tool use and multi-step reasoning
├── Graph-and-Vector/      # Hybrid graph + vector retrieval
├── Graph-RAG/             # Graph-based retrieval augmented generation
├── HybridRAG/             # Hybrid RAG combining sparse + dense retrieval
├── LLM-Wiki/              # LLM knowledge base with Wikipedia-style retrieval
├── MultiVector-RAG/       # Multi-vector retrieval (LangChain + ColBERT)
├── OCR-RAG/               # OCR-powered RAG for scanned documents
└── Vectorless-RAG/        # RAG without vector embeddings

MongoDB-Labs/
└── Lab 1 - Student Records Lookup/  # MongoDB Atlas CRUD, queries, indexing
```

## License

[MIT](LICENSE)
