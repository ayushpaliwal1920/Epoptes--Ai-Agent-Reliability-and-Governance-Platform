
import json

from sqlalchemy.orm import Session

from ..db.model import AuditEvent


def create_audit_event(
    db: Session,
    organization_id: int,
    action: str,
    resource_type: str,
    resource_id: int | str | None = None,
    actor_user_id: int | None = None,
    details: dict | None = None
):
    event = AuditEvent(
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        details=json.dumps(details or {})
    )

    db.add(event)

    return event
