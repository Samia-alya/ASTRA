from fastapi import APIRouter

from app.config import indicators

router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.get("")
def list_indicators() -> dict:
    """Metadata + explanations for each indicator (used by the guidance UI)."""
    return indicators()
