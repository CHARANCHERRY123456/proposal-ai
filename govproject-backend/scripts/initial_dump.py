"""Initial dump: 2 requests × 1000 = 2000 opportunities from SAM.gov → MongoDB. Set SAM_API_KEY in .env"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

# Project root so "models" is found when run as python scripts/initial_dump.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from dotenv import load_dotenv

load_dotenv()
from models.opportunity import ensure_indexes, upsert_opportunity

BASE = "https://api.sam.gov/opportunities/v2/search"
KEYS = ("noticeId", "title", "postedDate", "solicitationNumber", "fullParentPathName", "type",
        "archiveDate", "typeOfSetAside", "typeOfSetAsideDescription", "responseDeadLine",
        "naicsCode", "naicsCodes", "active", "description", "resourceLinks", "uiLink")


def to_opp(sam):
    o = {k: sam.get(k) for k in KEYS}
    o["naicsCodes"] = o.get("naicsCodes") or []
    if sam.get("pointOfContact"):
        o["pointOfContact"] = [{"fullName": p.get("fullName"), "email": p.get("email"), "phone": p.get("phone")} for p in sam["pointOfContact"]]
    if sam.get("placeOfPerformance"):
        p = sam["placeOfPerformance"]
        o["placeOfPerformance"] = {"city": {"name": (p.get("city") or {}).get("name")}, "state": p.get("state"), "country": p.get("country")}
    return o


async def main():
    api_key = os.getenv("SAM_API_KEY")
    if not api_key:
        print("Error: Set SAM_API_KEY in .env")
        return
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=90)
    posted_to, posted_from = end.strftime("%m/%d/%Y"), start.strftime("%m/%d/%Y")

    await ensure_indexes()
    total = 0
    for i in range(2):
        try:
            r = requests.get(BASE, params={"api_key": api_key, "postedFrom": posted_from, "postedTo": posted_to, "limit": 1000, "offset": i * 1000}, timeout=60)
            r.raise_for_status()
            batch = r.json().get("opportunitiesData") or []
        except Exception as e:
            print(f"Error on page {i + 1}:", e)
            break
        if not batch:
            break
        for sam in batch:
            try:
                await upsert_opportunity(to_opp(sam))
                total += 1
            except Exception as e:
                print("Skip", sam.get("noticeId"), e)
        print(f"Page {i + 1}: {len(batch)} stored, total {total}")
    print("Done.", total, "opportunities.")


if __name__ == "__main__":
    asyncio.run(main())
