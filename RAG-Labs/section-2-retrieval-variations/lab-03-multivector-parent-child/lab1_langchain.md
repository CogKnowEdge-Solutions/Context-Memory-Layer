# Parent-Child & Summary-Based Multi-Vector RAG

---

# Problem Statement / Use Case Overview

A standard RAG pipeline embeds the exact same piece of text it later hands to the LLM. That creates a tug-of-war between two goals that both want a different chunk size. Small chunks embed precisely and match a question well, but they don't give the LLM enough surrounding context to answer fully. Large chunks give the LLM plenty of context, but they embed poorly, since a big block of mixed topics rarely matches a specific question closely.

### Key Terms Used in This Lab

| Term | Meaning |
|---|---|
| **Vector / embedding** | A list of numbers (here 384 of them) that represents the meaning of a piece of text. Texts with similar meaning get vectors that point in similar directions. |
| **Cosine similarity** | A score for how close two vectors are, based on the angle between them. Closer to 1 means more similar in meaning. Qdrant uses it to rank matches. |
| **`top_k` (written `k` in code)** | How many of the best-scoring matches a search returns. `search_kwargs={"k": 2}` means "give me the 2 closest". |
| **Token** | A small piece of text (a short word or part of a word) that an LLM reads and counts. Roughly, 1 token is about 4 characters of English. |
| **Context window** | The maximum number of tokens an LLM can read in one request (prompt plus answer). Parents have to be small enough to fit. |
| **LCEL** | LangChain Expression Language: the `\|` syntax that chains steps together, such as `prompt \| llm \| StrOutputParser()`. |

### How This Lab Solves It

This lab builds a way around that trade-off: stop using the same chunk for both jobs. A document is split into large **parent** chunks, which hold all the context the LLM will eventually need. Each parent is then split further into small **child** chunks, and also condensed into a short **summary** — both of which are built specifically to be easy to search. The children and summaries are the only things actually embedded and searched; the parents are kept in a separate **parent store** (a plain key-value store, not a vector index) and never touched during search. When a question comes in, the search step finds the closest-matching child or summary, and a retriever swaps it out for its full parent document before that goes to the LLM — meaning the piece that wins the search is never the piece the LLM actually reads.

**This pipeline has four connected parts:**

1. **Splitting** — break the document into large parent chunks, then split each parent further into small child chunks.
2. **Summarizing** — condense every parent into a short summary using the LLM.
3. **Indexing** — embed only the children and summaries into a vector store, while storing the full parents separately, linked by a shared ID.
4. **Retrieving and answering** — search the vectors, swap each match for its linked parent, and generate an answer with a full reasoning trace.

This is useful for:
- **Long, information-dense documents** — where a single paragraph often isn't enough context, but the whole document is too much to embed usefully.
- **Improving search precision without losing context** — small children and summaries search well; full parents still get read by the LLM.
- **Multiple ways to be found** — a parent can be matched either through one of its child chunks or through its own summary, giving it two chances to be the right result.

---

# Input Data

| Item | Detail |
|------|--------|
| **The PDF** | A document downloaded automatically from a link |
| **Your question** | A natural-language question about the document |
| **LLM API Key** | Used to generate summaries and the final answer |
| **Embedding model** | Runs locally — no API key needed, downloaded automatically the first time it's used |
| **Qdrant Cloud cluster (URL + API key)** | Hosts the vector store that holds the child and summary embeddings. Optional: Step 3 also shows an in-memory Qdrant option that needs no account |

---

# Processing

### Part A — Building the Two-Layer Index

```mermaid
flowchart LR
    PDF["PDF link"] --> DL["Download & extract text"]
    DL --> PC["Split into large<br/>Parent chunks (~10,000 chars)"]
    PC --> CC["Split each Parent further into<br/>small Child chunks (~400 chars)"]
    PC --> SM["Summarize each Parent<br/>using the LLM"]
    CC --> EMB["Embed Children into Qdrant"]
    SM --> EMB2["Embed Summaries into Qdrant"]
    PC --> DS["Store full Parents in a<br/>separate parent store"]

    classDef ingestStyle fill:#eef7ee,stroke:#3a7d3a,stroke-width:1px,color:#111111
    class PDF,DL,PC,CC,SM,EMB,EMB2,DS ingestStyle
```

Every parent chunk feeds three separate things: its own storage in the parent store, a set of child chunks, and a summary. Only the children and summaries end up as vectors in Qdrant — the parents themselves are never embedded, since their job is to hold context, not to be found through search.

### Part B — How a Question Finds Its Answer

