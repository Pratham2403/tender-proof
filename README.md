# TenderProof

A locally-deployable AI platform that automates government tender eligibility evaluation. Upload a tender document and bidder submissions — TenderProof extracts eligibility criteria, evaluates each bidder, and produces a fully explainable, auditable report.

**Core principle:** LLMs parse, a deterministic rule engine judges. No eligibility verdict is ever produced by model inference alone.

---

## How It Works

1. **Upload tender** — Procurement officer uploads a tender PDF/DOCX. Gemini 2.0 Flash extracts all eligibility criteria into a typed `EvaluationSchema`.
2. **Review schema** — Officer reviews and approves (or edits) the extracted criteria before evaluation begins.
3. **Upload bidder submissions** — Multi-file packages (typed PDFs, scanned documents, DOCX, JPG/PNG). Qwen2.5-VL-72B reads each page as an image — no OCR preprocessing.
4. **Automated evaluation** — A pure deterministic rule engine compares each bidder's extracted values against the approved schema. Every verdict cites: criterion → source document → page number → extracted value → rule applied.
5. **Human review queue** — Any extraction with confidence < 0.70 routes to a review queue. Officer confirms or overrides. All overrides are logged.
6. **Consolidated report** — Per-criterion PASS / FAIL / REVIEW verdict for every bidder, with full citation trail.

---

## Architecture

```
Next.js Dashboard  ──REST/WS──►  FastAPI  ──►  Redis  ──►  Celery Worker
                                                                 │
                                              ┌──────────────────┼──────────────────┐
                                              ▼                  ▼                  ▼
                                       Schema Compiler    Vision Extractor     Rule Engine
                                       (Gemini Flash)    (Qwen2.5-VL-72B)    (pure Python)
                                              │                  │                  │
                                              └──────────────────┴──────────────────┘
                                                                 │
                                                            MongoDB + Audit Log
```

