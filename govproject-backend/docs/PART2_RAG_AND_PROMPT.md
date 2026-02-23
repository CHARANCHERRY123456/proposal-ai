# Part 2: RAG Workflow & Prompt Engineering (The "Brain")

GovPreneurs AI — How the AI generates the proposal.

---

## 1. RAG Pipeline Design

**Inputs**

- **Government Solicitation (SAM.gov):** Notice metadata (title, solicitation number, agency, deadlines, set-aside, NAICS) + scope/description URL + attachment URLs (e.g. PDF RFP).
- **User Profile:** Company name, capabilities, certifications, past performance, capabilities statement, NAICS, set-aside type.

**Process (steps)**

1. **Ingest**
   - Attachments (e.g. PDF) for the notice are downloaded to `downloads/<noticeId>/`.
   - Each file is parsed (PDF → text) and split into **chunks** using our context-aware chunking strategy (see `docs/CHUNKING_STRATEGY.md` for details).
   - Chunking: 400-600 tokens per chunk, respects document structure (headings, sections), detects requirements, handles tables separately, tracks amendments.
   - Metadata: `noticeId`, `filename`, `chunk_index`, `section_type`, `requirement_flag`, `is_table`, `amendment_number`, `is_latest_version`.

2. **Index**
   - Each chunk is embedded (Gemini embedding model) and upserted into Pinecone with `noticeId` so we can filter by opportunity.

3. **Retrieve**
   - When a user applies (noticeId + companyId), we run a **semantic search** on Pinecone:
     - Query: opportunity title + " scope requirements evaluation criteria" (so we pull requirement/evaluation sections from the RFP).
     - Filter: `noticeId` so only chunks from this solicitation are returned.
   - Top-k chunks (e.g. 10) are returned as the **retrieved RFP requirements**.

4. **Build context**
   - We build one context block for the LLM:
     - **Solicitation:** SAM metadata + scope/description (if any).
     - **Retrieved RFP sections:** The top-k chunk texts from the PDF (so the model sees the actual requirements).
     - **Firm profile:** Capabilities, past performance, certifications, capabilities statement.

5. **Generate**
   - System prompt (see below) + the context above are sent to the LLM.
   - The model writes a section-by-section response: for each requirement/criterion it uses **only** the provided context, ties to the firm’s experience when present, and says when there is no match (no invention).

**Simple diagram (flow)**

```
[SAM.gov solicitation + attachments]     [User profile]
         |                                        |
         v                                        v
   Ingest PDF → Chunk → Embed → Pinecone          |
         |                                        |
         v                                        v
   Retrieve top-k chunks (by noticeId + query) ---+
         |
         v
   Build context = Solicitation + RAG chunks + Profile
         |
         v
   LLM (system prompt + context) → Proposal draft
```

**How we match RFP requirements to user experience**

- **Chunking:** Context-aware, structure-based chunking (400-600 tokens) that respects document sections, detects requirements, and handles tables separately. See `docs/CHUNKING_STRATEGY.md` for full details.
- **Retrieval:** Semantic search returns top-k chunks filtered by `noticeId` and `is_latest_version = true`, with full text fetched from MongoDB for citations.
- **Single context:** The model sees both the retrieved RFP text and the full firm profile in one context, so it can align each requirement/criterion to specific past performance or capabilities when the context supports it.
- **Prompt rules:** The system prompt instructs: (1) use only provided context, (2) for each requirement write a response and tie to firm experience when possible, (3) if there is no relevant experience, say so—do not invent. That keeps matching explicit and avoids hallucination.

---

## 2. System Prompt (Professional Government Compliant, No Hallucination)

This is the system prompt sent to the LLM to generate the proposal. It enforces **Professional Government Compliant** tone and **strictly avoids hallucination**.

**Prompt (used in code: `services/proposal_service.py` — `SYSTEM_PROMPT`)**

```text
You are a government proposal writer generating a draft for an official solicitation response.

OBJECTIVE:
Produce a technically compliant, evaluator-friendly proposal based strictly on the provided context.

OUTPUT STRUCTURE (mandatory):
1. Executive Summary
2. Understanding of the Requirement
3. Technical Approach
4. Management / Staffing (only if context supports it)
5. Past Performance
6. Certifications and Socioeconomic Status
7. Compliance Statement
8. Pricing Note
9. Conclusion

SECTION RULES:
- Mirror the solicitation requirements and evaluation criteria.
- For each requirement:
  • Restate the requirement in one sentence.
  • Provide the response using only the provided company context.
  • If no relevant information exists, write:
    "Not specified in the provided context."

UNDERSTANDING OF THE REQUIREMENT (mandatory, before Technical Approach):
- Demonstrate understanding of: location/site, objective of the work, and performance outcome (what success looks like). Federal evaluators expect this.

PAST PERFORMANCE — RELEVANCE (strict):
- Only include past performance if scope/type is similar to this solicitation. If none is similar, write exactly: "No directly relevant past performance in provided context." Do not stretch unrelated experience.

PERFORMANCE OUTCOME / QUALITY CONTROL:
- State how work will be completed (e.g., one mobilization), system returned to operational condition, and testing & verification. Strengthens technical score.

GROUNDING RULES — STRICT:
- Use ONLY the provided context.
- Do NOT invent experience, projects, numbers, certifications, partners, personnel, locations, or technical methods.
- Do NOT infer capability from unrelated experience.

TONE:
- Formal, neutral, and definitive.
- Use "will", "shall", and "provides".
- No marketing language.
- No apologies or statements of inability.

TRACEABILITY:
- Every capability claim must be supported by a referenced item from the company context.

LENGTH:
- Be concise and evaluator-focused.
- Avoid generic filler text.

PRICING:
- Do not generate numbers. State that pricing is provided separately if no data exists.

CONCLUSION:
- Do NOT use "best value" unless the solicitation says "best value tradeoff." Otherwise use "technically acceptable and fair and reasonable."

If required information is missing, explicitly state:
"Not specified in the provided context."
```

**Rationale**

- **Professional Government Compliant:** Mandatory output structure (Executive Summary through Conclusion); formal tone ("will", "shall", "provides"); no marketing or apologies.
- **Strictly no hallucination:** Grounding rules; past performance only when scope/type similar (otherwise "No directly relevant past performance in provided context"); traceability; no pricing numbers; conclusion uses "technically acceptable and fair and reasonable" unless solicitation says "best value tradeoff."

---

## 3. Where it lives in code

| Piece            | Location |
|------------------|----------|
| Chunking         | `rag/chunker.py` — `chunk_by_structure()` (context-aware, token-based). See `docs/CHUNKING_STRATEGY.md` for details. |
| Ingest           | `rag/ingest.py` — `run_ingest(notice_id)` (parse, chunk, embed, upsert). |
| Retrieve         | `rag/retrieve.py` — `retrieve(query_text, top_k, notice_id)` (async, fetches full text from MongoDB). |
| Context building | `services/proposal_service.py` — `build_context(opp, profile, rag_chunks)` (solicitation + RAG chunks + profile). |
| System prompt    | `services/proposal_service.py` — `SYSTEM_PROMPT`. |
| Generate draft   | `services/proposal_service.py` — `generate_draft(context)` (uses `GeminiClient.ask()`). |