```mermaid
flowchart LR
    Q["Question"] --> S["Search Qdrant for the closest<br/>Child chunk or Summary"]
    S --> M["Best match found —<br/>could be either type"]
    M --> ID["Read its linked doc_id"]
    ID --> P["Fetch the full Parent<br/>with that doc_id"]
    P --> C["Combine top Parents<br/>into labeled context"]
    C --> LLM["LLM answers using<br/>only that context"]
    LLM --> A["Final Answer +<br/>Explainability trace"]

    classDef defaultStyle fill:#ffffff,stroke:#333333,stroke-width:1px,color:#111111
    class Q,S,M,ID,P,C,LLM,A defaultStyle
```

The piece that actually wins the vector search — a child chunk or a summary — is never what reaches the LLM. As soon as a match is found, its `doc_id` is used to look up the complete parent it came from, and that full parent is what gets added to the context. This is the core trick of multi-vector retrieval: search on the small, precise version, but answer from the large, complete version.

### How One Parent Becomes Two Searchable Entry Points

Here's what happens to a single parent chunk, concretely, as it moves through the pipeline. Say a parent chunk holds several paragraphs about self-attention and computational complexity:

```mermaid
flowchart TB
    Parent["Parent Chunk<br/>(~10,000 characters)<br/>doc_id: abc-123"]

    Parent -->|split into several pieces| C1["Child 1<br/>doc_id: abc-123"]
    Parent -->|split into several pieces| C2["Child 2<br/>doc_id: abc-123"]
    Parent -->|split into several pieces| C3["Child 3<br/>doc_id: abc-123"]
    Parent -->|condensed by the LLM| Sum["Summary<br/>doc_id: abc-123"]

    C1 --> Qd[("Embedded into Qdrant")]
    C2 --> Qd
    C3 --> Qd
    Sum --> Qd

    Parent --> Store[("Stored, untouched,<br/>in the parent store")]

    classDef parentStyle fill:#ffe08a,stroke:#d68f00,stroke-width:2px,color:#1a1a1a
    classDef childStyle fill:#e7f1ff,stroke:#1d6fa5,stroke-width:1px,color:#0b1f33
    classDef sumStyle fill:#e9f9ee,stroke:#2f8d46,stroke-width:1px,color:#0b3d2e
    class Parent parentStyle
    class C1,C2,C3 childStyle
    class Sum sumStyle
```

Every one of those four searchable pieces — the three children and the summary — carries the exact same `doc_id` as the parent they came from. That shared ID is the only link between them; a question can match any one of the four and still be routed back to the same full parent. This is also why a single parent can be "found" through more than one path: its summary might match a broad question about the topic overall, while one of its children might match a very specific detail — but either way, the same parent ends up in the LLM's context.

### Walking Through a Sample Retrieval

Now here's the reverse direction: a question coming in and finding its way to an answer, using this lab's own question. The diagram below is **illustrative** — it shows the shape of the journey, not saved output. Which pieces win the search (and their IDs) is something you can see for yourself with the optional cell at the end of Step 8, which prints your real hits.

```mermaid
flowchart TB
    Q["Question: What is the computational complexity per<br/>layer of self-attention vs a recurrent layer?"]

    Q --> Search["Search Qdrant<br/>(across every embedded Child and Summary)"]

    Search -->|"closest match"| M1["Hit 1: a Child chunk or a Summary<br/>doc_id: A"]
    Search -->|"second closest match"| M2["Hit 2: a Child chunk or a Summary<br/>doc_id: B (or A again)"]

    M1 -->|"doc_id looked up"| P1["Full Parent A fetched<br/>(up to ~10,000 characters)"]
    M2 -->|"doc_id looked up"| P2["Full Parent B fetched<br/>(up to ~10,000 characters)"]

    P1 --> Ctx["Combined into labeled context:<br/>Source 1, Source 2"]
    P2 --> Ctx

    Ctx --> LLM["LLM answers using<br/>only the labeled Sources"]
    LLM --> Ans["Final Answer:<br/>O(n²·d) vs O(n·d²)"]

    classDef qStyle fill:#fff3cd,stroke:#d68f00,stroke-width:2px,color:#1a1a1a
    classDef matchStyle fill:#e7f1ff,stroke:#1d6fa5,stroke-width:1px,color:#0b1f33
    classDef parentStyle fill:#e9f9ee,stroke:#2f8d46,stroke-width:2px,color:#0b3d2e
    class Q qStyle
    class M1,M2 matchStyle
    class P1,P2,Ctx,LLM,Ans parentStyle
```

`search_kwargs={"k": 2}` means two matches come back, not just one. Each match can be a *child* chunk (good for exact details such as numbers in a table) or a *summary* (good for broad topic questions). Either way, the match is swapped for its full parent before the LLM sees anything, so the LLM reads complete sections instead of small fragments. That is why the real explainability trace in the Output section could refer to "Table 1" by name — a lone 400-character child could easily have cut that table off mid-sentence.

