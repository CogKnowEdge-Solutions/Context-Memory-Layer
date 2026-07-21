# Lab 1 Guide: Automated Ingestion (Building Structured Knowledge)

---

## 1. What is an LLM Wiki?

**LLM** stands for **Large Language Model** — an AI system that is very good at reading and writing natural language. It can read a document and summarize or restructure what's inside it.

**Wiki** refers to something like Wikipedia — a collection of short, focused pages, where each page explains exactly one topic, supported by an index that helps locate the right page quickly.

An **LLM Wiki** combines the two ideas: it is a Wikipedia-style knowledge base that is built and read by an AI. Instead of a person writing each page by hand, the AI reads the source material and generates the pages. Instead of a person browsing to find the right page, the AI searches the index and reads the relevant page when it needs to answer a question.

---

## 2. What is OKF (Open Knowledge Format)?

If an AI is going to generate knowledge pages automatically, there needs to be one consistent format for what a page looks like. That is what **OKF (Open Knowledge Format)** defines — a simple, consistent structure that every knowledge file follows.

Every OKF file has **two layers**:

1. **Metadata Layer** — short facts about the page: its title, type, tags, and a one-line description. This layer exists so the AI (or a person) can quickly judge relevance without reading the entire file.
2. **Content Layer** — the full explanation itself.

```mermaid
graph TD
    A["OKF File"] --> B["Metadata Layer<br/>title, type, tags, description<br/>-- quick to scan --"]
    A --> C["Content Layer<br/>the full explanation<br/>-- read fully when needed --"]

    classDef metaStyle fill:#e7f1ff,stroke:#1d6fa5,stroke-width:1px,color:#0b1f33
    classDef contentStyle fill:#e9f9ee,stroke:#2f8d46,stroke-width:1px,color:#0b3d2e
    classDef rootStyle fill:#ffffff,stroke:#333333,stroke-width:1px,color:#111111

    class A rootStyle
    class B metaStyle
    class C contentStyle
```

These two layers are kept separate because they serve different purposes. The metadata is meant to be scanned quickly to decide whether a page is relevant. The content is meant to be read in full, but only once the metadata has already confirmed relevance.

As an example, this guide itself follows the same idea. If it were stored as an OKF file, its metadata layer would look like this:

```yaml
title: "Lab 1 Guide: Automated Ingestion (Building Structured Knowledge)"
type: "guide"
tags: ["llm-wiki", "okf", "lab1", "ingestion", "groq"]
description: "A step-by-step walkthrough of the Lab 1 notebook: what an LLM Wiki and OKF are, why this approach is used, and what every part of the code does."
```

Everything below that — the explanations, code walkthroughs, and diagrams that follow — is the content layer.

---

## 3. Why Use This Approach

A common way AI tools handle large documents is to split them into small, randomly-sized chunks, then retrieve a handful of chunks that appear similar to a given question. This has a well-known weakness: chunking can separate a fact from the context that explains it, and "appears similar" is not the same as "actually answers the question." When the retrieved chunks don't fully cover the answer, the AI tends to fill the gap with a guess — commonly referred to as **hallucination**.

This workshop avoids that problem by generating one complete, self-contained file per fact or concept, along with a master index describing what exists. When a question is asked later, the AI does not guess from fragments — it checks the index, selects the correct file(s), and reads them in full.

Lab 1 is where this structured knowledge base gets created, starting from a single unstructured PDF.

---

## 4. Pipeline Overview

```mermaid
flowchart LR
    A["Messy PDF<br/>SunFactSheet.pdf"] --> B["Extract raw text<br/>using PyPDF2"]
    B --> C["Send text to Groq<br/>with strict instructions"]
    C --> D{"Valid JSON<br/>returned?"}
    D -- No --> E["Print error<br/>concepts = empty list"]
    D -- Yes --> F["Loop through<br/>every concept"]
    F --> G["Write one .md file<br/>per concept"]
    G --> H["Append one line<br/>to index.md"]
    H --> I["output_wiki/ folder<br/>of structured OKF files"]

    classDef defaultStyle fill:#ffffff,stroke:#333333,stroke-width:1px,color:#111111
    class A,B,C,D,E,F,G,H,I defaultStyle
```

