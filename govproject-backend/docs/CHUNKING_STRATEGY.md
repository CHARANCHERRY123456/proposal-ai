# Chunking Strategy

## Overview

Our chunking strategy uses context-aware, structure-based chunking with token limits, requirement detection, table handling, and amendment versioning.

---

## 3-Phase Implementation

### Phase 1: Structure Detection + Token-Based Chunking + MongoDB Storage

**Structure Detection:**
- Detects headings: all caps, numbered sections (SECTION 1:), ends with colon
- Identifies paragraphs: double newlines (`\n\n`)
- Preserves document structure

**Section Classification:**
- **Requirement**: keywords "requirement", "shall", "must"
- **Specification**: keywords "specification", "spec", "technical spec"
- **Condition**: keywords "condition", "terms", "clause"
- **Evaluation Criteria**: keywords "evaluation", "criteria", "scoring"
- **Scope of Work**: keywords "scope", "statement of work", "sow"
- **Other**: everything else

**Token-Based Chunking:**
- Target: 400-600 tokens per chunk
- Each section = one chunk (if < 600 tokens)
- If section > 600 tokens: split at paragraph boundaries
- If paragraph > 600 tokens: split at sentence boundaries

**Storage:**
- Full text stored in MongoDB `chunks` collection
- Vector DB stores minimal metadata: `chunk_id`, `noticeId`, `section_type`, `is_critical`
- No full text in vector DB (saves space, improves performance)

**File Filtering:**
- Includes: scope, requirement, specification, solicitation, terms, condition, work, technical, statement, criteria, evaluation
- Excludes: questionnaire, form, template, blank, example, sample

---

### Phase 2: Requirement Detection + Table Handling

**Requirement Detection:**
- Scans chunk text for keywords: "shall", "must", "required", "requirement", "mandatory"
- Sets `requirement_flag = true` if found
- Stored in both MongoDB and vector DB metadata

**Table Detection:**
- Detects tables: contains `|` or `\t`, or keywords "pricing", "clin", "line item"
- Tables marked as `type = "pricing_table"` or `is_table = true`
- **Tables are NOT embedded in vector DB** (only stored in MongoDB)
- Reason: Tables aren't useful for semantic search, only for reference

**Metadata Updates:**
- Vector DB: `chunk_id`, `noticeId`, `section_type`, `is_critical`, `requirement_flag`
- MongoDB: Full text + all metadata including `is_table`, `requirement_flag`

---

### Phase 3: Amendment Versioning + Semantic Fallback

**Amendment Versioning:**
- `amendment_number`: 0 for original, 1, 2, 3... for amendments
- `is_latest_version`: true/false flag
- When re-chunking: marks old chunks as `is_latest_version = false`, creates new with `is_latest_version = true`
- Retrieval filters to only `is_latest_version = true` chunks

**Semantic Fallback:**
- If no headings detected → uses paragraph-based chunking
- Groups paragraphs by token limits (400-600 tokens)
- Ensures documents without structure still chunk correctly

**Retrieval Updates:**
- Fetches full text from MongoDB using `chunk_id` (not from vector DB)
- Filters to latest version only
- Returns chunks with complete text for citations

---

## Chunking Flow

```
1. Parse document → Extract text
2. Detect headings → Identify sections
3. Classify sections → requirement/specification/condition/etc.
4. Create chunks by section:
   - Section < 600 tokens → one chunk
   - Section > 600 tokens → split at paragraphs
   - Paragraph > 600 tokens → split at sentences
5. Detect requirements → Set requirement_flag
6. Detect tables → Mark is_table, skip vector DB
7. Store in MongoDB → Full text + metadata
8. Store in vector DB → Minimal metadata (no text)
9. Track amendments → amendment_number, is_latest_version
```

---

## Chunk Metadata Structure

**MongoDB (chunks collection):**
```json
{
  "chunk_id": "noticeId_filename_chunkIndex",
  "noticeId": "...",
  "filename": "...",
  "text": "full chunk text...",
  "section_name": "SECTION 2: REQUIREMENTS",
  "section_type": "requirement",
  "is_critical": true,
  "requirement_flag": true,
  "is_table": false,
  "chunk_index": 0,
  "amendment_number": 0,
  "is_latest_version": true
}
```

**Vector DB (Pinecone metadata):**
```json
{
  "chunk_id": "...",
  "noticeId": "...",
  "filename": "...",
  "section_type": "requirement",
  "is_critical": "true",
  "requirement_flag": "true"
}
```

---

## Key Features

1. **Context-Aware**: Respects document structure, keeps related content together
2. **Token-Based**: Uses tokens (400-600) instead of characters for better LLM compatibility
3. **Requirement Detection**: Automatically marks requirement chunks
4. **Table Handling**: Excludes tables from RAG (stored for reference only)
5. **Amendment Tracking**: Handles document updates without duplicates
6. **Semantic Fallback**: Works even without document structure
7. **Efficient Storage**: Full text in MongoDB, minimal metadata in vector DB
8. **Citation Support**: Full text available for citations via chunk_id

---

## File Locations

- Helper functions: `rag/utils.py`
- Chunking logic: `rag/chunker.py`
- Ingestion: `rag/ingest.py`
- Retrieval: `rag/retrieve.py`
