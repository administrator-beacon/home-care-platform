from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


PHI_EVENT = "phi_access"


def log_event(
    db: Session,
    *,
    agency_id: int | None,
    actor_user_id: int | None,
    event_type: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    message: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    entry = AuditLog(
        agency_id=agency_id,
        actor_user_id=actor_user_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        message=message,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(entry)
    db.commit()
