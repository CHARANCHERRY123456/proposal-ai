"""Authentication endpoints."""

import secrets
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
    Simple authentication: verify companyId exists, return a token.
    For demo purposes, we generate a simple token. In production, use JWT.
    """
    profile = await get_user_profiles_collection().find_one({"companyId": req.companyId})
    if not profile:
        raise HTTPException(status_code=404, detail="Company ID not found. Please create a user profile first.")
    
    # Simple token generation (for demo). In production, use proper JWT.
    token = secrets.token_urlsafe(32)
    
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        companyId=req.companyId,
    )
