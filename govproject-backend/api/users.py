"""User profile endpoints."""

from fastapi import APIRouter

from models.user_profile import UserProfile, ensure_indexes, get_user_profiles_collection

router = APIRouter()


@router.post("")
async def create_user(profile: UserProfile):
    await ensure_indexes()
    doc = profile.to_mongo()
    coll = get_user_profiles_collection()
    result = await coll.insert_one(doc)
    company_id = doc.get("companyId") or str(result.inserted_id)
    if not doc.get("companyId"):
        await coll.update_one({"_id": result.inserted_id}, {"$set": {"companyId": company_id}})
    return {"companyId": company_id, "message": "created"}
