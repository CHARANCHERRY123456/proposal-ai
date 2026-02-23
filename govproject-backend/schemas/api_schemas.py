"""
API request and response models (Pydantic).
Keep main and route handlers free of model definitions.
"""

from pydantic import BaseModel


class DraftProposalRequest(BaseModel):
    """Request body for POST /draft-proposal."""
    noticeId: str
    companyId: str
    includeDraft: bool = True


class RefineDraftRequest(BaseModel):
    """Request body for POST /draft-proposal/refine."""
    noticeId: str
    companyId: str
    currentDraft: str
    refinementPrompt: str


class DownloadPdfRequest(BaseModel):
    """Request body for POST /draft-proposal/download-pdf."""
    noticeId: str
    companyId: str
    draftText: str