from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.database import get_db
from .dependencies import get_current_agent

from ..db.model import ExecutionEvent

from ..schemas.observability import EventCreate

from ..db.observability import (
    create_execution_event,
    get_owned_run,
)


router = APIRouter(
    prefix="/api/v1/runs/{run_id}/events",
    tags=["Observability - Events"],
)


@router.post("/", status_code=201)
def create_event(
    run_id: int,
    payload: EventCreate,
    db: Session = Depends(get_db),
    agent=Depends(get_current_agent),
):
    try:
        event = create_execution_event(
            db,
            agent,
            run_id,
            payload,
        )

        if not event:
            raise HTTPException(404, "Run not found")

        return {
            "id": event.id,
            "event_type": event.event_type,
            "created_at": event.created_at,
        }

    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc))


@router.get("/")
def get_events(
    run_id: int,
    db: Session = Depends(get_db),
    agent=Depends(get_current_agent),
):
    run = get_owned_run(db, agent, run_id)

    if not run:
        raise HTTPException(404, "Run not found")

    events = db.scalars(
        select(ExecutionEvent)
        .where(
            ExecutionEvent.run_id == run_id,
            ExecutionEvent.organization_id == agent.organization_id,
        )
        .order_by(ExecutionEvent.created_at)
    ).all()

    return {
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "severity": e.severity,
                "message": e.message,
                "trace_id": e.trace_id,
                "payload": e.payload,
                "created_at": e.created_at,
            }
            for e in events
        ]
    }