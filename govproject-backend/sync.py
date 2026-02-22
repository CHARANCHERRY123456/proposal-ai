import os
from datetime import datetime, timedelta, timezone

import httpx

from db import db
from models.opportunity import ensure_indexes, upsert_opportunity

BASE = "https://api.sam.gov/opportunities/v2/search"
LIMIT = 1000
META_KEY = "sam_sync"
MAX_DAYS = 365

KEYS = (
    "noticeId", "title", "postedDate", "solicitationNumber", "fullParentPathName",
    "type", "archiveDate", "typeOfSetAside", "typeOfSetAsideDescription", "responseDeadLine",
    "naicsCode", "naicsCodes", "active", "description", "resourceLinks", "uiLink",
)


def _to_opp(sam):
    o = {k: sam.get(k) for k in KEYS}
    o["naicsCodes"] = o.get("naicsCodes") or []
    if sam.get("pointOfContact"):
        o["pointOfContact"] = [
            {"fullName": p.get("fullName"), "email": p.get("email"), "phone": p.get("phone")}
            for p in sam["pointOfContact"]
        ]
    if sam.get("placeOfPerformance"):
        p = sam["placeOfPerformance"]
        o["placeOfPerformance"] = {
            "city": {"name": (p.get("city") or {}).get("name")},
            "state": p.get("state"),
            "country": p.get("country"),
        }
    return o


async def _ensure_last_sync():
    meta = db["meta"]
    doc = await meta.find_one({"_id": META_KEY})
    if not doc:
        today = datetime.now(timezone.utc).strftime("%m/%d/%Y")
        await meta.insert_one({"_id": META_KEY, "lastSync": today})
        return today
    return doc["lastSync"]


async def run_sync():
    api_key = os.getenv("SAM_API_KEY")
    if not api_key:
        raise ValueError("SAM_API_KEY not set")

    await ensure_indexes()
    last_sync = await _ensure_last_sync()
    now = datetime.now(timezone.utc)
    now_str = now.strftime("%m/%d/%Y")

    try:
        last_d = datetime.strptime(last_sync, "%m/%d/%Y").replace(tzinfo=timezone.utc)
    except ValueError:
        last_d = now - timedelta(days=1)
    if (now - last_d).days > MAX_DAYS:
        last_sync = (now - timedelta(days=MAX_DAYS)).strftime("%m/%d/%Y")

    total = 0
    offset = 0

    async with httpx.AsyncClient(timeout=60) as client:
        while True:
            res = await client.get(
                BASE,
                params={
                    "api_key": api_key,
                    "postedFrom": last_sync,
                    "postedTo": now_str,
                    "limit": LIMIT,
                    "offset": offset,
                },
            )
            res.raise_for_status()
            data = res.json().get("opportunitiesData", [])
            if not data:
                break
            for opp in data:
                try:
                    await upsert_opportunity(_to_opp(opp))
                    total += 1
                except Exception:
                    pass
            if len(data) < LIMIT:
                break
            offset += LIMIT

    await db["meta"].update_one(
        {"_id": META_KEY},
        {"$set": {"lastSync": now_str}},
        upsert=True,
    )
    return total
