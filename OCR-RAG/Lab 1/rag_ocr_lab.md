# Structured OCR + RAG Chatbot: Chatting with Invoices Using RapidOCR and Gemini

---

# Problem Statement / Use Case Overview

Invoices, receipts, and purchase orders usually exist as scanned images or photos, not as searchable text. To ask a question like "what was the total on this invoice?", the numbers first have to be pulled out of the image correctly — and this is where most simple OCR setups fall apart. A basic OCR pass reads every text box on the page but throws away the layout, so an invoice's neatly organized rows and columns turn into a jumbled bag of words. Once that happens, an LLM reading the output can no longer tell which number belongs to which field, and it starts guessing.

This lab avoids that problem by keeping the page's layout intact when the text is extracted, so a number like `$56,651.49` still sits next to the label `Charges` instead of floating loose in a wall of text. Each document is then turned into its own searchable unit, so when you ask a question, only the relevant document(s) are pulled in as context — and the LLM is told to tag every fact it uses with the exact document it came from.

This is especially useful for:
- **Digitizing invoices and receipts** — turning scanned images into something you can actually query
- **Expense and purchase-order tracking** — quickly pulling a specific number out of a pile of documents
- **Any situation where an answer needs to be traceable back to the exact document it came from**

---

# Input Data

| Item | Detail |
|------|--------|
| **Your question** | A question about one or more of the invoices/receipts (e.g. "What's the invoice number on the Contoso invoice?") |
| **The sample documents** | An invoice, a receipt, and a purchase order — downloaded automatically from GitHub links, no need to have them saved beforehand |
| **Gemini API Key** | Used both to embed each document for retrieval, and to generate the final answer |

---

# Processing

### The Full Flow

*(Diagram to be added here)*

Every question goes through the same five stages: the sample documents are downloaded, each one is read by RapidOCR and turned into structured text, that text is embedded and stored as a tiny knowledge base, the question is compared against that knowledge base to find the closest match(es), and Gemini writes the final answer using only what was retrieved — tagging every fact with the document it came from.

### How Each Document Becomes Searchable

*(Diagram to be added here)*

Each image goes through OCR once, is converted into layout-preserving text, and is embedded into a single vector. There's no splitting into a dozen fragments and no vector database to manage — with only a handful of short documents, one embedding per document is enough to make retrieval accurate.

### Answering a Question, Step by Step

*(Diagram to be added here)*

The question is embedded the same way the documents were, compared against every document's embedding using cosine similarity, and the top matches are handed to Gemini as labeled context. Gemini is instructed to answer only from that context and to cite the source document for every fact.

---

# Output

A plain, accurate answer built from the OCR'd text of the relevant document(s), with every fact tagged to the document it came from. For example:

> _"The total charge on the Contoso invoice was $56,651.49. [Source: simple-invoice.png]"_

Along with the answer, the lab also prints:
- **The document(s) it retrieved**, along with their similarity score to the question
- **A short explanation for each document** — whether it was actually cited in the answer, and why it mattered

---

# Tech Stack

| Component | Tool |
|---|---|
| **Reading the documents** | RapidOCR — a fast, CPU-only OCR engine that detects and reads text boxes in each image |
| **Structuring the OCR output** | RapidOCR's `.to_markdown()` — rebuilds a reading order from the box coordinates, so rows and columns stay roughly aligned instead of turning into a flat list |
| **Building the knowledge base** | Gemini Embedding API (`gemini-embedding-001`) — turns each document's structured text into a vector |
| **Searching for relevant documents** | Cosine similarity (plain NumPy) — compares the question's embedding to every document's embedding, no vector database needed |
| **Writing the answer** | Gemini Chat model (`gemini-2.5-flash`) — reads the retrieved document(s) and writes the answer, tagging every fact with its source |
| **Downloading the sample documents** | `requests` — grabs each sample invoice/receipt from GitHub and saves it locally |

---

# Underlying Concepts (Summarized)

A plain OCR engine gives you text boxes with coordinates, but no sense of layout — everything comes back as one flat list, in whatever order the engine happened to detect it. For a document like an invoice, that's a problem, because the meaning of a number depends entirely on which column and row it sits in. This lab uses RapidOCR's layout-aware output instead of the raw text list, so a document like `Invoice Number: 34278587` stays readable as a document, not a scrambled sentence.

Once the text is structured, this becomes a standard **RAG (Retrieval-Augmented Generation)** setup, just applied to OCR output instead of plain text files:
- **Retrieval** — every document is embedded once, and a question is matched against those embeddings using cosine similarity, so only the most relevant document(s) are used.
- **Generation** — the matched document(s) are handed to Gemini as context, with instructions to answer only from what's given and to cite the source document for every fact, using a tag like `[Source: filename]`.

That citation tag is what makes the explainability check possible afterward — the lab doesn't have to guess which documents actually mattered, it just checks whether each document's tag shows up in the final answer.

---

# Pre-requisites

