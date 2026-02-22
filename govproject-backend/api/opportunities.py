"""Opportunities listing endpoint."""

from fastapi import APIRouter, Query

from models.opportunity import get_opportunities_collection

router = APIRouter()


@router.get("")
async def get_opportunities(
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """
    List opportunities with pagination.
    Returns active opportunities sorted by postedDate (newest first).
    If no active opportunities, returns all opportunities.
    """
    coll = get_opportunities_collection()
    
    # Build query - prefer active, but if none exist, return all
    active_count = await coll.count_documents({"active": "Yes"})
    if active_count > 0:
        query = {"active": "Yes"}
    else:
        # Fallback: return all opportunities if no active ones
        query = {}
    
    # Count total
    total = await coll.count_documents(query)
    
    # Fetch with pagination, sorted by postedDate descending
    cursor = coll.find(query).sort("postedDate", -1).skip(offset).limit(limit)
    items = await cursor.to_list(length=limit)
    
    # Convert ObjectId to string and clean up
    for item in items:
        if "_id" in item:
            item["_id"] = str(item["_id"])
        # Ensure all expected fields have defaults
        if "naicsCodes" not in item:
            item["naicsCodes"] = []
        if "solicitationNumber" not in item:
            item["solicitationNumber"] = item.get("solicitationNumber") or ""
        if "typeOfSetAsideDescription" not in item:
            item["typeOfSetAsideDescription"] = item.get("typeOfSetAsideDescription") or ""
    
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }
