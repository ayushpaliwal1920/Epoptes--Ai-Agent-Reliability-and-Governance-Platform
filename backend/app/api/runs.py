
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.database import get_db
from .dependencies import get_current_agent

from ..db.model import AgentRun
from ..schemas.observability import RunStart, RunFinish

from ..db.observability import (
    start_run,
    finish_run,
    get_owned_run,
)


router = APIRouter(
    prefix="/api/v1/runs",
    tags=["Observability - Runs"],
)


@router.post("/start", status_code=201)
def create_run(
    payload: RunStart,
    db: Session = Depends(get_db),
    agent=Depends(get_current_agent),
):
    try:
        run = start_run(
            db,
            agent,
            payload,
        )

        return {
            "message": "Run started",
            "run_id": run.id,
            "external_run_id": run.external_run_id,
            "status": run.status,
        }

    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc))


@router.post("/{run_id}/finish")
def complete_run(
    run_id: int,
    payload: RunFinish,
    db: Session = Depends(get_db),
    agent=Depends(get_current_agent),
):
    try:
        run = finish_run(
            db,
            agent,
            run_id,
            payload,
        )

        if not run:
            raise HTTPException(404, "Run not found")

        return {
            "message": "Run completed",
            "run_id": run.id,
            "status": run.status,
            "latency_ms": run.latency_ms,
            "total_tokens": run.total_tokens,
        }

    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc))


@router.get("/")
def list_runs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    agent=Depends(get_current_agent),
):
    statement = (
        select(AgentRun)
        .where(
            AgentRun.agent_id == agent.id,
            AgentRun.organization_id == agent.organization_id,
        )
        .order_by(AgentRun.started_at.desc())
        .limit(limit)
        .offset(offset)
    )

    runs = db.scalars(statement).all()

    return {
        "runs": [
            {
                "id": r.id,
                "external_run_id": r.external_run_id,
                "name": r.name,
                "status": r.status,
                "started_at": r.started_at,
                "ended_at": r.ended_at,
                "latency_ms": r.latency_ms,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "total_tokens": r.total_tokens,
                "estimated_cost": r.estimated_cost,
                "error_message": r.error_message,
            }
            for r in runs
        ],
        "limit": limit,
        "offset": offset,
    }


@router.get("/{run_id}")
def get_run(
    run_id: int,
    db: Session = Depends(get_db),
    agent=Depends(get_current_agent),
):
    run = get_owned_run(db, agent, run_id)

    if not run:
        raise HTTPException(404, "Run not found")

    return {
        "id": run.id,
        "external_run_id": run.external_run_id,
        "name": run.name,
        "status": run.status,
        "started_at": run.started_at,
        "ended_at": run.ended_at,
        "latency_ms": run.latency_ms,
        "input_tokens": run.input_tokens,
        "output_tokens": run.output_tokens,
        "total_tokens": run.total_tokens,
        "llm_call_count": run.llm_call_count,
        "tool_call_count": run.tool_call_count,
        "step_count": run.step_count,
        "retry_count": run.retry_count,
        "estimated_cost": run.estimated_cost,
        "timed_out": run.timed_out,
        "error_type": run.error_type,
        "error_message": run.error_message,
    }
