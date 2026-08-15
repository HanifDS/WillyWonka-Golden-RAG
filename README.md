# Wonka Industries RAG

<p align="center">
  <img src="docs/willy-wonka-banter.png" alt="Wonka — synthetic founder, real RAG" width="280">
</p>
<p align="center"><em>End to End RAG Project utilising Amazon Bedrock's managed Knowledge Base.</em></p>

A small end-to-end RAG project that uses **Amazon Bedrock’s managed Knowledge Base** instead of a homemade chunker and vector database. The goal was to show how in a production environment one could ingest from S3, chunked and vectorised by Knowledge base managed by AWS, and finally be queried from a thin FastAPI app.

The advantage of using a managed Knowledge Base is that one can focus on the retrieval and generation of the answer, while the underlying infrastructure is managed by AWS with the added benefit of being able to scale the infrastructure as needed whilst maintaining security and compliance..

I did not build OpenSearch, FAISS, or a splitting pipeline in for this repo. Bedrock Knowledge Base does the chunking, embeddings, and hybrid search. This app only **retrieves** from that service and asks **Amazon Nova Lite** to write an answer the user can read. Nova Lite was chosen as it is a cheap model that is great for prototype and development purposes.

```
S3 bucket  wonka-industries-rag-data   (source of truth)
        ↓  one-time ingest in AWS
Bedrock managed Knowledge Base A30YI231W3
        ↓  Retrieve (managed search)
FastAPI  →  Nova Lite (amazon.nova-lite-v1:0)
        ↓
Browser UI at http://127.0.0.1:8000/
```


## What was done

1. **Put a company corpus in S3.** Bucket `wonka-industries-rag-data` in `us-east-1` holds 29 markdown files. They are **synthetic** (Wonka is fictional) but they are written like the mix a real firm would dump into a shared drive: policies, board packs, product specs, incident reports, contracts, training.
2. **Let a managed service index them.** A Bedrock “quick start” Knowledge Base ingested that bucket. AWS owns chunking, embeddings, and retrieval. 
3. **Query that index from Python.** `scripts/s3_sync.py` can list or copy objects; `src/rag.py` calls `Retrieve` with `managedSearchConfiguration` (required for a managed KB), then `Converse` on Nova Lite.
4. **Wrap it in FastAPI.** A local UI at `/` asks a question; `/ask` returns JSON. Same path as the CLI (`scripts/ask_kb.py`).

## The S3 corpus: synthetic, but company-shaped

None of this is real data. Willy Wonka would I do apologise. It is a **made-up but realistic** intranet: named roles, document IDs, dates, “CONFIDENTIAL” markings, and facts that **repeat across files** (headcount 3,200, founded 1962) the way a real handbook, annual report, and board minutes would overlap.

That overlap is deliberate. A managed RAG system should find the right *kind* of document (precision) and, when a number lives in more than one place, not miss the extras (recall). A single Wikipedia-style page would not test that.


About 29 objects in S3, all markdown, all fake, all in the shape of SharePoint-or-S3 company dump: **policies, minutes, specs, incidents, contracts, training**. That mix is the experiment. A managed Knowledge Base has to search across those types; Nova Lite has to answer only from what came back — including saying it does not know.

## What you see in the UI

The header portrait is the same Wonka illustration as at the top of this README. The questions below are the live app at `http://127.0.0.1:8000/`.

![How many people work at the company](docs/screenshots/ask-headcount.png)

![How many days of annual leave](docs/screenshots/ask-annual-leave.png)

![What are the public holidays](docs/screenshots/ask-public-holidays.png)

![Hallucination check: boxing weight class](docs/screenshots/ask-boxing-weight-class.png)

## Why Nova Lite (and RAGAS)

The **question / answer** step uses Nova Lite on purpose.  For a small managed-KB demo, a cheap writer is enough: RAGAS is scoring whether the answer **stuck to retrieved chunks**, **addressed the question**, and whether retrieval **picked the right documents** — not whether the prose sounds like a frontier model.

If Nova Lite stays faithful on in-corpus HR facts and refuses out-of-corpus nonsense, the pipeline is testable. Spending more on the writer would not fix a bad retrieve.

## Evaluating answers with RAGAS

The standard framework for this is **RAGAS**. It scores a RAG system on four metrics:

| Metric | Question it asks |
|---|---|
| **Faithfulness** | Did the answer stick to the retrieved context? |
| **Answer relevance** | Did it actually address the question? |
| **Context precision** | Did retrieval find the *right* chunks? |
| **Context recall** | Did it find *all* the relevant chunks? |

These UI tests map onto that:

**1. “How many people work at the company”** — grounded fact.  
“Approximately 3,200 staff across all divisions” is in `employee_handbook.md` (and again in board minutes / the annual report). High **faithfulness** and **answer relevance**. Hitting the handbook is **context precision**; **context recall** is only complete if the other 3,200 mentions came back too.

**2. “How many days of annual leave can I take this year”** — two regimes, one question.  
Nova Lite split **28 days + bank holidays** (full-size staff) vs **35 days + Loompa cultural holidays** (Oompa Loompa framework). That is the handbook *and* `oompa_loompa_employment_framework.md`. Strong **answer relevance** (it did not pick only one contract) and a **context recall** win: both employment docs matter.

**3. “What are the public holidays”** — the parallel calendar.  
Loompa New Year, Festival of the Cacao Bean, Ancestors’ Day, plus OLWC-designated days, sit in the Oompa Loompa framework. Faithful to that file; it did not invent UK bank-holiday names that are not listed there.

**4. “What weight class does Willy Wonka box at?”** — hallucination check.  
Nothing in the corpus is about boxing. The model said it does not have that information. That is the **faithfulness** behaviour we want: cheaper Nova Lite still refused to invent a division. **Answer relevance** holds because it addressed the question by saying the KB does not contain it.

Together: Nova Lite is cheap enough to run these checks often, and still good enough for RAGAS — it answers from Wonka docs when the facts are there, and it does not hallucinate when they are not.

## 1. Activate the environment

This project uses a conda env at `.venv` (not a `venv` activate script):

```bash
conda activate /Users/HanifDS/Documents/AIProjects/RAGProject/WillieWonka/.venv
```

From the project root you can also use:

```bash
conda activate "$(pwd)/.venv"
```

Cursor should also pick up `.venv` automatically.

## 2. Add your API keys

Copy values into `.env` (already created, gitignored):

- **AWS / boto3** — fill `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`, **or** leave them blank and use `~/.aws/credentials`
- Sandbox IAM is used for S3 and Knowledge Base Retrieve
- Generation model is `amazon.nova-lite-v1:0`

Then confirm everything loads:

```bash
python scripts/check_setup.py
```

## 3. S3 source documents

The project bucket is `wonka-industries-rag-data` in `us-east-1`. S3 uses IAM, not the Bedrock API key.

```bash
python scripts/s3_sync.py              # list objects
python scripts/s3_sync.py --download   # copy into data/raw/
```

## 4. Run the app

CLI:

```bash
python scripts/ask_kb.py "What is the everlasting gobstopper?"
python scripts/ask_kb.py --chunks "What is the everlasting gobstopper?"
```

API + webpage:

```bash
uvicorn src.api:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/ for the UI.

`/ask?q=...` returns raw JSON (for programs, not a page). Interactive API docs: http://127.0.0.1:8000/docs

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the everlasting gobstopper?"}'
```
