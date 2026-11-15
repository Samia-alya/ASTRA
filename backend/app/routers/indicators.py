from fastapi import APIRouter

from app.config import autonomy_rule, environments, indicators

router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.get("")
def list_indicators() -> dict:
    """Metadata + explanations for each indicator (used by the guidance UI)."""
    return indicators()


env_router = APIRouter(prefix="/environments", tags=["environments"])


@env_router.get("")
def list_environments() -> dict:
    """Mission environments (display name, one-way signal delay, source) and the Earth-independent mode rule."""
    return {"environments": environments(), "autonomy": autonomy_rule()}
