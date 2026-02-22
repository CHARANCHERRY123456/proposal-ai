"""
MongoDB persistence for GovPreneurs opportunities.
Schema matches schemas/govpreneurs_opportunity.schema.json (minimal).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- Nested types (trimmed) ---


class PointOfContact(BaseModel):
    fullName: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class PlaceCity(BaseModel):
    name: Optional[str] = None


class PlaceState(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None


class PlaceCountry(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None


class PlaceOfPerformance(BaseModel):
    city: Optional[PlaceCity] = None
    state: Optional[PlaceState] = None
    country: Optional[PlaceCountry] = None


# --- Main document ---


class GovPreneursOpportunity(BaseModel):
    """Minimal opportunity document for MongoDB (opportunities collection)."""

    noticeId: str = Field(..., description="Unique SAM.gov notice ID; primary key for upserts.")
    title: str = Field(..., description="Opportunity title.")
    postedDate: str = Field(..., description="YYYY-MM-DD.")

    solicitationNumber: Optional[str] = None
    fullParentPathName: Optional[str] = None
    type: Optional[str] = None
    archiveDate: Optional[str] = None
    typeOfSetAside: Optional[str] = None
    typeOfSetAsideDescription: Optional[str] = None
    responseDeadLine: Optional[str] = None
    naicsCode: Optional[str] = None
    naicsCodes: list[str] = Field(default_factory=list)
    active: Optional[str] = None  # "Yes" | "No"
    description: Optional[str] = None # ex : https://api.sam.gov/prod/opportunities/v1/noticedesc?noticeid=f85ff581f08d4d408ae0214beb569d95&api_key=SAM-XXXXXX  we have to add api_key at the end 
    scopeOfWorkText: Optional[str] = None
    resourceLinks: Optional[list[str]] = None
    pointOfContact: Optional[list[PointOfContact]] = None
    placeOfPerformance: Optional[PlaceOfPerformance] = None
    uiLink: Optional[str] = None
    ingestedAt: Optional[str] = None  # ISO 8601; set on insert/update

    model_config = {"extra": "forbid"}

    def to_mongo(self) -> dict:
        """Convert to dict for MongoDB (exclude None so we don't overwrite with null on partial updates)."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_mongo(cls, doc: dict) -> "GovPreneursOpportunity":
        """Build from MongoDB document."""
        return cls.model_validate(doc)


# --- Collection and indexes ---

COLLECTION_NAME = "opportunities"


def get_opportunities_collection():
    from db import db
    return db[COLLECTION_NAME]


async def ensure_indexes():
    """Create indexes for queries and upserts. Idempotent."""
    coll = get_opportunities_collection()
    await coll.create_index("noticeId", unique=True)
    await coll.create_index("active")
    await coll.create_index("postedDate")
    await coll.create_index("responseDeadLine")
    await coll.create_index("typeOfSetAside")
    await coll.create_index("naicsCodes")
    await coll.create_index([("active", 1), ("responseDeadLine", 1)])
    await coll.create_index([("title", "text")], default_language="english")


async def upsert_opportunity(data: dict) -> str:
    """Insert or replace by noticeId; set ingestedAt. Returns noticeId."""
    doc = GovPreneursOpportunity.model_validate(data).to_mongo()
    doc["ingestedAt"] = datetime.utcnow().isoformat() + "Z"
    coll = get_opportunities_collection()
    await coll.replace_one(
        {"noticeId": doc["noticeId"]},
        doc,
        upsert=True,
    )
    return doc["noticeId"]
