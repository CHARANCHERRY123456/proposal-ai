"""
API routes. Main includes this single router and does not import route logic.
"""

from fastapi import APIRouter

from api import health, users, proposals, sync_routes, auth, opportunities

router = APIRouter()
router.include_router(health.router, tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(opportunities.router, prefix="/opportunities", tags=["opportunities"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(proposals.router, prefix="/draft-proposal", tags=["proposals"])
router.include_router(sync_routes.router, prefix="/sync", tags=["sync"])