**Two hits can come from the same parent.** A child and the summary of the same parent share one `doc_id`, so they can both rank in the top 2. Both then point to the same parent. In that case the retriever hands back that parent once, so you can get fewer parents than `k`. The optional cell in Step 8 lets you check this on your own run.

---

## Qdrant Overview

**What is Qdrant?**

Qdrant is an open-source vector database — a database built specifically for storing embeddings (the numeric vectors that represent text) and for finding the ones closest to a query vector. Instead of matching exact text, it measures how semantically similar vectors are, so a question phrased differently from the stored text can still find the right content. In this lab, Qdrant is the search layer: it stores the small child chunks and the summaries as vectors, so a question can quickly retrieve the best matches before the retriever swaps them for their full parent documents.

The connection is made in Step 3, where `QdrantVectorStore.from_texts(...)` takes three pieces of information:

- `url` — the address of your Qdrant Cloud cluster, i.e. where the vectors live (loaded from `QDRANT_URL` in `.env`).
- `api_key` — the secret key that authorizes your code to read from and write to that cluster (loaded from `QDRANT_API_KEY` in `.env`).
- `collection_name` — the name of the "collection" (a Qdrant collection is roughly a table of vectors) that stores the children and summaries.

---

# Output

**Extracting the document** prints the total character count:

```
Extracted 39611 characters.
```

**Splitting into parent chunks** prints how many were created:

```
Created 5 Parent Documents.
```

**Splitting parents into child chunks** prints the total count across all parents:

```
Created 117 Child Documents.
```

**Summarizing every parent** confirms how many summaries were generated:

```
Generated 5 Summaries.
```

**Building the multi-vector index** confirms both the children and summaries were embedded, and the parents were linked in:

```
Multi-vector search index ready.
```

**Running the pipeline** on the question *"What is the computational complexity per layer of a self-attention mechanism compared to a recurrent layer?"* returns a two-part answer:

```
### Final Answer
A self-attention layer has a per-layer computational complexity of **O(n² · d)**, whereas a recurrent layer has a complexity of **O(n · d²)**. Thus, self-attention scales quadratically with sequence length but linearly with representation dimension, while recurrent layers scale linearly with sequence length but quadratically with representation dimension.

### AI Tracing & Explainability
I extracted the complexity figures from Table 1 in the provided context. The table lists:
- **Self-Attention**: complexity per layer = **O(n² · d)**.
- **Recurrent**: complexity per layer = **O(n · d²)**.

These entries directly answer the question by comparing the two mechanisms. No additional text was copied; I simply referenced the table's values and explained the scaling relationship.
```

Notice the explainability trace references a specific table from the source document — something only visible because the full parent chunk (not just a small child fragment) was passed to the LLM as context.

---

# Tech Stack

| Component | Tool |
|---|---|
| **PDF Text Extraction** | `pypdf` — pulls raw text out of every page of the PDF |
| **File Downloading** | `requests` — grabs the PDF from a link |
| **Text Splitting** | `langchain-text-splitters` (`RecursiveCharacterTextSplitter`) — used twice, once for large parent chunks and once for small child chunks |
| **Summarization** | LLM (`nvidia/nemotron-3-super-120b-a12b:free`), via an LCEL chain built with `langchain-core` |
| **Embedding Model** | `sentence-transformers` / `all-MiniLM-L6-v2`, via `langchain-huggingface` — runs locally |
| **Vector Store** | `Qdrant` Cloud, via `langchain-qdrant` — a hosted vector database holding only the children and summaries, accessed with a cluster `url` and `api_key` |
| **Parent Store** | `InMemoryByteStore` — holds the full parent documents, keyed by ID (the retriever calls it `docstore`) |
| **Retrieval Logic** | `MultiVectorRetriever`, from `langchain-classic` — searches the vector store, then swaps each match for its linked parent |
| **Prompt & Chain Orchestration** | `langchain-core` — `ChatPromptTemplate`, `RunnablePassthrough`, `RunnableParallel`, and `StrOutputParser`, chained together with the `\|` operator |
| **Notebook Display** | `IPython.display` (`Markdown`, `display`) — renders the LLM's markdown answer with formatting in the notebook |

---

# Underlying Concepts (Summarized)

**Multi-Vector Retrieval** is the general idea behind this pipeline: instead of embedding and searching the exact text that gets shown to the LLM, one or more *searchable* representations are embedded instead, and each is linked back to the *real* content that should actually be used once a match is found.

