"""Proposal / draft-proposal endpoints."""

from fastapi import APIRouter, HTTPException

from models.opportunity import get_opportunities_collection
from models.user_profile import get_user_profiles_collection
from schemas.api_schemas import DraftProposalRequest
from services.proposal_service import get_proposal_details

router = APIRouter()


@router.post("")
async def draft_proposal(req: DraftProposalRequest):
    opp = await get_opportunities_collection().find_one({"noticeId": req.noticeId})
    profile = await get_user_profiles_collection().find_one({"companyId": req.companyId})
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    return get_proposal_details(opp, profile, include_draft=req.includeDraft)
