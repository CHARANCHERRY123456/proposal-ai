"""Authentication endpoints. Simple demo: company ID only, no JWT."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.user_profile import get_user_profiles_collection

router = APIRouter()


class LoginRequest(BaseModel):
    companyId: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    companyId: str


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """
    Simple auth: verify companyId exists in user_profiles, return same companyId.
    Frontend stores it in localStorage and sends it (e.g. as Bearer) on each request.
    """
    profile = await get_user_profiles_collection().find_one({"companyId": req.companyId})
    if not profile:
        raise HTTPException(status_code=404, detail="Company ID not found. Please create a user profile first.")

    return LoginResponse(
        access_token=req.companyId,
        token_type="bearer",
        companyId=req.companyId,
    )
