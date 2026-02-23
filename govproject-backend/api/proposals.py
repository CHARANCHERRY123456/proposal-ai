"""Proposal / draft-proposal endpoints."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from models.opportunity import get_opportunities_collection
from models.user_profile import get_user_profiles_collection
from schemas.api_schemas import DraftProposalRequest, RefineDraftRequest, DownloadPdfRequest
from services.proposal_service import get_proposal_details, refine_draft, build_context
from services.pdf_generator import generate_pdf
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
    
    # Fetch full description text
    from services.proposal_service import fetch_description_text
    description_text = ""
    description_url = opp.get("description")
    if description_url:
        description_text = await fetch_description_text(description_url)
    
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
    context = build_context(opp, profile, rag_chunks, description_text)
    
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


@router.post("/download-pdf")
async def download_pdf(req: DownloadPdfRequest):
    """Generate and download proposal draft as PDF."""
    opp = await get_opportunities_collection().find_one({"noticeId": req.noticeId})
    profile = await get_user_profiles_collection().find_one({"companyId": req.companyId})
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    if not req.draftText:
        raise HTTPException(status_code=400, detail="No draft text provided")
    
    # Generate PDF
    try:
        opp_title = opp.get("title", "Proposal")
        company_name = profile.get("companyName", "")
        pdf_buffer = generate_pdf(req.draftText, title=opp_title, company_name=company_name)
        
        # Generate filename
        notice_id = opp.get("noticeId", "proposal")
        filename = f"proposal_{notice_id}.pdf"
        
        return Response(
            content=pdf_buffer.read(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"PDF generation not available: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")
