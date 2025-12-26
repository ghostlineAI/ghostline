"""Service status endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
def api_status():
    """Lightweight status endpoint for liveness checks."""
    return {"status": "operational", "api_version": "v1"}