**Parent Chunk** is a large piece of the document, sized to give the LLM enough surrounding context to answer well. Parents are never embedded directly — they're only ever retrieved by way of something smaller that points to them.

**Child Chunk** is a small piece cut out of a parent, sized to embed precisely enough to match a specific, narrow question. Every child carries the same ID as its parent, so a match on the child can be traded for the full parent afterward.

**Summary** is a short, LLM-generated condensation of a parent's content. Because it's phrased more like a general description of the topic, it tends to match broader questions that a narrow child chunk might miss.

**`doc_id`** is the shared identifier that ties a parent to all of its children and its summary. It's the only thing connecting the searchable vectors to the real documents sitting in the separate parent store.

**LCEL (LangChain Expression Language)** is the `|`-based syntax used to chain steps together — for example, `prompt | llm | StrOutputParser()` means "fill in the prompt, send it to the model, then turn the reply into a plain string." It keeps a multi-step process readable as a single expression.

> **Why this matters:** Searching a full 10,000-character parent chunk directly would blur together many different ideas into one vector, making it hard to match against a specific question. Searching a 400-character child instead finds a precise, narrow match — but the LLM still needs the surrounding paragraphs to answer completely, which is exactly what gets pulled back in once the matching child's `doc_id` points to its parent.

---

# Pre-requisites

- **Basic familiarity** with Python (functions, loops, `import` statements).
- **A general sense of what RAG and embeddings are** — retrieving relevant text using vector similarity before asking an LLM to answer.
- **An LLM API Key** — used for summarization and for generating the final answer.
- **A Qdrant Cloud cluster** — its URL and API key host the vector store (see "Getting Qdrant Credentials" below). No account? Skip that section and use the optional in-memory cell in Step 3 instead.

---

## Getting Qdrant Credentials

