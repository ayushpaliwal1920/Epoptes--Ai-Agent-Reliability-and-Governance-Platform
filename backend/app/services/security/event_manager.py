
from sqlalchemy.orm import Session

from app.db.model import SecurityEvent


class SecurityEventManager:

    def record_findings(
        self,
        db: Session,
        organization_id: int,
        agent_id: int,
        run_id: int | None,
        findings: list,
        original_content: str = ""
    ) -> list:

        created_events = []

        for finding in findings:

            event = SecurityEvent(
                organization_id=organization_id,
                agent_id=agent_id,
                run_id=run_id,
                event_type=finding["event_type"],
                severity=finding["severity"],
                status="open",
                description=finding["description"],

                # Never persist original prompt/output content.
                detected_content_redacted=None,

                detection_method=finding["detection_method"],
                blocked=finding.get("blocked", False),
                metadata_json={}
            )

            db.add(event)
            created_events.append(event)

        # Send pending INSERT statements to the database.
        # Do not commit here. The calling API owns the transaction.
        db.flush()

        return created_events
