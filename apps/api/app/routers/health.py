from fastapi import APIRouter

from app.db.database import get_database_config_status

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "AkademX10 XAI API"}


@router.get("/health/config")
def health_config() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "AkademX10 XAI API",
        "database": get_database_config_status(),
    }
