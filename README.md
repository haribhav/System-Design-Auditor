# System Design Reviewer

A standalone production-oriented audit API for reviewing system design documents using retrieval-augmented analysis (RAG) and modular reviewers. This is an **audit tool**, not a conversational chatbot.

## Features
- FastAPI backend on Python 3.11
- PDF ingestion with `PyPDFLoader` preserving page metadata
- Persistent local Chroma vector store (`data/chroma`)
- Token-budgeted retrieval (`<=900` chars/chunk, `<=6000` chars total context)
- Triage + targeted/deep module reviewers
- Deterministic overall scoring and confidence (no LLM scoring merge)
- Structured JSON logging with request IDs and latency

## Project structure

```
app/
  main.py
  config.py
  logging_setup.py
  ingest.py
  store.py
  retrieval.py
  prompts.py
  reviewers.py
  scoring.py
  models.py
data/chroma/
data/uploads/
requirements.txt
Dockerfile
.env.example
README.md
```

## Setup

1) Create and activate a Python 3.11 virtualenv.
2) Install dependencies:

```bash
pip install -r requirements.txt
```

3) Configure environment:

```bash
cp .env.example .env
# then edit .env with OPENAI_API_KEY and INGEST_TOKEN
```

4) Run locally:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> `GET /health` works without an API key, but `/ingest` and `/analyze` require `OPENAI_API_KEY`.

## API Endpoints

### 1) Health
```bash
curl http://localhost:8000/health
```

### 2) Ingest PDF
```bash
curl -X POST "http://localhost:8000/ingest?collection=default" \
  -H "x-ingest-token: $INGEST_TOKEN" \
  -F "file=@./design.pdf"
```

### 3) List ingested files/chunks
```bash
curl "http://localhost:8000/files?collection=default"
```

### 4) Analyze
```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "default",
    "query": "Review this design for production readiness",
    "mode": "targeted",
    "top_k": 6,
    "file_filter": null,
    "budget_modules": 3
  }'
```

## Modes
- `triage`: one LLM call that returns high-risk areas, missing info, recommended modules, and questions.
- `targeted`: triage first, then runs up to `budget_modules` from recommended modules.
- `deep`: runs a fixed set of 6 core modules.

Modules available:
`security, reliability, scalability, api_contracts, data_consistency, deployment_rollout, cost, testing, tradeoffs`

## Token-saving tips
- Use `file_filter` to restrict analysis to one document.
- Keep `top_k` at 6 (default) unless coverage is low.
- Use `targeted` mode for cost-efficient iteration.
- Use `triage` mode first to identify where deep review is needed.

## Docker

```bash
docker build -t system-design-reviewer .
docker run --rm -p 8000:8000 --env-file .env system-design-reviewer
```

## Notes
- If model output is invalid JSON, the service retries once with stricter formatting instruction.
- Unknowns are expected and should appear in `missing_info`.