The pipeline takes an unstructured PDF as input and produces a folder of clean, indexed OKF files as output. The rest of this guide walks through the notebook that implements this pipeline, cell by cell.

---

## 5. Code Walkthrough

### Step 1 — Install Required Libraries

```python
# !pip install PyPDF2 python-dotenv groq requests
```

This line is commented out because it only needs to run once, during initial setup — not every time the notebook runs. Each library serves a specific purpose:

- **PyPDF2** — opens a PDF file and extracts its plain text.
- **python-dotenv** — reads secret values (such as an API key) from a hidden `.env` file, instead of hardcoding them into the notebook.
- **groq** — the official library used to communicate with Groq's AI models.
- **requests** — a general-purpose library for making internet requests, used internally by some of the other libraries.

### Step 2 — Import Libraries

```python
import os
import json
import PyPDF2
from dotenv import load_dotenv
from groq import Groq
```

Installing a library makes it available on the machine. Importing it brings it into this specific notebook so it can be used.

| Import | Purpose |
|---|---|
| `os` | Working with file paths and folders |
| `json` | Converting JSON-formatted text into a Python dictionary/list |
| `PyPDF2` | Opening the PDF and reading its pages |
| `load_dotenv` | Reading values from the `.env` file |
| `Groq` | The client used to send requests to the AI |

### Step 3 — Set Up API Keys

```python
load_dotenv("../.env")

# Initialize the Native Groq Client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
```

- This cell loads the secret Groq API key from a hidden `.env` file, and uses it to open a connection to the AI.
- That connection is stored in `client`, which every later call to the AI will use.
- Keeping the key in a separate `.env` file — instead of typing it directly into the notebook — means the key stays private even if the notebook itself is shared.

### Step 4 — Locate and Read the Document

```python
PDF_PATH = "../SunFactSheet.pdf"

if os.path.exists(PDF_PATH):
    print(f"Success: Found the document at '{PDF_PATH}'")
else:
    print(f"Error: Could not find the document.")

reader = PyPDF2.PdfReader(PDF_PATH)
raw_text = ""
for page in reader.pages:
    raw_text += page.extract_text() + "\n"

print("Text extraction complete! Ready for AI processing.")
```

- This cell first checks that the PDF actually exists at the given location, so the notebook fails with a clear message instead of a confusing crash.
- It then opens the PDF and reads through every page, collecting all the text into one variable, `raw_text`.
- By the end of this cell, the entire PDF exists as one plain block of text — nothing has been summarized yet, it's just been pulled out of the PDF.

### Step 5 — Extract Concepts with Groq

```python
system_prompt = """
You are a data extraction assistant. Read the text below and extract every distinct technical fact or value present in the source.
Do not limit yourself to a fixed number of facts — extract all of them, no matter how many there are.
Use the same wording as the source text for each fact — do not paraphrase or rename values.
Each fact must have its own separate concept entry, even if two facts are about a related topic.
Keep each "content" field short — 1 to 2 sentences maximum, stating only the fact and its value.
Respond in JSON only, matching this format:
{
  "concepts": [
    {
      "filename": "concept_name.md",
      "type": "concept",
      "title": "Human Readable Title",
      "tags": ["tag1", "tag2"],
      "description": "A single sentence summary",
      "content": "The full detailed explanation in markdown format."
    }
  ]
}
Output ONLY the JSON. No extra text, no markdown formatting blocks.
"""

print("Sending document to Groq for extraction...")

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile", 
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": raw_text}
    ],
    temperature=0.0,
    max_tokens=8000
)

raw_json = response.choices[0].message.content.strip()

try:
    structured_data = json.loads(raw_json)
    concepts = structured_data.get("concepts", [])
    print(f"Success! AI identified {len(concepts)} distinct concepts.")
except json.JSONDecodeError:
    print("Error: The model's JSON response was cut off or malformed.")
    print("Try reducing the amount of source text, or check the raw output below:")
    print(raw_json[-500:])
    concepts = []
```

