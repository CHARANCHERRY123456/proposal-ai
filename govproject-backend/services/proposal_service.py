"""
Proposal details (opportunity + company + attachments) and optional LLM draft.
Attachments are downloaded under downloads/<noticeId>/ with safe filenames.
"""

import os
import re
from urllib.parse import urlparse, unquote

import httpx

from clients import GeminiClient

# --- Constants ---

ATTACHMENTS_DIR = "downloads"
DUMMY_SCOPE_TEXT = "[Scope of work not fetched. Description URL available; append API key to fetch when quota allows.]"

CONTENT_TYPE_TO_EXT = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel": ".xls",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/zip": ".zip",
    "text/plain": ".txt",
    "text/html": ".html",
}

# --- Attachment download helpers ---


def _safe_basename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    s = re.sub(r"[^\w\-_. ]", "_", unquote(name).strip())
    return s[:200] if s else ""


def _filename_from_response(response, url: str, index: int) -> str:
    """Choose filename from Content-Disposition, URL path, or fallback to attachment_{index}.ext."""
    content_disp = (response.headers.get("content-disposition") or "").lower()
    if "filename=" in content_disp:
        part = content_disp.split("filename=", 1)[-1].strip().strip('"\'')
        if ";" in part:
            part = part.split(";")[0].strip()
        name = _safe_basename(part)
        if name and name.lower() != "download":
            return name
    name = _safe_basename(os.path.basename(urlparse(url).path))
    if name and name.lower() != "download":
        return name
    content_type = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
    ext = CONTENT_TYPE_TO_EXT.get(content_type, "")
    return f"attachment_{index}{ext}"


def _download_one(url: str, dir_path: str, index: int, timeout: float = 30.0) -> tuple[bool, str | None, str]:
    """Download one URL into dir_path. Returns (success, error_message, filename)."""
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            filename = _filename_from_response(response, url, index)
            os.makedirs(dir_path, exist_ok=True)
            path = os.path.normpath(os.path.join(dir_path, filename))
            with open(path, "wb") as f:
                f.write(response.content)
            return True, None, filename
    except Exception as e:
        return False, str(e), ""


def download_attachments(notice_id: str, resource_links: list[str]) -> list[dict]:
    """Download each resource link into downloads/<notice_id>/; return list of {url, localPath, success, error?}."""
    base_dir = os.path.join(ATTACHMENTS_DIR, notice_id or "unknown")
    result = []
    for i, url in enumerate(resource_links):
        if not (url and isinstance(url, str)):
            continue
        success, error, filename = _download_one(url, base_dir, i)
        local_path = os.path.normpath(os.path.join(base_dir, filename)) if filename else ""
        item = {"url": url, "localPath": local_path, "success": success}
        if error:
            item["error"] = error
        result.append(item)
    return result

# --- Proposal details (opportunity + company + attachments) ---

OPPORTUNITY_KEYS = (
    "noticeId", "title", "solicitationNumber", "fullParentPathName", "postedDate",
    "responseDeadLine", "type", "archiveDate", "typeOfSetAside", "typeOfSetAsideDescription",
    "naicsCode", "naicsCodes", "active", "uiLink", "pointOfContact", "placeOfPerformance",
)

COMPANY_KEYS = (
    "companyId", "companyName", "website", "location", "yearsOfExperience", "teamSize",
    "naicsCodes", "capabilities", "certifications", "pastPerformance", "capabilitiesStatement",
    "setAsideType", "uei", "cageCode", "contact",
)


def _to_opportunity_details(opp: dict) -> dict:
    out = {k: opp.get(k) for k in OPPORTUNITY_KEYS}
    out["descriptionUrl"] = opp.get("description")
    out["scopeOfWorkText"] = opp.get("scopeOfWorkText") or DUMMY_SCOPE_TEXT
    out["descriptionNote"] = "Append API key to descriptionUrl to fetch full text (not requested now; quota)."
    return out


def _to_company_details(profile: dict) -> dict:
    return {k: profile.get(k) for k in COMPANY_KEYS}


