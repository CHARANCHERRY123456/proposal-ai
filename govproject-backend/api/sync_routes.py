"""Sync endpoints."""

from fastapi import APIRouter, HTTPException

from sync import run_sync

router = APIRouter()


@router.post("")
async def sync():
    try:
        total = await run_sync()
        return {"synced": total}
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