| Component | Technology |
|-----------|------------|
| Frontend | Next.js 14 (App Router), TailwindCSS, ShadcnUI |
| Backend API | FastAPI, Python 3.11+, Beanie ODM |
| Task queue | Celery 5.x + Redis |
| Database | MongoDB (Beanie ODM, Pydantic v2) |
| Tender schema compilation | Gemini 2.0 Flash — Google AI Studio free tier |
| Bidder document extraction | Qwen2.5-VL-72B-Instruct — OpenRouter free tier |
| Document conversion | PyMuPDF (PDF → PNG), LibreOffice headless (DOCX → PDF) |

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB (local install or Docker)
- Redis
- LibreOffice (for DOCX support — `sudo apt install libreoffice`)
- [Google AI Studio API key](https://aistudio.google.com/) (free)
- [OpenRouter API key](https://openrouter.ai/) (free)

---

## Setup

### 1. Clone and configure

```bash
git clone <repo-url>
cd tender-proof
cp backend/.env.example backend/.env
```

Edit `backend/.env`:

```env
MONGODB_URL=mongodb://localhost:27017/tenderproof
REDIS_URL=redis://localhost:6379/0
GOOGLE_API_KEY=<your_google_ai_studio_key>
OPENROUTER_API_KEY=<your_openrouter_key>
UPLOAD_DIR=./uploads
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Install frontend dependencies

```bash
cd client
npm install
```

### 4. Start all services

**Terminal 1 — MongoDB:**
```bash
mongod --dbpath ./data/db
```

**Terminal 2 — Backend (Redis + Celery + FastAPI):**
```bash
cd backend
redis-server &
celery -A app.worker worker --loglevel=info &
uvicorn app.main:app --reload --port 8000
```

**Terminal 3 — Frontend:**
```bash
cd client
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

> Shortcut: with MongoDB and Redis already running, `./start.sh` launches the
> Celery worker, FastAPI, and Next.js together.

### 5. (Optional) Load demo data

Pre-populates a demo CRPF tender with 3 bidder submissions (one clean typed PDF, one scanned, one mixed with a photo attachment):

```bash
cd backend
python -m seed.seed
```

---

## Project Structure

```
tenderproof/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── config.py                # Settings (pydantic-settings)
│   │   ├── database.py              # Beanie / MongoDB init
│   │   ├── worker.py                # Celery app factory
│   │   ├── models/                  # MongoDB document models
│   │   ├── schemas/                 # Request/response Pydantic schemas
│   │   ├── routers/                 # FastAPI route handlers
│   │   ├── services/                # Core logic (compiler, extractor, engine, audit)
│   │   ├── tasks/                   # Celery task definitions
│   │   └── ws/                      # WebSocket job progress
│   ├── seed/                        # Demo data loader + mock document generator
│   ├── tests/                       # Unit tests (rule engine, audit chain, converter)
│   └── requirements.txt
└── client/
    ├── app/                         # Next.js App Router pages
    ├── components/                  # UI components
    ├── lib/                         # API client + WebSocket hook
    └── types/                       # Shared TypeScript types
```

---

## Key API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/tenders` | Upload tender, trigger schema compilation |
| `GET` | `/api/tenders/{id}/schema` | Fetch compiled schema for review |
| `PATCH` | `/api/tenders/{id}/schema` | Officer approves / edits schema |
| `POST` | `/api/tenders/{id}/bidders` | Upload bidder documents, trigger extraction |
| `GET` | `/api/tenders/{id}/report` | Fetch consolidated evaluation report |
| `GET` | `/api/tenders/{id}/review` | Fetch human review queue |
| `POST` | `/api/tenders/{id}/review/{item_id}` | Officer confirms or overrides a verdict |
| `GET` | `/api/jobs/{job_id}/status` | Poll job progress |
| `WS` | `/ws/jobs/{job_id}` | Real-time job progress stream |

---

## Verdict Logic

The rule engine applies typed comparisons — never LLM inference:

| Criterion Type | Rule |
|----------------|------|
| `CurrencyThreshold` | `extracted_value >= minimum_crore` |
| `CountMinimum` | `extracted_count >= minimum_count` |
| `BooleanPresence` | Value present and matches accepted list |
| `DateRange` | Date within specified range / not expired |
| `SimilarityScore` | Score ≥ 0.7 → PASS; ≤ 0.4 → FAIL; else → REVIEW |

**Confidence gate:** Any extraction with confidence < 0.70 is routed to `REVIEW` regardless of the rule outcome. A bidder is never silently disqualified.

---

## Audit Trail

Every automated decision and officer action is written to an append-only, hash-chained audit log in MongoDB. Each entry includes a SHA-256 hash of the previous entry — any tampering breaks the chain and is detectable.

Events logged: schema compiled, schema approved, extraction complete, verdict produced, officer override, report finalized.

---

## Production Migration

All components can move to free-tier cloud with only environment variable changes — no code changes:

| Component | Local | Cloud (free tier) |
|-----------|-------|-------------------|
| MongoDB | `mongod` local | MongoDB Atlas M0 |
| Redis | `redis-server` local | Railway Redis |
| Backend | `uvicorn` local | Railway / Render |
| Frontend | `next dev` | Vercel |

---

## Design Decisions

- **MongoDB over PostgreSQL** — EvaluationSchema and BidderProfile are deeply nested, variable-length structures that map naturally to documents. Migration to Atlas = one env-var change.
- **Two LLMs, two jobs** — Gemini Flash (1M token context) handles long tender text; Qwen2.5-VL-72B handles vision-heavy scanned documents. No single free model is best at both.
- **Vision-first, no OCR** — PyMuPDF renders pages to PNG at 150 DPI; Qwen2.5-VL reads images directly. Avoids the 25–30% semantic noise introduced by OCR on real-world scanned documents.
- **Celery + Redis for async** — 200 Vision LLM calls for a 10-bidder tender run in parallel across workers, completing in ~60s vs 600s sequential.
