# VetChat AI

A local MVP veterinary advising chat app that answers pet health questions using citation-first RAG over academic veterinary literature, with emergency red-flag detection before any LLM call.

## Architecture

```
Browser (Next.js 14)
    │  POST /api/chat
    ▼
FastAPI Backend (port 8000)
    ├── 1. EmergencyDetector  ← pure Python, runs BEFORE any LLM call
    ├── 2. Chroma retrieval   ← cosine similarity over ingested chunks
    ├── 3. Cross-encoder rerank
    ├── 4. Citation builder   ← [1], [2] numbered references
    ├── 5. Claude API         ← claude-sonnet-4-6, constrained by system prompt
    └── 6. Disclaimer inject
    │
    ├── ChromaDB (./chroma_store/)   ← local vector store
    └── ScienceDirect API            ← ingestion only (optional)
```

## Prerequisites

- Python 3.11+ (tested with 3.13)
- Node.js 18+ (tested with v24)
- An Anthropic API key (`ANTHROPIC_API_KEY`)
- *(Optional)* A ScienceDirect API key for ingesting real papers

## Quick Start (Offline — mock data only)

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd vetchat-ai

# 2. Set up environment
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY, leave SCIENCEDIRECT_API_KEY blank

# 3. Install backend dependencies
cd backend
pip install -r requirements.txt

# 4. Seed mock data (no API key required)
python scripts/seed_mock_data.py --chroma-path ./chroma_store

# 5. Start the backend
uvicorn app.main:app --reload --port 8000

# 6. In a new terminal — start the frontend
cd ../frontend
npm install
npm run dev
```

Open http://localhost:3000

## Ingesting Real ScienceDirect Papers (Online)

```bash
cd backend
python scripts/ingest_sciencedirect.py \
    --queries "veterinary xylitol toxicology" \
              "canine chocolate toxicity" \
              "feline respiratory distress" \
              "small animal dermatology pruritus" \
    --count 25 \
    --chroma-path ./chroma_store
```

## Running Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest tests/ -v --tb=short
```

All tests run fully offline — Claude is mocked, Chroma uses an in-memory instance.

## Test Coverage

| Test file | What is tested |
|-----------|---------------|
| `test_emergency_detector.py` | 20 cases: xylitol, chocolate, grapes, respiratory, cardiovascular, neurological, trauma; case-insensitivity; false-positive avoidance; hotline presence |
| `test_retriever.py` | Relevant queries return chunks; metadata shape; empty collection; n_results limit |
| `test_claude_service.py` | Citation in answer; no-literature response; missing API key error; model selection; system prompt presence |
| `test_chat_endpoint.py` | Emergency short-circuits LLM; emergency response shape; normal query 200; disclaimer present; missing key → 503; ingest without ScienceDirect key → 503 |
| `test_ingestion.py` | Chunker token budget; overlap; mock seed; idempotency; JSON validity; missing ScienceDirect key error; HTTP 429 handling |

## Offline vs Online

| Feature | No `SCIENCEDIRECT_API_KEY` | With `SCIENCEDIRECT_API_KEY` |
|---------|--------------------------|------------------------------|
| Emergency detection | ✅ | ✅ |
| Chat answers | ✅ (mock data) | ✅ (real papers) |
| Citations | Mock abstract-style | Real DOIs + journals |
| `POST /ingest` | ❌ Returns 503 | ✅ |
| All tests | ✅ | ✅ |

## API Reference

### `POST /chat`
```json
{ "query": "my dog has itchy skin" }
```
Response:
```json
{
  "answer": "Canine atopic dermatitis is characterized by... [1]",
  "citations": [{"ref": 1, "title": "...", "journal": "...", "year": 2023, "doi": "...", "url": "..."}],
  "emergency": false,
  "resources": [],
  "disclaimer": "VetChat AI provides..."
}
```

Emergency response:
```json
{
  "emergency": true,
  "category": "toxicology",
  "matched_term": "xylitol",
  "answer": "This sounds like a potential poisoning emergency...",
  "resources": ["ASPCA Animal Poison Control: (888) 426-4435", ...],
  "citations": []
}
```

### `POST /ingest`
Requires `SCIENCEDIRECT_API_KEY` set.
```json
{ "queries": ["veterinary xylitol toxicology"], "count": 25 }
```

### `GET /health`
```json
{ "status": "ok", "version": "0.1.0" }
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | — | App refuses to start without this |
| `SCIENCEDIRECT_API_KEY` | No | `""` | Leave blank for offline mode |
| `USE_MOCK_DATA` | No | `true` | Auto-seed Chroma on startup if empty |
| `CHROMA_PATH` | No | `./chroma_store` | ChromaDB persistence path |
| `CLAUDE_MODEL` | No | `claude-sonnet-4-6` | Can also use `claude-haiku-4-5-20251001` |
| `USE_RERANKER` | No | `true` | Set false to skip cross-encoder rerank |
| `EMBEDDING_MODEL` | No | `all-MiniLM-L6-v2` | Sentence-transformers model |

## Mock Data

Three categories of veterinary content in `backend/data/mock/`:

- **toxicology.jsonl** — xylitol, chocolate methylxanthines, grapes/raisins, allium, acetaminophen
- **respiratory.jsonl** — feline asthma, BOAS, pleural effusion, canine pneumonia
- **dermatology.jsonl** — canine atopic dermatitis, Malassezia, pyoderma, feline miliary dermatitis

Each record mimics a real academic abstract with plausible DOIs, journals, and authors for realistic citation testing.

## Docker

```bash
docker-compose up --build
```

Backend on port 8000, frontend on port 3000.
