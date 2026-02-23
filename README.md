# GovPreneurs — Auto‑Proposal Engine (AI Proposal Drafting)

Live frontend: `https://proposal-ai-one.vercel.app/`

This project helps a small business go from **finding a government opportunity** to **generating + refining a proposal draft** quickly, with **citations** for trust and a **PDF export** for submission-ready output.

---

## Architecture (high level)

### Core components

- **Frontend** (`react-frontend/`): React + TypeScript + Vite UI
  - Login via **companyId** (demo auth)
  - Opportunity browsing + “Apply”
  - Proposal review UI with **inline citations** that jump to evidence
  - Iterative “Refine draft” loop
  - “Download PDF” (final PDF strips citations)

- **Backend** (`govproject-backend/`): FastAPI
  - MongoDB for opportunities, user profiles, and chunk text/metadata
  - Pinecone for vector search (RAG)
  - Gemini for embeddings + proposal generation + refinement

### Data / AI flow

1. **Sync opportunities (SAM.gov → MongoDB)**
   - Pull opportunities from SAM.gov search API and upsert by `noticeId`
   - Stored in MongoDB `opportunities`
   - See `govproject-backend/docs/PART1_DATA_INTEGRATION.md`

2. **Fetch full notice description**
   - Each opportunity has a `description` URL (SAM.gov “noticedesc” endpoint)
   - Backend fetches the full text using `SAM_API_KEY` and injects it into the LLM context

3. **Ingest attachments for RAG (downloads → chunk → embed)**
   - Attachments are in `resourceLinks[]`
   - Downloaded under `govproject-backend/downloads/<noticeId>/`
   - Parsed + chunked (structure-aware, token-limited), stored in MongoDB, embedded into Pinecone
   - Dedup: if chunks already exist for the latest version, ingestion is skipped
   - See `govproject-backend/docs/CHUNKING_STRATEGY.md`

4. **Retrieve evidence (Pinecone → MongoDB)**
   - Query Pinecone with `noticeId` filter + a requirements-focused query
   - Fetch full chunk text from MongoDB for **citations**

5. **Generate draft + citations (Gemini)**
   - LLM receives: solicitation metadata + full description text + retrieved chunks + firm profile
   - Prompt requires inline citations like `[1] [2] ...` mapping to retrieved sources

6. **Review + refine loop**
   - Users can submit refinement prompts repeatedly until satisfied
   - If the refinement request is unclear, the model returns `CLARIFICATION_NEEDED: ...`

7. **Export PDF**
   - Backend generates a PDF from the current draft text
   - PDF output **removes citations** for a clean, professional deliverable

---

## Repo layout

- `govproject-backend/`
  - `main.py` (FastAPI app + CORS)
  - `api/` (routes)
  - `services/proposal_service.py` (RAG + prompts + draft/refine)
  - `services/pdf_generator.py` (PDF export)
  - `rag/` (ingest, chunk, retrieve)
  - `docs/` (architecture + chunking + citations docs)
- `react-frontend/`
  - `src/lib/api.ts` (API client)
  - `src/pages/Opportunities.tsx` (list + attachment count)
  - `src/pages/ProposalReview.tsx` (draft UI, refine loop, citations, PDF download)

---

## Environment variables

### Backend (`govproject-backend/.env`)

- `MONGO_URL` — MongoDB connection string
- `GEMINI_API_KEY` — Gemini API key
- `PINECONE_API_KEY` — Pinecone API key
- `SAM_API_KEY` — SAM.gov public API key (used to fetch full notice description text)

### Frontend (`react-frontend/.env`)

- `VITE_API_URL` — Backend base URL (example: `http://127.0.0.1:8000`)

---

## Run locally (quick)

### Backend

From `govproject-backend/`:

- Install deps: `pip install -r requirements.txt`
- Start API: `python -m uvicorn main:app --reload --port 8000`

### Frontend

From `react-frontend/`:

- Install deps: `npm install`
- Start dev server: `npm run dev`

---

## Deploy

### Frontend (Vercel)

- Set `VITE_API_URL` to your backend URL
- Deploy `react-frontend/`

### Backend (Render)

- **Root Directory**: `govproject-backend`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Set env vars: `MONGO_URL`, `GEMINI_API_KEY`, `PINECONE_API_KEY`, `SAM_API_KEY`

---

## Extra docs

- `govproject-backend/docs/PART1_DATA_INTEGRATION.md`
- `govproject-backend/docs/PART2_RAG_AND_PROMPT.md`
- `govproject-backend/docs/CHUNKING_STRATEGY.md`
- `govproject-backend/docs/CITATIONS_SYSTEM.md`

