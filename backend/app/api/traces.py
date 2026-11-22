
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.database import get_db
from .dependencies import get_current_agent

from ..db.model import AgentTrace

from ..schemas.observability import (
    TraceStart,
    TraceFinish,
)

from ..db.observability import (
    start_trace,
    finish_trace,
    get_owned_run,
)


router = APIRouter(
    prefix="/api/v1/runs/{run_id}/traces",
    tags=["Observability - Traces"],
)


@router.post("/", status_code=201)
def create_trace(
    run_id: int,
    payload: TraceStart,
    db: Session = Depends(get_db),
    agent=Depends(get_current_agent),
):
    try:
        trace = start_trace(
            db,
            agent,
            run_id,
            payload,
        )

        if not trace:
            raise HTTPException(404, "Run not found")

        return {
            "message": "Trace started",
            "trace_id": trace.external_trace_id,
            "status": trace.status,
        }

    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc))


@router.post("/{trace_id}/finish")
def complete_trace(
    run_id: int,
    trace_id: str,
    payload: TraceFinish,
    db: Session = Depends(get_db),
    agent=Depends(get_current_agent),
):
    try:
        trace = finish_trace(
            db,
            agent,
            run_id,
            trace_id,
            payload,
        )

        if not trace:
            raise HTTPException(404, "Trace not found")

        return {
            "message": "Trace completed",
            "trace_id": trace.external_trace_id,
            "status": trace.status,
            "latency_ms": trace.latency_ms,
        }

    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc))


@router.get("/")
def list_traces(
    run_id: int,
    db: Session = Depends(get_db),
    agent=Depends(get_current_agent),
):
    run = get_owned_run(db, agent, run_id)

    if not run:
        raise HTTPException(404, "Run not found")

    traces = db.scalars(
        select(AgentTrace)
        .where(AgentTrace.run_id == run_id)
        .order_by(AgentTrace.started_at)
    ).all()

    return {
        "traces": [
            {
                "id": t.id,
                "trace_id": t.external_trace_id,
                "parent_trace_id": t.parent_trace_id,
                "name": t.name,
                "type": t.trace_type,
                "status": t.status,
                "provider": t.provider,
                "model_name": t.model_name,
                "tool_name": t.tool_name,
                "latency_ms": t.latency_ms,
                "input_tokens": t.input_tokens,
                "output_tokens": t.output_tokens,
                "estimated_cost": t.estimated_cost,
                "time_to_first_token_ms": (
                    t.time_to_first_token_ms
                ),
                "error_message": t.error_message,
            }
            for t in traces
        ]
    }