async def get_proposal_details(
    opp: dict,
    profile: dict,
    *,
    rag_top_k: int = 10,
    include_draft: bool = True,
) -> dict:
    """Build full proposal payload: opportunity, company, attachments, RAG chunks, and LLM draft."""
    notice_id = opp.get("noticeId") or ""
    resource_links = opp.get("resourceLinks") or []
    stored_files = download_attachments(notice_id, resource_links)
    folder_for_notice = os.path.join(ATTACHMENTS_DIR, notice_id) if notice_id else ATTACHMENTS_DIR

    # RAG: ingest (so chunks have text in metadata) then retrieve
    rag_chunks = []
    if notice_id:
        try:
            import logging
            logger = logging.getLogger(__name__)
            from rag.ingest import run_ingest
            from rag.retrieve import retrieve
            await run_ingest(notice_id)
            query = (opp.get("title") or "") + " scope requirements evaluation criteria"
            from rag.retrieve import retrieve
            rag_chunks = await retrieve(query.strip() or "requirements", top_k=rag_top_k, notice_id=notice_id)
            logger.info(f"[CITATIONS] Retrieved {len(rag_chunks)} chunks for proposal generation")
            if rag_chunks:
                logger.info(f"[CITATIONS] First chunk metadata keys: {list(rag_chunks[0].get('metadata', {}).keys())}")
        except FileNotFoundError:
            rag_chunks = []
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"[CITATIONS] Error retrieving chunks: {e}", exc_info=True)
            rag_chunks = []

    out = {
        "opportunity": _to_opportunity_details(opp),
        "company": _to_company_details(profile),
        "attachments": {
            "folder": ATTACHMENTS_DIR,
            "folderForNotice": folder_for_notice,
            "urls": resource_links,
            "storedFiles": stored_files,
            "note": "Description URL not requested (quota). Use descriptionUrl + API key for notice text when needed.",
        },
        "ragChunks": rag_chunks,
    }

    if include_draft:
        context = build_context(opp, profile, rag_chunks)
        out["draft"] = generate_draft(context, rag_chunks)

    return out

# --- Context text for LLM (used when draft generation is enabled) ---


def _build_opportunity_text(opp: dict) -> str:
    parts = [
        f"Title: {opp.get('title', '')}",
        f"Solicitation Number: {opp.get('solicitationNumber', '')}",
        f"Agency: {opp.get('fullParentPathName', '')}",
        f"Posted: {opp.get('postedDate', '')}",
        f"Response Deadline: {opp.get('responseDeadLine', '')}",
        f"Type: {opp.get('type', '')}",
        f"Set-Aside: {opp.get('typeOfSetAsideDescription') or opp.get('typeOfSetAside', '')}",
        f"NAICS: {', '.join(opp.get('naicsCodes') or [])}",
    ]
    if opp.get("scopeOfWorkText"):
        parts.append(f"Scope of Work:\n{opp['scopeOfWorkText']}")
    if opp.get("description"):
        parts.append(f"Description URL: {opp['description']}")
    return "\n".join(parts)


def _build_profile_text(profile: dict) -> str:
    parts = [
        f"Company: {profile.get('companyName', '')}",
        f"Capabilities: {', '.join(profile.get('capabilities') or [])}",
        f"Certifications: {', '.join(profile.get('certifications') or [])}",
        f"NAICS: {', '.join(profile.get('naicsCodes') or [])}",
        f"Set-Aside: {profile.get('setAsideType', '')}",
    ]
    if profile.get("capabilitiesStatement"):
        parts.append(f"Capabilities Statement:\n{profile['capabilitiesStatement']}")
    past = profile.get("pastPerformance") or []
    if past:
        parts.append("Past Performance:")
    for i, p in enumerate(past, 1):
        parts.append(
            f"  {i}. {p.get('projectName', '')} | Client: {p.get('client', '')} | {p.get('description', '')} "
            f"| Value: {p.get('projectValue')} | Year: {p.get('year')} | Keywords: {', '.join(p.get('keywords') or [])}"
        )
    return "\n".join(parts)


def build_context(opp: dict, profile: dict, rag_chunks: list[dict] | None = None) -> str:
    """Single text block for LLM: solicitation + retrieved RFP chunks + firm profile."""
    parts = [
        "--- SOLICITATION ---\n" + _build_opportunity_text(opp),
        "\n\n--- FIRM PROFILE ---\n" + _build_profile_text(profile),
    ]
    if rag_chunks:
        chunk_sections = []
        for idx, chunk in enumerate(rag_chunks, 1):
            text = chunk.get("text", "").strip()
            if not text:
                continue
            filename = chunk.get("metadata", {}).get("filename", f"Source {idx}")
            section_name = chunk.get("metadata", {}).get("section_name", "")
            section_type = chunk.get("metadata", {}).get("section_type", "other")
            
            # Build labeled source
            source_label = f"[Source {idx}]"
            source_header = f"{source_label} From: {filename}"
            if section_name:
                source_header += f" | Section: {section_name}"
            if section_type != "other":
                source_header += f" | Type: {section_type}"
            
            chunk_sections.append(f"{source_header}\n{text}")
        
        if chunk_sections:
            parts.insert(
                1,
                "\n\n--- RETRIEVED SOLICITATION SECTIONS (from RFP/attachments) ---\n"
                "IMPORTANT: When referencing information from these sources in your proposal, cite them using [1], [2], [3], etc. matching the Source number.\n"
                + "\n\n".join(chunk_sections),
            )
    return "".join(parts)


