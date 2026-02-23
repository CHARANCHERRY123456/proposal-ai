"""Proposal / draft-proposal endpoints."""

from fastapi import APIRouter, HTTPException

from models.opportunity import get_opportunities_collection
from models.user_profile import get_user_profiles_collection
from schemas.api_schemas import DraftProposalRequest, RefineDraftRequest
from services.proposal_service import get_proposal_details, refine_draft, build_context
from rag.retrieve import retrieve

router = APIRouter()


@router.post("")
async def draft_proposal(req: DraftProposalRequest):
    opp = await get_opportunities_collection().find_one({"noticeId": req.noticeId})
    profile = await get_user_profiles_collection().find_one({"companyId": req.companyId})
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    return await get_proposal_details(opp, profile, include_draft=req.includeDraft)


@router.post("/refine")
async def refine_proposal(req: RefineDraftRequest):
    """Refine an existing draft based on user feedback."""
    opp = await get_opportunities_collection().find_one({"noticeId": req.noticeId})
    profile = await get_user_profiles_collection().find_one({"companyId": req.companyId})
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Retrieve RAG chunks for context
    notice_id = opp.get("noticeId") or ""
    rag_chunks = []
    if notice_id:
        try:
            query = (opp.get("title") or "") + " scope requirements evaluation criteria"
            rag_chunks = await retrieve(query.strip() or "requirements", top_k=10, notice_id=notice_id)
        except Exception:
            rag_chunks = []
    
    # Build context
    context = build_context(opp, profile, rag_chunks)
    
    # Refine draft
    refined = refine_draft(context, req.currentDraft, req.refinementPrompt)
    
    # Check if clarification is needed
    if refined.startswith("CLARIFICATION_NEEDED:"):
        return {
            "needsClarification": True,
            "clarificationQuestion": refined.replace("CLARIFICATION_NEEDED:", "").strip(),
            "draft": req.currentDraft,  # Return original draft unchanged
        }
    
    return {
        "needsClarification": False,
        "draft": refined,
    }
