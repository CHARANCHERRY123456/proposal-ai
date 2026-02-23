# Citations & Evidence System

## Overview

The citation system provides transparency and trust by showing users exactly which sources were used to generate each part of the proposal. Users can see the original documents, sections, and text that informed the AI's responses.

---

## How It Works

### 1. **Backend: Enhanced Metadata**

When chunks are retrieved from the vector database, we fetch full metadata from MongoDB:

**Retrieval Process (`rag/retrieve.py`):**
1. Query Pinecone for top-k chunks (semantic search)
2. For each match, fetch full chunk document from MongoDB using `chunk_id`
3. Return enriched metadata including:
   - `section_name`: Original document section heading
   - `section_type`: Classification (requirement, specification, evaluation_criteria, etc.)
   - `requirement_flag`: Whether chunk contains requirement keywords
   - `is_critical`: Whether section is marked as critical
   - `chunk_index`: Position in document
   - `filename`: Source document name
   - `text`: Full chunk text (for citations)

**Response Structure:**
```json
{
  "id": "chunk_id",
  "score": 0.85,
  "text": "Full chunk text...",
  "metadata": {
    "chunk_id": "...",
    "noticeId": "...",
    "filename": "attachment_a_solicitation.pdf",
    "section_name": "SECTION 2: REQUIREMENTS",
    "section_type": "requirement",
    "requirement_flag": true,
    "is_critical": true,
    "chunk_index": 5
  }
}
```

### 2. **Frontend: Citation Display**

**Sidebar Sources Panel:**
- Lists all retrieved chunks used in proposal generation
- Shows filename, section name, and relevance score
- Color-coded badges for section types:
  - **Blue**: Requirements
  - **Purple**: Specifications
  - **Green**: Evaluation Criteria
  - **Orange**: Scope of Work
- Expandable view shows:
  - Snippet preview (150 chars)
  - Full text (expandable)
  - Chunk ID for reference

**Section-Level Citations:**
- Each proposal section shows relevant sources
- Automatically matches chunks to sections based on:
  - Section type keywords
  - Section name similarity
  - Requirement/critical flags
- Displays source filenames as badges below section content

---

## User Experience

### Trust Indicators

1. **Source Count**: "X sources used to generate this proposal"
2. **Relevance Scores**: Percentage match for each source
3. **Section Mapping**: Which sources informed which sections
4. **Full Text Access**: Users can read the exact source text
5. **Metadata Badges**: Visual indicators for requirement/critical sections

### Citation Features

**SourceChip Component:**
- Click to expand/collapse
- Shows filename, section name, and badges
- Displays snippet and full text
- Shows chunk ID for traceability

**SectionCard Component:**
- Shows relevant source count in header
- Lists referenced sources below content
- Links sources to specific sections

---

## Technical Implementation

### Backend Changes

**File: `rag/retrieve.py`**
```python
# Fetches full chunk from MongoDB with all metadata
chunk_doc = await db.chunks.find_one({"chunk_id": chunk_id, "is_latest_version": True})

# Returns enriched metadata
out.append({
    "id": chunk_id,
    "score": m.get("score"),
    "text": chunk_doc.get("text", ""),
    "metadata": {
        **meta,
        "section_name": chunk_doc.get("section_name", ""),
        "section_type": chunk_doc.get("section_type", "other"),
        "requirement_flag": chunk_doc.get("requirement_flag", False),
        "is_critical": chunk_doc.get("is_critical", False),
        "chunk_index": chunk_doc.get("chunk_index", 0),
    },
})
```

### Frontend Changes

**File: `react-frontend/src/lib/api.ts`**
- Updated `RagChunk` interface with typed metadata

**File: `react-frontend/src/pages/ProposalReview.tsx`**
- Enhanced `SourceChip` component with:
  - Section name display
  - Color-coded badges
  - Expandable full text
  - Requirement/critical indicators
- Enhanced `SectionCard` component with:
  - Relevant source detection
  - Source badges per section
  - Source count in header

---

## Benefits

1. **Transparency**: Users see exactly what sources informed the proposal
2. **Trust**: Full text access allows verification
3. **Traceability**: Chunk IDs enable debugging and auditing
4. **Context**: Section names and types provide document structure
5. **Quality**: Requirement/critical flags highlight important sections

---

## Future Enhancements

1. **Inline Citations**: Add `[1]`, `[2]` markers in draft text
2. **Source Highlighting**: Highlight which parts of text came from which source
3. **Export Citations**: Generate bibliography/reference list
4. **Source Filtering**: Filter proposal sections by source
5. **Citation Analytics**: Show which sources are most referenced
