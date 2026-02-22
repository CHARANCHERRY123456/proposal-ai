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
