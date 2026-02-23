# GovPreneurs Auto-Proposal Engine — Architecture & Flow Documentation

**Video Demo:** [Watch the Loom video](https://www.loom.com/share/0de827df32204824bcb708a3252fda2b)

**Live Prototype:**
- Frontend: https://proposal-ai-one.vercel.app/
- Backend: https://proposal-ai.onrender.com

---

## Overview

This document explains how the Auto-Proposal Engine works: **Data Schema**, **Ingestion Strategy**, **RAG Logic**, and **Prompt Engineering**. The system helps small businesses generate government contract proposals in under 10 minutes by automatically matching RFP requirements to company capabilities.

---

## 1. Data Schema Choices

### Why MongoDB + Pinecone?

**MongoDB** (Document Database):
- Stores **full text** of chunks for citations
- Stores **opportunities** (from SAM.gov) and **user profiles** (company info)
- Fast lookups by `noticeId` and `companyId`
- Handles nested documents (past performance, contact info)

**Pinecone** (Vector Database):
- Stores **embeddings** (vector representations) of chunks
- Enables **semantic search** (finds similar meaning, not just keywords)
- Fast similarity search across millions of chunks
- Stores **minimal metadata** (saves space, improves performance)

**Why Both?**
- **Pinecone** finds relevant chunks quickly via semantic search
- **MongoDB** provides full text for citations and display
- Separation of concerns: search vs. storage

### Schema Structure

#### MongoDB Collections

**1. `opportunities` Collection**
```json
{
  "noticeId": "f85ff581f08d4d408ae0214beb569d95",  // Primary key
  "title": "MSHA Altair Gas Monitors",
  "solicitationNumber": "1605C4-26-Q-00021",
  "postedDate": "2024-01-15",
  "responseDeadLine": "2024-02-20",
  "type": "Solicitation",
  "typeOfSetAsideDescription": "SDVOSB",
  "naicsCodes": ["541511", "541611"],
  "description": "https://api.sam.gov/...",  // URL to fetch full description
  "resourceLinks": ["https://.../RFP.pdf", "https://.../SOW.pdf"],  // Attachments
  "active": "Yes",
  "ingestedAt": "2024-01-15T10:00:00Z"
}
```

**2. `user_profiles` Collection**
```json
{
  "companyId": "sg-security-001",  // Primary key
  "companyName": "SafeGuard Security",
  "naicsCodes": ["541511", "541611"],
  "capabilities": ["IT Services", "Cybersecurity"],
  "certifications": ["Small Business", "SDVOSB"],
  "capabilitiesStatement": "Our company provides...",
  "setAsideType": "SDVOSB",
  "pastPerformance": [
    {
      "projectName": "Cybersecurity Assessment",
      "client": "Department of Defense",
      "description": "Performed security audits...",
      "projectValue": "$500,000",
      "year": "2023",
      "keywords": ["cybersecurity", "audit", "compliance"]
    }
  ],
  "contact": {
    "fullName": "John Doe",
    "email": "john@example.com"
  }
}
```

**3. `chunks` Collection** (RAG chunks from RFP attachments)
```json
{
  "chunk_id": "noticeId_filename_0",  // Primary key
  "noticeId": "f85ff581f08d4d408ae0214beb569d95",
  "filename": "RFP_Section2.pdf",
  "text": "The contractor shall provide 24/7 support...",  // Full text
  "section_name": "SECTION 2: REQUIREMENTS",
  "section_type": "requirement",  // requirement/specification/evaluation_criteria/etc.
  "is_critical": true,
  "requirement_flag": true,  // Contains "shall", "must", "required"
  "is_table": false,
  "chunk_index": 0,
  "amendment_number": 0,  // 0 = original, 1+ = amendments
  "is_latest_version": true  // Only latest chunks are retrieved
}
```

#### Pinecone Index

**Metadata Only** (no full text):
```json
{
  "chunk_id": "noticeId_filename_0",
  "noticeId": "f85ff581f08d4d408ae0214beb569d95",
  "filename": "RFP_Section2.pdf",
  "section_type": "requirement",
  "is_critical": "true",
  "requirement_flag": "true"
}
```

**Why This Design?**
- **Full text in MongoDB**: Needed for citations and display (can't fit in vector DB metadata)
- **Metadata in Pinecone**: Enables filtering by `noticeId`, `section_type`, `requirement_flag`
- **Embedding vector**: Stored separately in Pinecone for semantic search

---

## 2. Ingestion Strategy

### Overview

When a user applies to an opportunity, the system:
1. Downloads RFP attachments (PDFs, XLSX, TXT)
2. Parses them into text
3. Chunks them intelligently (structure-aware, token-based)
4. Stores full text in MongoDB
5. Embeds and stores in Pinecone for search

### Step-by-Step Flow

```
1. User clicks "Apply" on opportunity
   ↓
2. Backend checks: Are chunks already ingested for this noticeId?
   ↓ YES → Skip ingestion, use existing chunks
   ↓ NO → Continue
   ↓
3. Download attachments from resourceLinks[]
   → Saved to: downloads/<noticeId>/RFP.pdf, SOW.pdf, etc.
   ↓
4. Parse each file (PDF → text, XLSX → text, TXT → text)
   ↓
5. Chunk the text (see Chunking Strategy below)
   ↓
6. For each chunk:
   - Store full text + metadata in MongoDB (chunks collection)
   - Embed text using Gemini embedding model
   - Store embedding + minimal metadata in Pinecone
   ↓
7. Done! Chunks ready for retrieval
```

### Chunking Strategy (Context-Aware, Token-Based)

**Goal**: Break documents into 400-600 token chunks that preserve context and structure.

**Process**:

1. **Structure Detection**
   - Detects headings: ALL CAPS, numbered sections (SECTION 1:), ends with colon
   - Identifies paragraphs: double newlines (`\n\n`)
   - Preserves document hierarchy

2. **Section Classification**
   - **Requirement**: Contains "requirement", "shall", "must"
   - **Specification**: Contains "specification", "spec", "technical spec"
   - **Evaluation Criteria**: Contains "evaluation", "criteria", "scoring"
   - **Scope of Work**: Contains "scope", "statement of work", "SOW"
   - **Other**: Everything else

3. **Token-Based Chunking**
   - Target: 400-600 tokens per chunk (uses `tiktoken` for accurate counting)
   - If section < 600 tokens → one chunk
   - If section > 600 tokens → split at paragraph boundaries
   - If paragraph > 600 tokens → split at sentence boundaries

4. **Requirement Detection**
   - Scans for keywords: "shall", "must", "required", "requirement", "mandatory"
   - Sets `requirement_flag = true` if found
   - Helps prioritize requirement chunks during retrieval

5. **Table Handling**
   - Detects tables: contains `|` or `\t`, or keywords "pricing", "clin", "line item"
   - Tables marked as `is_table = true`
   - **Tables are NOT embedded in Pinecone** (only stored in MongoDB for reference)
   - Reason: Tables aren't useful for semantic search

6. **Amendment Versioning**
   - When RFP is updated, old chunks marked `is_latest_version = false`
   - New chunks created with `amendment_number++` and `is_latest_version = true`
   - Retrieval only fetches latest version chunks

7. **Semantic Fallback**
   - If no headings detected → uses paragraph-based chunking
   - Groups paragraphs by token limits (400-600 tokens)
   - Ensures documents without structure still chunk correctly

### File Filtering

**Included**: scope, requirement, specification, solicitation, terms, condition, work, technical, statement, criteria, evaluation

**Excluded**: questionnaire, form, template, blank, example, sample

**Why?** Focus on substantive content, skip administrative forms.

### Deduplication

- Before ingesting, checks if chunks already exist for `noticeId` with `is_latest_version = true`
- If yes → skip ingestion (no duplicate chunking)
- If no → proceed with ingestion

---

## 3. RAG Logic (Retrieval-Augmented Generation)

### What is RAG?

RAG combines **semantic search** (finding relevant chunks) with **LLM generation** (writing the proposal). Instead of the LLM relying only on its training data, it uses **retrieved chunks** from the RFP as context.

### RAG Pipeline

```
[User clicks "Apply"]
   ↓
1. Fetch opportunity from MongoDB (by noticeId)
   ↓
2. Fetch user profile from MongoDB (by companyId)
   ↓
3. Ingest attachments (if not already done) → Chunks in MongoDB + Pinecone
   ↓
4. Retrieve relevant chunks from Pinecone:
   - Query: opportunity_title + " scope requirements evaluation criteria"
   - Filter: noticeId (only chunks from this RFP)
   - Top-k: 10 chunks
   ↓
5. Fetch full text from MongoDB (using chunk_id from Pinecone results)
   ↓
6. Build context string:
   - Solicitation metadata + full description (from SAM.gov API)
   - Retrieved RFP chunks (labeled as [Source 1], [Source 2], etc.)
   - User profile (capabilities, past performance, certifications)
   ↓
7. Send to LLM (Gemini):
   - System prompt (instructions)
   - Context (solicitation + RAG chunks + profile)
   - Task: "Write a proposal draft"
   ↓
8. LLM generates proposal with inline citations [1], [2], etc.
   ↓
9. Return draft to frontend
```

### How We Match RFP Requirements to User Experience

**1. Semantic Search**
- Query: `"MSHA Altair Gas Monitors scope requirements evaluation criteria"`
- Pinecone finds chunks with similar meaning (not just keyword match)
- Prioritizes chunks with `requirement_flag = true` and `is_critical = true`

**2. Single Context Window**
- LLM sees **both** the RFP requirements (from retrieved chunks) **and** the user's past performance/capabilities (from profile) in one context
- LLM can align each requirement to relevant experience when scope/type matches

**3. Prompt Rules**
- System prompt instructs: "For each requirement, provide response using only the provided company context"
- "Only include past performance if scope/type is similar (same NAICS, service type)"
- "If no relevant experience exists, write: 'No directly relevant past performance in provided context'"
- **No hallucination**: LLM can only use what's in the context

**4. Citation System**
- Each retrieved chunk is labeled as `[Source 1]`, `[Source 2]`, etc.
- LLM must cite sources using `[1]`, `[2]`, etc. inline
- Frontend displays citations as clickable links that jump to source evidence

### Retrieval Details

**Query Construction**:
```python
query = opportunity_title + " scope requirements evaluation criteria"
# Example: "MSHA Altair Gas Monitors scope requirements evaluation criteria"
```

**Pinecone Search**:
- Embed query using Gemini embedding model
- Search Pinecone index with `noticeId` filter
- Return top-k chunks (default: 10)

**MongoDB Lookup**:
- For each Pinecone result, fetch full text from MongoDB using `chunk_id`
- Filter to only `is_latest_version = true` chunks
- Return chunks with complete text and metadata

**Why This Two-Step Process?**
- Pinecone is fast for semantic search but doesn't store full text
- MongoDB stores full text but isn't optimized for semantic search
- Combining both gives us fast search + complete text for citations

---

## 4. Prompt Engineering

### System Prompt (Initial Draft Generation)

The system prompt enforces **professional government compliance** and **strictly avoids hallucination**.

**Key Instructions**:

1. **Output Structure** (mandatory):
   - Executive Summary
   - Understanding of the Requirement
   - Technical Approach
   - Management / Staffing (if context supports)
   - Past Performance
   - Certifications and Socioeconomic Status
   - Compliance Statement
   - Pricing Note
   - Conclusion

2. **Section Rules**:
   - Mirror solicitation requirements and evaluation criteria
   - For each requirement: restate it, then provide response using only company context
   - If no relevant information exists: "Not specified in the provided context."

3. **Past Performance** (strict):
   - Only include if scope/type is similar (same NAICS, service type)
   - If no similar experience: "No directly relevant past performance in provided context."
   - Do not stretch unrelated experience

4. **Citations** (critical):
   - For every claim from RFP sources, include inline citation `[1]`, `[2]`, etc.
   - Citations must appear immediately after the relevant claim
   - Example: "The contractor shall provide 24/7 support [1] and maintain ISO 27001 certification [2]."

5. **Grounding Rules** (strict):
   - Use ONLY the provided context
   - Do NOT invent experience, projects, numbers, certifications, partners, personnel, locations, or technical methods
   - Do NOT infer capability from unrelated experience

6. **Tone**:
   - Formal, neutral, definitive
   - Use "will", "shall", "provides"
   - No marketing language
   - No apologies

**Full Prompt**: See `govproject-backend/services/proposal_service.py` → `SYSTEM_PROMPT`

### Refinement Prompt (Iterative Improvement)

When users want to refine the draft, a separate prompt handles iterative refinement:

**Key Instructions**:

1. **Clarification**: If user's request is unclear, ask ONE clarifying question
2. **Maintain Compliance**: Keep all compliance requirements intact
3. **Preserve Accuracy**: Don't invent new information
4. **Structure**: Keep same structure unless explicitly asked to change

**Full Prompt**: See `govproject-backend/services/proposal_service.py` → `REFINEMENT_SYSTEM_PROMPT`

### Context Building

The context sent to the LLM includes:

1. **Solicitation Section**:
   - Title, solicitation number, agency, deadlines, set-aside, NAICS
   - Full description text (fetched from SAM.gov API using `description` URL + API key)
   - Scope of work (if available)

2. **Retrieved RFP Sections**:
   - Top-k chunks from Pinecone (labeled as `[Source 1]`, `[Source 2]`, etc.)
   - Each chunk includes: filename, section name, section type, full text
   - Example:
     ```
     [Source 1] From: RFP_Section2.pdf | Section: SECTION 2: REQUIREMENTS | Type: requirement
     The contractor shall provide 24/7 support and maintain ISO 27001 certification...
     ```

3. **Firm Profile**:
   - Company name, capabilities, certifications, NAICS, set-aside type
   - Capabilities statement
   - Past performance (project name, client, description, value, year, keywords)

**Why This Context?**
- LLM sees everything it needs: what the government wants (solicitation + RFP chunks) and what the company offers (profile)
- LLM can match requirements to capabilities when scope/type aligns
- Citations ensure traceability back to source documents

---

## Summary: End-to-End Flow

```
1. User logs in with companyId (e.g., "sg-security-001")
   ↓
2. User browses opportunities (from MongoDB)
   ↓
3. User clicks "Apply" on an opportunity
   ↓
4. Backend:
   a. Fetches opportunity (MongoDB)
   b. Fetches user profile (MongoDB)
   c. Ingests attachments (if not done) → Chunks in MongoDB + Pinecone
   d. Retrieves relevant chunks (Pinecone → MongoDB)
   e. Fetches full description from SAM.gov API
   f. Builds context (solicitation + RAG chunks + profile)
   g. Generates draft (Gemini LLM with system prompt)
   ↓
5. Frontend displays draft with:
   - Inline citations [1], [2], etc. (clickable, jump to sources)
   - Source sidebar (shows all retrieved chunks with metadata)
   - Refinement panel (user can refine draft iteratively)
   - Download PDF button (generates clean PDF without citations)
   ↓
6. User refines draft (if needed) → Backend calls refinement API
   ↓
7. User downloads PDF → Backend generates PDF, removes citations
   ↓
8. Done! User has a submission-ready proposal
```

---

## Key Design Decisions

1. **MongoDB + Pinecone**: Fast semantic search (Pinecone) + full text storage (MongoDB)
2. **Context-Aware Chunking**: Preserves document structure, detects requirements, handles tables separately
3. **Amendment Versioning**: Tracks document updates without duplicates
4. **Citation System**: Inline citations `[1]`, `[2]` build user trust and ensure traceability
5. **Strict Prompting**: No hallucination, only use provided context, explicit "not specified" when missing
6. **Iterative Refinement**: Users can refine drafts until satisfied
7. **PDF Export**: Clean, professional PDF without citations for submission

---

## File Locations

| Component | Location |
|-----------|----------|
| Data Models | `govproject-backend/models/` |
| Chunking Logic | `govproject-backend/rag/chunker.py` |
| Ingestion | `govproject-backend/rag/ingest.py` |
| Retrieval | `govproject-backend/rag/retrieve.py` |
| Context Building | `govproject-backend/services/proposal_service.py` → `build_context()` |
| System Prompt | `govproject-backend/services/proposal_service.py` → `SYSTEM_PROMPT` |
| Draft Generation | `govproject-backend/services/proposal_service.py` → `generate_draft()` |
| PDF Generation | `govproject-backend/services/pdf_generator.py` |

---

## Additional Documentation

- **Chunking Strategy Details**: `govproject-backend/docs/CHUNKING_STRATEGY.md`
- **RAG & Prompt Details**: `govproject-backend/docs/PART2_RAG_AND_PROMPT.md`
- **Citations System**: `govproject-backend/docs/CITATIONS_SYSTEM.md`
- **Data Integration**: `govproject-backend/docs/PART1_DATA_INTEGRATION.md`

---

**Questions?** Contact the development team or refer to the codebase for implementation details.
