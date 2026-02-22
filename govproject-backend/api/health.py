"""Health and readiness endpoints."""

from fastapi import APIRouter

from db import db

router = APIRouter()


@router.get("/")
def home():
    return {"message": "API running"}


@router.get("/test-db")
async def test_db():
    await db.test.insert_one({"msg": "MongoDB connected"})
    return {"status": "ok"}
