"""User profile endpoints."""

import re
from fastapi import APIRouter, HTTPException

from models.user_profile import UserProfile, ensure_indexes, get_user_profiles_collection

router = APIRouter()


def generate_company_id(company_name: str) -> str:
    """Generate a companyId from company name."""
    # Convert to lowercase, remove special chars, replace spaces with hyphens
    base = re.sub(r'[^a-z0-9\s-]', '', company_name.lower())
    base = re.sub(r'\s+', '-', base.strip())
    # Limit to 30 chars, add random suffix if needed
    if len(base) > 20:
        base = base[:20]
    # Add timestamp suffix for uniqueness
    from datetime import datetime
    suffix = datetime.now().strftime("%y%m%d")
    return f"{base}-{suffix}"


@router.post("")
async def create_user(profile: UserProfile):
    await ensure_indexes()
    doc = profile.to_mongo()
    coll = get_user_profiles_collection()
    
    # CompanyId is required - generate if not provided
    if not doc.get("companyId"):
        company_id = generate_company_id(doc.get("companyName", "company"))
        # Ensure uniqueness
        counter = 1
        original_id = company_id
        while await coll.find_one({"companyId": company_id}):
            company_id = f"{original_id}-{counter}"
            counter += 1
        doc["companyId"] = company_id
    
    # Check if companyId already exists
    existing = await coll.find_one({"companyId": doc["companyId"]})
    if existing:
        raise HTTPException(status_code=400, detail=f"Company ID '{doc['companyId']}' already exists. Please choose a different one.")
    
    result = await coll.insert_one(doc)
    return {"companyId": doc["companyId"], "message": "created"}