- A Gemini API key (free at https://aistudio.google.com/apikey)
- A basic idea of what OCR and an LLM are

---

# Environment / Dependencies Setup

The cell below installs all required Python packages:

| Package | Purpose |
|---------|---------|
| `rapidocr` | Reads each image and extracts its text, box by box |
| `onnxruntime` | The CPU backend RapidOCR runs its models on |
| `google-genai` | Connects to Gemini for both embeddings and chat generation |
| `requests` | Downloads the sample invoices from GitHub |
| `numpy` | Does the cosine similarity math for retrieval |

```python
# rapidocr        -> the OCR engine (runs fully on CPU via onnxruntime)
# onnxruntime      -> the backend RapidOCR uses to run its models
# google-genai     -> the official Gemini API SDK (chat + embeddings)
# requests, numpy  -> downloading files & doing the similarity math
!pip install rapidocr onnxruntime google-genai requests numpy --quiet
```

## Import Libraries

```python
# Standard library
import os
import json

# For downloading the sample invoices and doing vector math
import requests
import numpy as np

# RapidOCR -- our OCR engine
from rapidocr import RapidOCR

# Gemini SDK -- used both for embeddings (retrieval) and chat (generation)
from google import genai
```

## Add Your Key

```python
# Paste your key when prompted (get one for free at https://aistudio.google.com/apikey)
GEMINI_API_KEY = input("Enter your Gemini API key: ").strip()

# Create one Gemini client we'll reuse for both embeddings and chat generation
client = genai.Client(api_key=GEMINI_API_KEY)

# Model names -- change these if Google renames/updates them later
CHAT_MODEL = "gemini-2.5-flash"
EMBED_MODEL = "gemini-embedding-001"

print("Gemini client ready.")
```

> 📝 **Note:** This is the only manual input the notebook needs — everything else, from downloading the documents to running OCR, happens automatically.

---

# Step-wise Instructions — Development

---

### Step 1 — Download the Sample Invoices

Three sample documents (an invoice, a receipt, and a purchase order) are downloaded directly from GitHub and saved locally, so there's nothing to upload by hand.

```python
# Direct links to freely available sample documents on GitHub
INVOICE_URLS = {
    "simple-invoice.png": "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/simple-invoice.png",
    "contoso-receipt.png": "https://raw.githubusercontent.com/Azure/azure-sdk-for-python/master/sdk/formrecognizer/azure-ai-formrecognizer/tests/sample_forms/receipt/contoso-receipt.png",
    "purchase-order-1.jpg": "https://raw.githubusercontent.com/Azure/azure-sdk-for-python/master/sdk/formrecognizer/azure-ai-formrecognizer/tests/sample_forms/forms/Form_1.jpg",
}

os.makedirs("invoices", exist_ok=True)
invoice_paths = {}

for filename, url in INVOICE_URLS.items():
    path = os.path.join("invoices", filename)
    response = requests.get(url)
    response.raise_for_status()
    with open(path, "wb") as f:
        f.write(response.content)
    invoice_paths[filename] = path
    print(f"Downloaded {filename} ({len(response.content)/1024:.1f} KB)")
```

---

### Step 2 — Run OCR on Each Document

RapidOCR detects every text box on the page, then reads the text inside each one. It runs entirely on CPU and needs no GPU, so this step works the same on a laptop as it would on a server.

```python
# Initialize the OCR engine once -- this loads the detection, classification, and recognition models
engine = RapidOCR()

ocr_results = {}
for filename, path in invoice_paths.items():
    result = engine(path)
    ocr_results[filename] = result
    print(f"{filename}: found {len(result.txts)} text boxes in {result.elapse:.2f}s")
```

---

### Step 3 — Convert OCR Output into Structured Text

A plain list of text boxes loses the document's layout — which line belongs to which column, which label goes with which value. RapidOCR's `.to_markdown()` uses the box coordinates to rebuild a reading order that keeps rows and columns roughly aligned, so the output reads like the document instead of a shuffled list of words.

```python
# Build a dictionary of {filename: structured_text} -- this is our tiny document store
document_texts = {}
for filename, result in ocr_results.items():
    document_texts[filename] = result.to_markdown()

# Peek at one example to see the structure preserved
print(document_texts["simple-invoice.png"])
```

This is the difference between "structured" and plain OCR: instead of `Invoice Number Invoice Date 34278587 6/18/2017 ...` all run together, the layout-aware version keeps the header row and the value row visibly separate.

---

### Step 4 — Embed Each Document (Build the Knowledge Base)

Each document is short, so the whole thing is treated as a single retrieval unit. For longer documents you'd split the text into smaller overlapping chunks first, but with invoice-length text, one chunk per document keeps things simple without losing accuracy.

```python
def embed_text(text):
    """Get a Gemini embedding vector for a piece of text."""
    response = client.models.embed_content(model=EMBED_MODEL, contents=text)
    return np.array(response.embeddings[0].values)

# Build the knowledge base: one entry per document, with its text and embedding
knowledge_base = []
for filename, text in document_texts.items():
    knowledge_base.append({
        "source": filename,
        "text": text,
        "embedding": embed_text(text),
    })

print(f"Knowledge base built with {len(knowledge_base)} documents.")
```

---

### Step 5 — Define the Retrieval Function

To find the most relevant document(s) for a question, the question is embedded the same way the documents were, then compared to every document's embedding using cosine similarity — a higher score means a closer match.

```python
def cosine_similarity(a, b):
    # Standard cosine similarity: dot product over the product of magnitudes
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def retrieve(query, top_k=2):
    """Return the top_k most relevant documents for the query, most relevant first."""
    query_embedding = embed_text(query)

    scored = []
    for doc in knowledge_base:
        score = cosine_similarity(query_embedding, doc["embedding"])
        scored.append({**doc, "score": float(score)})

    scored.sort(key=lambda d: d["score"], reverse=True)
    return scored[:top_k]
```

**What's happening here, step by step:**
1. The question is turned into an embedding, the same way each document was.
2. Cosine similarity is computed between the question and every document in the knowledge base.
3. The documents are sorted by score, highest first.
4. The top `top_k` documents are returned, each still carrying its similarity score.

---

### Step 6 — Combine Retrieved Documents and Ask Gemini, With Citations

This ties retrieval and generation together — it calls the retrieval function, labels each retrieved document clearly (e.g. `[Source: simple-invoice.png]`), and tells Gemini to tag every fact it uses with the document it came from. That tag is what makes the explainability check in Step 8 possible without needing a separate pass just to figure out what was used.

```python
def rag_answer(query, top_k=2):
    retrieved_docs = retrieve(query, top_k=top_k)

    # Label each document so Gemini can cite exactly which one it used
    labeled_context = "\n\n".join(
        f"[Source: {doc['source']}]\n{doc['text']}" for doc in retrieved_docs
    )

    prompt = f"""You are an assistant that answers questions about invoices/receipts using ONLY the context below.
Every fact you state must be tagged with its source, like [Source: filename].
If the answer isn't in the context, say "Not found in the provided documents."

Context:
{labeled_context}

Question: {query}
Answer:"""

    response = client.models.generate_content(model=CHAT_MODEL, contents=prompt)
    return response.text, retrieved_docs
```

---

### Step 7 — Ask a Question

```python
query = "What is the invoice number and total charge on the Contoso invoice?"

answer, retrieved_docs = rag_answer(query)

print("--- DOCUMENTS RETRIEVED ---")
for doc in retrieved_docs:
    print(f"{doc['source']}  (similarity: {doc['score']:.3f})")

print("\n--- ANSWER ---")
print(answer)
```

A good test question, because the answer lives entirely inside one document (`simple-invoice.png`) — a clean, single-document lookup that also shows retrieval correctly ignoring the receipt and purchase order.

---

### Step 8 — See Why Each Document Was Used

For every document the lab checked, this prints its similarity score, whether it was actually cited in the answer, and — asking Gemini directly — why it mattered.

Unlike a rough guess, the "was it used" check here is exact: it looks for the citation tag itself (e.g. `[Source: simple-invoice.png]`) inside the final answer, so it only counts a document as used if Gemini actually cited it.

```python
print("\n--- EXPLAINABILITY ---")
for doc in retrieved_docs:
    # Check if the citation tag is actually present in Gemini's answer
    was_used = f"[Source: {doc['source']}]" in answer

    status = "USED in answer" if was_used else "retrieved but NOT used"

    print(f"\nDocument: \"{doc['source']}\"")
    print(f"similarity: {doc['score']:.3f} | {status}")

    # Ask Gemini why this document is relevant, using the actual text that was retrieved
    explain_prompt = f"""
In 3-4 short lines, explain why the document below is relevant to the question.
Be specific -- mention the actual numbers or fields that connect to the question.
Do not repeat the question. Do not add extra commentary.

Question: {query}

Document source: {doc['source']}
Document content: {doc['text']}
"""
    explanation_response = client.models.generate_content(model=CHAT_MODEL, contents=explain_prompt)
    print(f"Why: {explanation_response.text.strip()}")
```

---

### Step 9 — Simple Interactive Chatbot (Optional)

A minimal chat loop over the same `rag_answer` function, so you can ask follow-up questions about any of the three documents without re-running earlier cells.

```python
while True:
    question = input("Ask about your invoices (or 'exit'): ").strip()
    if question.lower() == "exit":
        print("Goodbye!")
        break

    answer, retrieved_docs = rag_answer(question)
    sources = ", ".join(doc["source"] for doc in retrieved_docs)
    print(f"\n[Retrieved: {sources}]")
    print(answer)
    print()
```

---

# What We Learnt

This lab turns scanned invoices into something you can actually query, and checks — with proof — exactly which documents ended up in the final answer.

- **Layout is preserved during OCR** — text is read using its position on the page, not just detected in whatever order the engine happens to find it, so rows and columns stay meaningfully together.
- **Retrieval needs no vector database** — with a small set of short documents, one embedding per document and plain cosine similarity is enough to find the right match.
- **Every fact in the answer is tagged to its document** — Gemini is told to cite `[Source: filename]` for every fact it uses.
- **The "was it used" check is exact, not a guess** — it looks for the actual citation tag in the answer, so there's no ambiguity about which documents mattered.
- **The sample documents are downloaded automatically** — no need to have them saved on your computer beforehand.