1. Go to [cloud.qdrant.io](https://cloud.qdrant.io) and sign up, or log in if you already have an account.
2. Click **Create Cluster** to set up a new cluster. A free tier is available for testing and is enough for this lab.
3. Choose a cloud provider and region, give the cluster a name, and confirm. Creating it takes a minute or two while the cluster provisions.
4. Once the cluster is ready, open its **Overview** page and copy the **Cluster URL** — it looks like `https://<cluster-id>.cloud.qdrant.io:6333`. Save it as `QDRANT_URL` in the `.env` file next to this notebook.
5. Open the cluster's **Access Control** (or **API Keys**) tab. Copy the existing API key, or create a new one. Save it as `QDRANT_API_KEY` in the same `.env` file.

The `.env` file holds all three secrets the notebook needs:

```bash
QDRANT_URL=https://<cluster-id>.cloud.qdrant.io:6333
QDRANT_API_KEY=<your Qdrant cluster API key>
OPENROUTER_API_KEY=<your OpenRouter API key>
```

> **Tip:** Keep the credentials out of the notebook itself — the code calls `load_dotenv(".env")` and reads everything with `os.getenv(...)`, so nothing sensitive is exposed if the file is shared.

---

# Environment / Dependencies Setup

The cell below installs all required Python packages:

| Package | Purpose |
|---------|---------|
| `langchain`, `langchain-classic`, `langchain-community` | Core LangChain components, including `MultiVectorRetriever` |
| `langchain-openai` | Wraps the LLM in LangChain's `ChatOpenAI` interface |
| `langchain-huggingface` | Wraps the local embedding model |
| `langchain-qdrant`, `qdrant-client` | Connects to and manages the Qdrant vector store |
| `pypdf` | **PDF text extraction** |
| `tiktoken` | Token counting, used internally by some LangChain components |
| `flask`, `numpy`, `scipy`, `scikit-learn` | Supporting libraries used by the retrieval and embedding stack |
| `sentence-transformers` | Backs the local embedding model |
| `python-dotenv` | Loads the secrets from the `.env` file into the notebook |
| `ipython` | Provides `IPython.display` (`Markdown`, `display`) for rendering answers in the notebook |

> **Note:** Run this cell first — it only needs to be run once per session.

```python
!pip install -qU langchain langchain-classic langchain-community langchain-openai langchain-huggingface langchain-qdrant qdrant-client pypdf tiktoken flask numpy scipy scikit-learn sentence-transformers python-dotenv "torch>=2.5" ipython
```

---

# Step-wise Instructions — Development

---

### Step 1 — Imports

```python
import os

import requests
from dotenv import load_dotenv
from IPython.display import Markdown, display
from langchain_classic.retrievers.multi_vector import MultiVectorRetriever
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_core.stores import InMemoryByteStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
```

| Import | Purpose |
|---|---|
| `os` | Reads the secrets loaded from `.env` via `os.getenv(...)` |
| `load_dotenv` | Loads the `.env` file sitting next to the notebook into the environment |
| `hashlib` | Imported later, in Step 6 — its SHA-256 hash gives each parent a stable ID that links it to its children and summary |
| `requests` | Downloads the PDF |
| `PdfReader` | Extracts raw text from the PDF |
| `ChatOpenAI` | LangChain's wrapper for calling the LLM |
| `HuggingFaceEmbeddings` | Loads the local embedding model |
| `RecursiveCharacterTextSplitter` | Splits text into chunks, used for both parents and children |
| `MultiVectorRetriever` | Searches the vector store, then swaps each match for its linked parent |
| `InMemoryByteStore` | Holds the full parent documents |
| `QdrantVectorStore` | The vector store holding children and summaries |
| `Document` | LangChain's standard wrapper for a piece of text plus its metadata |
| `ChatPromptTemplate` | Builds a reusable prompt with fillable variables |
| `StrOutputParser` | Converts the LLM's reply into a plain string |
| `RunnablePassthrough`, `RunnableParallel` | Building blocks for chaining steps together with LCEL |
| `Markdown`, `display` | Renders the LLM's markdown answer with proper formatting in the notebook |

---

### Step 2 — Configure Models

```python
# Load the secrets (QDRANT_URL, QDRANT_API_KEY, OPENROUTER_API_KEY) from .env
load_dotenv(".env")

# Initialize Chat Model
llm = ChatOpenAI(
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    # openai-compatible client, but routed to OpenRouter's servers
    openai_api_base="https://openrouter.ai/api/v1",
    model_name="nvidia/nemotron-3-super-120b-a12b:free",
    temperature=0.0
)

# Initialize Dense Embedding Model
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
```

> **Note:** `load_dotenv(".env")` reads the key–value pairs from the `.env` file in the lab folder, so `os.getenv("OPENROUTER_API_KEY")` returns your real key without it ever appearing in the notebook. `temperature=0.0` keeps the summaries and final answers consistent. This one LLM connection is reused for both summarizing parents and generating the final answer.

---

### Step 3 — Initialize Storage Architecture or Use Existing if already made

```python
# Qdrant Cloud holds the child & summary VECTORS (the semantic search index)
vectorstore = QdrantVectorStore.from_texts(
    # throwaway seed text: from_texts needs at least one string to create the collection
    texts=["Initialize"], 
    embedding=embeddings, 
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
    collection_name="multi_vector_collection"
)

# Will hold the full parent documents, keyed by doc_id, once the retriever wraps it
store = InMemoryByteStore()
id_key = "doc_id"
```

```python
# Use this instead of the cell above ONLY if you already ran this notebook before and the vectors already exist in Qdrant. Comment out the cell above and uncomment this one.
# vectorstore = QdrantVectorStore.from_existing_collection(
#     embedding=embeddings,
#     url=os.getenv("QDRANT_URL"),
#     api_key=os.getenv("QDRANT_API_KEY"),
#     collection_name="multi_vector_collection"
# )
#
# store = InMemoryByteStore()
# id_key = "doc_id"
```

This cell connects the pipeline to Qdrant Cloud and sets up the storage that backs the multi-vector retriever. `QdrantVectorStore.from_texts(...)` opens — or creates, if it doesn't already exist — a Qdrant collection named `multi_vector_collection` on the cluster at `os.getenv("QDRANT_URL")`, authenticating with `os.getenv("QDRANT_API_KEY")`; both values come from the `.env` file loaded in Step 2. The `texts=["Initialize"]` argument seeds the collection with one throwaway vector, purely so the collection is created before the real documents are added later. The `embedding=embeddings` argument tells Qdrant which embedding model produced the vectors being stored. `store` is an `InMemoryByteStore` that will hold the full parent documents, and `id_key = "doc_id"` names the metadata field that will link every vector back to its parent.

The second cell is the alternative for when the collection is **already stored in the cloud** — for example, from a previous run of this notebook. `QdrantVectorStore.from_existing_collection(...)` connects to that existing `multi_vector_collection` using the same `url` and `api_key`, without creating a new one or re-seeding it. It sets up the exact same `store` and `id_key`, so nothing downstream changes. This cell is **commented out by default** because the first-time setup needs to create the collection; only use it if you already ran the notebook before, in which case you comment out the cell above and uncomment this one.

#### Optional: no Qdrant Cloud account? Use in-memory Qdrant

Qdrant can also run entirely inside your notebook. Pass `location=":memory:"` instead of `url` and `api_key`, and nothing needs to be signed up for or stored in `.env` (except `OPENROUTER_API_KEY`). Run this cell **instead of** the Qdrant Cloud cell above:

```python
# OPTIONAL: no Qdrant Cloud account? Run this INSTEAD of the Qdrant Cloud cell above.
# It keeps the vectors in this notebook's memory, so they disappear when the kernel restarts.
vectorstore = QdrantVectorStore.from_texts(
    texts=["Initialize"],
    embedding=embeddings,
    location=":memory:",
    collection_name="multi_vector_collection"
)

store = InMemoryByteStore()
id_key = "doc_id"
```

Everything after this step works unchanged. The trade-off: the vectors live only in this notebook session. If you restart the kernel they are gone, so rerun the notebook from the top, and the `from_existing_collection` cell does not apply.

#### The leftover "Initialize" vector

`texts=["Initialize"]` really does leave one throwaway vector in the collection, and nothing in this lab removes it. After Step 8 the collection holds that one seed plus the real children and summaries. It is harmless in most searches, but a very odd query could match it. Because it has no `doc_id`, the retriever has no parent to swap it for, so it adds nothing useful. If you want it gone, run this optional cell once after the collection is created and before Step 8:

```python
# OPTIONAL: delete the throwaway "Initialize" vector so it can never show up as a search hit.
# Run it once, right after the cell that creates the collection and before Step 8.
from qdrant_client import models

vectorstore.client.delete(
    collection_name="multi_vector_collection",
    points_selector=models.FilterSelector(
        filter=models.Filter(
            must=[models.FieldCondition(key="page_content", match=models.MatchValue(value="Initialize"))]
        )
    ),
)
```

---

### Step 4 — Download & Extract Document

```python
# Attention is All You Need paper (source document for this lab)
PDF_URL = "https://arxiv.org/pdf/1706.03762.pdf"
PDF_FILENAME = "attention_paper.pdf"

# Download the PDF and save it locally; raise an error on HTTP failure
response = requests.get(PDF_URL)
response.raise_for_status()

with open(PDF_FILENAME, "wb") as f:
    f.write(response.content)
```

```python
# Extract text from every page and join pages with newlines into one string
reader = PdfReader(PDF_FILENAME)
raw_text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])

print(f"Extracted {len(raw_text)} characters.")
```

This step reads every page in the PDF rather than stopping after a character limit, since the full multi-vector setup is meant to handle a complete, long document. By the end of this step, `raw_text` holds the entire extracted document as one string.

---

### Step 5 — Generate Parent Documents

```python
# Parent chunks are LARGE (~10k chars) so the LLM has full context to answer from
parent_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=200)
parent_chunks = parent_splitter.split_text(raw_text)

# Wrap each chunk in a Document (parents are stored, not embedded directly)
parent_docs = [Document(page_content=chunk) for chunk in parent_chunks]

print(f"Created {len(parent_docs)} Parent Documents.")
```

A `chunk_size` of 10,000 characters is large enough to hold several paragraphs of surrounding context, which is exactly what the LLM will eventually need to answer fully. By the end of this step, `parent_docs` holds a list of `Document` objects — the exact pieces that will later be stored, untouched, and handed to the LLM once one of their children or summaries is matched.

---

### Step 6 — Generate Child Documents

This is where the link between parents and children is actually created: instead of a random `uuid`, each parent gets a deterministic ID derived from its own text. The `stable_id` helper hashes the chunk content with SHA-256, so the same chunk always produces the same `doc_id` — even across different runs of the notebook. That ID is stamped onto the parent itself, then copied onto every child cut out of it.

```python
import hashlib

def stable_id(text):
    """Deterministic ID derived from the chunk text, so the same chunk always gets the same ID across runs."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
```

Child chunks are deliberately small, so they embed precisely for semantic search.

```python
child_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
child_docs = []

for doc in parent_docs:
    _id = stable_id(doc.page_content)
    # the parent carries its own id, which every child below will inherit
    doc.metadata["doc_id"] = _id

    child_splits = child_splitter.split_documents([doc])
    for child in child_splits:
        # stamp the parent id so retrieval can jump from child chunk back to parent
        child.metadata["doc_id"] = _id

    child_docs.extend(child_splits)

print(f"Created {len(child_docs)} Child Documents.")
```

By the end of this step, every parent has a stable `doc_id`, and every one of its children carries that exact same ID in its metadata.

**Why a hash instead of a random ID?** The parent store is in memory, so it is empty every time the notebook restarts, while vectors in Qdrant Cloud stay. If IDs were random, rebuilding the parents would give them new IDs and the vectors already in Qdrant would point at parents that no longer exist. With a hash of the text, the same PDF and the same splitter settings always rebuild the same IDs, so the old vectors still link to the rebuilt parents. (Change the text or the chunk size and the hashes change too, so re-index in that case.)

---

### Step 7 — Define and Execute Summarization Pipeline

```python
# Prompt: compress a parent chunk into a short summary while keeping key terms
summary_prompt = ChatPromptTemplate.from_template(
    "Summarize the following core concepts concisely. Do not lose technical keywords.\n\nText: {context}"
)

# LCEL chain: pass text through unchanged → prompt → LLM → plain string output
summary_chain = (
    {"context": RunnablePassthrough()} 
    | summary_prompt 
    | llm 
    | StrOutputParser()
)
```

```python
summary_docs = []

# Summarize each parent and carry its doc_id so the summary maps back to it
for doc in parent_docs:
    summary_text = summary_chain.invoke(doc.page_content)
    
    summary_doc = Document(
        page_content=summary_text,
        metadata={"doc_id": doc.metadata["doc_id"]}
    )
    summary_docs.append(summary_doc)

print(f"Generated {len(summary_docs)} Summaries.")
```

`RunnablePassthrough()` simply lets the raw parent text flow into the prompt unchanged, and the chain then sends that filled-in prompt to the LLM and converts the reply into a plain string. Each resulting summary is wrapped in its own `Document`, carrying the same `doc_id` as the parent it was built from — the same linking pattern used for the children in the step before.

---

### Step 8 — Configure Multi-Vector Retriever

```python
retriever = MultiVectorRetriever(
    vectorstore=vectorstore,   # searches child/summary embeddings
    byte_store=store,          # returns the linked parent documents
    id_key=id_key,             # the metadata field linking vectors to parents
    search_kwargs={"k": 2}    # return top-2 matches per query
)

# Store the full parent Documents in the parent store (auto-serialized into the byte store)
retriever.docstore.mset([(doc.metadata[id_key], doc) for doc in parent_docs])

# First-time setup: uploads vectors to Qdrant. If you already ran this notebook before and data already exists in Qdrant, comment out these two lines to avoid uploading duplicates.
retriever.vectorstore.add_documents(child_docs)
retriever.vectorstore.add_documents(summary_docs)

print("Multi-vector search index ready.")
```

This is where the two storage systems set up in Step 3 are wired together into one retriever. `retriever.docstore.mset(...)` saves every parent, keyed by its `doc_id`, into the parent store. `add_documents` then embeds the children and summaries into Qdrant, each still carrying the `doc_id` that connects it back to its parent. `search_kwargs={"k": 2}` means every query returns the top 2 closest matches, whether those happen to be children, summaries, or a mix of both.

#### What lives where

After Step 8, the two storage systems hold different things. The counts come from this lab's printed outputs (5 parents, 117 children, 5 summaries):

| | Qdrant (vector store) | Parent store (`InMemoryByteStore`) |
|---|---|---|
| **Holds** | Child chunks and summaries, as vectors plus their text | Full parent chunks, as stored `Document`s |
| **How many** | 117 children + 5 summaries = 122 vectors (plus the 1 seed vector from Step 3) | 5 parents |
| **Size of each item** | About 400 characters per child; a short summary | Up to about 10,000 characters |
| **Keyed by** | Searched by meaning; each carries `doc_id` in its metadata | Looked up by `doc_id` |
| **Searched?** | Yes | No, only fetched by ID |
| **Survives a restart?** | Qdrant Cloud: yes. In-memory Qdrant: no | No, rebuilt each run |

#### Optional: see the swap on your own run

The retrieval walkthrough above is illustrative. This optional cell prints your real raw hits and the parents they are swapped for. Its output is not saved in this lesson, because it depends on your run.

```python
# OPTIONAL: look at the raw search hits, then at the parents the retriever swaps them for
peek_query = "What is the computational complexity per layer of a self-attention mechanism compared to a recurrent layer?"

raw_hits = vectorstore.similarity_search(peek_query, k=2)
for i, hit in enumerate(raw_hits):
    print(f"RAW HIT {i + 1}: {len(hit.page_content)} chars | doc_id {hit.metadata['doc_id'][:16]} | {hit.page_content[:80]!r}")

parents = retriever.invoke(peek_query)
for i, parent in enumerate(parents):
    print(f"PARENT {i + 1}: {len(parent.page_content)} chars | doc_id {parent.metadata['doc_id'][:16]}")
```

---

### Step 9 — Define the RAG Execution Function with Explainability

The prompt asks for two sections: the answer, then a trace of which sources were used.

```python
qa_template = """
You are a technical assistant. Answer the question using ONLY the provided context.

Context:
{context}

Question: {question}

Respond in exactly this format:

### Final Answer
<a clear, direct answer to the question>

### AI Tracing & Explainability
<Explain step by step how you arrived at the answer. Refer to the sources you used by their label (e.g. "Source 1"), state what each one contributed, and why it was relevant. Do not copy large blocks of text from the context — explain in your own words. Use as many lines as you need.>
"""

qa_prompt = ChatPromptTemplate.from_template(qa_template)
```

Those "Source 1", "Source 2" labels are what the trace refers back to, so they get attached here, before the chain is assembled.

```python
def format_docs(docs):
    """Label each source so the LLM can reference it by number in its tracing."""
    formatted = []
    for i, doc in enumerate(docs):
        parent_id = doc.metadata.get('doc_id', 'N/A')
        formatted.append(f"[Source {i+1}] (Parent ID: {parent_id})\n{doc.page_content}")
    return "\n\n".join(formatted)
```

Now wire retrieval and generation together. `RunnableParallel` runs the retriever and carries the raw question forward at the same time, so both are available to the next step.

```python
retrieval_chain = RunnableParallel(
    {"context": retriever, "question": RunnablePassthrough()}
)

# assign() reformats context in place while keeping the question key alongside
generation_chain = (
    RunnablePassthrough.assign(context=(lambda x: format_docs(x["context"])))
    | qa_prompt
    | llm
    | StrOutputParser()
)

# .assign attaches the generated answer without dropping the retrieved context
rag_chain = retrieval_chain.assign(answer=generation_chain)
```

#### What shape is the data at each stage?

```mermaid
flowchart TB
    Q["Input: question<br/>(a str)"] --> RP["RunnableParallel<br/>runs two branches"]
    RP --> R["retriever branch<br/>list of parent Documents"]
    RP --> QP["RunnablePassthrough branch<br/>question (a str)"]
    R --> D1["dict:<br/>context + question"]
    QP --> D1
    D1 --> F["format_docs<br/>context becomes one labeled str"]
    F --> PR["qa_prompt<br/>filled-in prompt"]
    PR --> L["llm<br/>AIMessage"]
    L --> SP["StrOutputParser<br/>answer (a str)"]
    SP --> OUT["Final dict: context (Documents),<br/>question, answer"]

    classDef defaultStyle fill:#ffffff,stroke:#333333,stroke-width:1px,color:#111111
    class Q,RP,R,QP,D1,F,PR,L,SP,OUT defaultStyle
```

Note that `format_docs` only changes the context *inside* `generation_chain`; the final dict returned by `rag_chain` still holds the original parent `Document` objects under `context`, next to the `question` and the `answer`.

Numbering each retrieved parent as "Source 1," "Source 2," and so on is what lets the LLM refer back to specific sources by name in its explainability trace instead of describing them vaguely. `generation_chain` formats whatever parents came back, fills in the prompt, and asks the LLM to answer strictly in the two-section format above. `rag_chain` ties both halves together into a single object that can be run with one call.

---

### Step 10 — Execute Query

```python
def run_rag_pipeline(query: str):
    """
    Executes the RAG pipeline and displays the LLM's own answer + reasoning.
    """
    response = rag_chain.invoke(query)
    display(Markdown(response["answer"]))
    return response
```

```python
query = "What is the computational complexity per layer of a self-attention mechanism compared to a recurrent layer?"
response = run_rag_pipeline(query)
```

`rag_chain.invoke(query)` runs the entire pipeline end-to-end: the question is embedded, the closest children and summaries are found, their parents are pulled in, and the LLM answers using that full context. `display(Markdown(...))` renders the answer with its headings and bold text formatted properly inside the notebook, rather than as plain unformatted text.

---

# What We Learnt

By the end of this lab, a single document has been indexed twice over — once as small, precise children and summaries for searching, and once as large, complete parents for answering — with a retriever in between that automatically swaps one for the other.

**Key takeaways:**
- **Search precision and answer context don't have to come from the same chunk** — small children and summaries are what get searched, while their much larger parents are what actually get read by the LLM.
- **A shared ID is what makes the swap possible** — every child and summary carries the exact same `doc_id` as its parent, which is how a match on one instantly resolves to the other.
- **A parent can be found more than one way** — through any of its child chunks, or through its own summary, giving broad and narrow questions both a fair chance of finding it.
- **Two separate storage systems play different roles** — a vector store holds only what needs to be searched, while a plain parent store holds the full content that needs to be preserved exactly as written.
- **LCEL chains keep multi-step logic readable** — formatting, prompting, calling the LLM, and parsing the reply are expressed as one chained pipeline rather than several separate function calls.
- **Explainability still works, even with retrieved parents rather than tiny fragments** — labeling each source lets the LLM reference exactly which parent contributed which part of the answer.