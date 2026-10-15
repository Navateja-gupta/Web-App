import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.health import DatabaseHealthResponse, HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness check: the API process is running."""
    return HealthResponse(status="ok", service=settings.APP_NAME, environment=settings.ENVIRONMENT)


@router.get("/db", response_model=DatabaseHealthResponse)
def health_db(db: Session = Depends(get_db)) -> DatabaseHealthResponse:
    """Readiness check: the API can reach PostgreSQL."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        # Log details server-side only; never return connection strings or stack traces.
        logger.exception("Database health check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )
    return DatabaseHealthResponse(status="ok", database="reachable")