This is the heart of the lab, so it helps to think of it in three parts:

- **The instructions.** The notebook first writes out strict instructions telling the AI to extract every fact from the text, keep the original wording, and reply with pure JSON — nothing else.
- **The request.** It then sends the PDF text along with those instructions to the AI, asking it to stay as factual and consistent as possible rather than creative, and giving it enough room in its reply to list out a large number of facts.
- **Reading the reply.** Finally, it takes the AI's answer and converts it from plain text into an actual usable list of facts, `concepts`. If the AI's reply comes back broken or incomplete, this step catches the problem instead of letting the notebook crash, and simply continues with an empty list.

By the end of this cell, every fact the AI found exists as its own small entry, ready to be turned into files.

### Step 6 — Build OKF Files and Update the Index

This step is split across two cells. The diagram below shows what the second cell does before we look at it.

```mermaid
flowchart TD
    A["Start loop: next concept"] --> B["Build filename and file path"]
    B --> C["Write concept file<br/>mode: w"]
    C --> D["Append summary line to index.md<br/>mode: a"]
    D --> E{"More concepts<br/>remaining?"}
    E -- Yes --> A
    E -- No --> F["Result: one .md file per concept<br/>plus one complete index.md"]

    classDef defaultStyle fill:#ffffff,stroke:#333333,stroke-width:1px,color:#111111
    class A,B,C,D,E,F defaultStyle
```

**Cell A — Preparing the output folder and index file:**

```python
output_dir = "../output_wiki"
os.makedirs(output_dir, exist_ok=True)

index_path = os.path.join(output_dir, "index.md")

if not os.path.exists(index_path):
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("# Master Index\n\n")

print(f"Output directory ready at: {output_dir}")
```

- This cell makes sure the `output_wiki` folder exists, creating it if it's the first run.
- It also starts the master index file if one doesn't already exist, without overwriting one from a previous run.

**Cell B — Generating the files:**

```python
for concept in concepts:
    filename = concept['filename'].replace(" ", "_").lower()
    if not filename.endswith('.md'):
        filename += '.md'
        
    file_path = os.path.join(output_dir, filename)
    
    okf_content = f"""type: {concept['type']}
title: {concept['title']}
tags: {concept['tags']}
description: {concept['description']}
---
# {concept['title']}

{concept['content']}
"""
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(okf_content)
    
    print(f"Created: {filename}")
    
    with open(index_path, "a", encoding="utf-8") as f:
        f.write(f"- **{filename}**: {concept['description']}\n")

print("\nPipeline complete! Ready for Lab 2.")
```

- This loop runs once for every fact in `concepts`.
- For each one, it cleans up the filename, builds the OKF-formatted content, and saves it as its own `.md` file.
- Right after saving, it adds one line about that fact to the master index — so the index grows alongside the files, without ever being rewritten from scratch.
- Once the loop finishes, `output_wiki/` holds one file per fact, plus a complete `index.md` listing all of them.

---

## 6. Expected Output

When the notebook runs successfully, the final cell should print output similar to:

```
Created: sun_mass.md
Created: earth_mass.md
Created: sun_to_earth_mass_ratio.md
...
Created: sun_photosphere_composition.md

Pipeline complete! Ready for Lab 2.
```

The `output_wiki/` folder should then contain one `.md` file per extracted fact, along with an `index.md` listing each file with its description.

---

## 7. Summary

By the end of Lab 1, an unstructured PDF has been converted into a folder of clean, consistently formatted OKF files, along with a master index describing all of them — generated automatically. This structured knowledge base, along with its master index, is the complete output of this lab.