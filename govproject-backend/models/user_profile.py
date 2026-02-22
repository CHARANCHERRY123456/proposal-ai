"""
User profile for opportunity matching and RAG (proposal drafting).
Schema: schemas/user_profile.schema.json
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class Location(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None


class PastPerformanceItem(BaseModel):
    projectName: Optional[str] = None
    client: Optional[str] = None
    description: Optional[str] = None
    projectValue: Optional[int | float] = None
    year: Optional[int] = None
    keywords: list[str] = Field(default_factory=list)


class Contact(BaseModel):
    fullName: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class UserProfile(BaseModel):
    companyId: Optional[str] = None
    companyName: str = Field(..., description="Company name.")
    website: Optional[str] = None
    location: Optional[Location] = None
    yearsOfExperience: Optional[int | float] = None
    teamSize: Optional[int] = None
    naicsCodes: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    pastPerformance: list[PastPerformanceItem] = Field(default_factory=list)
    capabilitiesStatement: Optional[str] = None
    setAsideType: Optional[str] = None
    uei: Optional[str] = None
    cageCode: Optional[str] = None
    contact: Optional[Contact] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None

    model_config = {"extra": "forbid"}

    def to_mongo(self) -> dict:
        d = self.model_dump(exclude_none=True)
        now = datetime.now(timezone.utc).isoformat()
        if "createdAt" not in d:
            d["createdAt"] = now
        d["updatedAt"] = now
        return d

    @classmethod
    def from_mongo(cls, doc: dict) -> "UserProfile":
        return cls.model_validate(doc)


COLLECTION_NAME = "user_profiles"


def get_user_profiles_collection():
    from db import db
    return db[COLLECTION_NAME]


async def ensure_indexes():
    coll = get_user_profiles_collection()
    await coll.create_index("companyId", unique=True, sparse=True)
    await coll.create_index("uei", sparse=True)
    await coll.create_index("naicsCodes")
    await coll.create_index("setAsideType")
