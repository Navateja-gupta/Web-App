from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.report import ReportAck, ReportCreate
from app.services import reports as report_service

router = APIRouter(prefix="/reports", tags=["reports"])

report_rate_limit = rate_limit(10, 3600)


@router.post("", response_model=ReportAck, status_code=status.HTTP_201_CREATED, dependencies=[Depends(report_rate_limit)])
def report(data: ReportCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ReportAck:
    """Report a vendor listing or a review. Any signed-in user can report; administrators review reports."""
    created = report_service.create_report(db, user, data)
    return ReportAck(id=created.id, status=created.status)