# Professional Government Compliant; strictly no hallucination (see docs/PART2_RAG_AND_PROMPT.md)
SYSTEM_PROMPT = """
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
- In a short section, demonstrate that the offeror understands: (1) the location/site, (2) the objective of the work, and (3) the performance outcome (what success looks like), not just the task. Federal evaluators expect this.

PAST PERFORMANCE — RELEVANCE (strict):
- Only include past performance if the scope or type of work is similar to this solicitation (e.g., same or closely related NAICS, service type, or deliverable). Do not stretch unrelated experience (e.g., access control or IT to HVAC repair).
- If no past performance in the provided context is similar in scope/type, write exactly:
  "No directly relevant past performance in provided context."
- Do not list tangentially related projects to fill the section; that weakens evaluation.

PERFORMANCE OUTCOME / QUALITY CONTROL (in Technical Approach or as appropriate):
- Even for small jobs, state clearly: how work will be completed (e.g., one mobilization if applicable), that the system/equipment will be returned to operational condition, and that testing and verification will be performed. This strengthens the technical score.

GROUNDING RULES — STRICT:
- Use ONLY the provided context.
- Do NOT invent experience, projects, numbers, certifications, partners, personnel, locations, or technical methods.
- Do NOT infer capability from unrelated experience.

TONE:
- Formal, neutral, and definitive.
- Use "will", "shall", and "provides".
- No marketing language.
- No apologies or statements of inability.

CITATIONS AND SOURCES (CRITICAL):
- You will be provided with retrieved RFP sections labeled as [Source 1], [Source 2], etc.
- For EVERY claim, requirement reference, or technical detail that comes from the RFP sources, include an inline citation in the format [1], [2], [3], etc.
- Citations MUST appear immediately after the relevant claim or statement.
- Example: "The contractor shall provide 24/7 support [1] and maintain ISO 27001 certification [2]."
- If referencing company capabilities from the firm profile, you may cite as [Company Profile] or omit citation if it's general company information.
- DO NOT cite for generic statements or common knowledge.
- DO cite for: specific requirements, evaluation criteria, technical specifications, deadlines, compliance requirements, and any details from the RFP documents.

TRACEABILITY:
- Every capability claim must be supported by a referenced item from the company context.
- Every requirement reference must cite the source document.

LENGTH:
- Be concise and evaluator-focused.
- Avoid generic filler text.

PRICING:
- Do not generate numbers. State that pricing is provided separately if no data exists.

CONCLUSION:
- Do NOT use "best value" unless the solicitation explicitly uses "best value tradeoff" or similar. Otherwise use wording such as: "technically acceptable and fair and reasonable."

If required information is missing, explicitly state:
"Not specified in the provided context."
"""


def generate_draft(context: str, rag_chunks: list[dict] | None = None) -> str:
    """Produce a proposal draft from context using Gemini (via GeminiClient)."""
    gemini = GeminiClient()
    
    citation_note = ""
    if rag_chunks:
        citation_note = "\n\nCITATION FORMAT: Use [1], [2], [3], etc. to cite sources. Each number corresponds to the Source number in the retrieved sections above."
    
    prompt = (
        f"{SYSTEM_PROMPT}\n\n--- Provided Context ---\n{context}\n\n--- Task ---\n"
        f"Write a proposal draft based on the above context only.{citation_note}\n"
        "Remember: Include inline citations [1], [2], etc. immediately after any claim or requirement that comes from the RFP sources."
    )
    return gemini.ask(prompt).strip()


REFINEMENT_SYSTEM_PROMPT = """
You are a government proposal writer refining an existing proposal draft based on user feedback.

OBJECTIVE:
Refine the provided draft according to the user's specific instructions while maintaining compliance and accuracy.

RULES:
1. If the user's request is unclear or ambiguous, ask ONE clarifying question in a friendly, professional tone.
2. If the request is clear, apply the changes while:
   - Maintaining all compliance requirements
   - Keeping the same structure unless explicitly asked to change
   - Preserving accurate information from the original context
   - Not inventing new information
3. If the user asks for something that contradicts compliance requirements, politely explain why it cannot be done and suggest an alternative.

OUTPUT:
- If clarification is needed, respond with: "CLARIFICATION_NEEDED: [your question]"
- Otherwise, return the refined draft in full.
"""


def refine_draft(context: str, current_draft: str, refinement_prompt: str) -> str:
    """Refine an existing draft based on user feedback."""
    gemini = GeminiClient()
    prompt = (
        f"{REFINEMENT_SYSTEM_PROMPT}\n\n"
        f"--- Original Context ---\n{context}\n\n"
        f"--- Current Draft ---\n{current_draft}\n\n"
        f"--- User's Refinement Request ---\n{refinement_prompt}\n\n"
        f"--- Task ---\n"
        f"Refine the draft according to the user's request. If clarification is needed, respond with 'CLARIFICATION_NEEDED:' followed by your question. Otherwise, return the complete refined draft."
    )
    result = gemini.ask(prompt).strip()
    
    # Check if clarification is needed
    if result.startswith("CLARIFICATION_NEEDED:"):
        return result
    
    return result
