from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def record_audit(
    db: Session,
    *,
    actor_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Add an audit entry to the current transaction (committed together with the change).

    Never pass passwords, tokens or unnecessary personal data in `details`.
    """
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
        )
    )
