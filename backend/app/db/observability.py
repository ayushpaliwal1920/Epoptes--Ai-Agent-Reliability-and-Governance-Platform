from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .model import AgentRun, AgentTrace, ExecutionEvent


def _utc_now():
    return datetime.now(timezone.utc)


def _latency_ms(started_at, ended_at):
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)

    return max(0, int((ended_at - started_at).total_seconds() * 1000))


def get_owned_run(db: Session, agent, run_id: int):
    return db.scalar(
        select(AgentRun).where(
            AgentRun.id == run_id,
            AgentRun.agent_id == agent.id,
            AgentRun.organization_id == agent.organization_id,
        )
    )


def start_run(db: Session, agent, payload):
    existing = db.scalar(
        select(AgentRun.id).where(
            AgentRun.agent_id == agent.id,
            AgentRun.external_run_id == payload.external_run_id,
        )
    )

    if existing is not None:
        raise ValueError("Run already exists")

    run = AgentRun(
        agent_id=agent.id,
        organization_id=agent.organization_id,
        external_run_id=payload.external_run_id,
        name=payload.name,
        status="running",
        started_at=_utc_now(),
        metadata_json=payload.metadata,
    )

    db.add(run)
    db.commit()
    db.refresh(run)

    return run


def finish_run(db: Session, agent, run_id: int, payload):
    run = get_owned_run(db, agent, run_id)
    if run is None:
        return None
    if run.status != "running":
        raise ValueError("Run is already finished")

    ended_at = _utc_now()
    run.status = payload.status
    run.ended_at = ended_at
    run.latency_ms = _latency_ms(run.started_at, ended_at)
    run.input_tokens = payload.input_tokens
    run.output_tokens = payload.output_tokens
    run.total_tokens = payload.input_tokens + payload.output_tokens
    run.llm_call_count = payload.llm_call_count
    run.tool_call_count = payload.tool_call_count
    run.step_count = payload.step_count
    run.retry_count = payload.retry_count
    run.estimated_cost = payload.estimated_cost
    run.task_completed = payload.task_completed
    run.timed_out = payload.timed_out
    run.error_type = payload.error_type
    run.error_message = payload.error_message

    db.commit()
    db.refresh(run)
    return run


def start_trace(db: Session, agent, run_id: int, payload):
    run = get_owned_run(db, agent, run_id)
    if run is None:
        return None

    existing = db.scalar(
        select(AgentTrace.id).where(
            AgentTrace.run_id == run.id,
            AgentTrace.external_trace_id == payload.external_trace_id,
        )
    )
    if existing is not None:
        raise ValueError("Trace already exists for this run")

    trace = AgentTrace(
        run_id=run.id,
        external_trace_id=payload.external_trace_id,
        parent_trace_id=payload.parent_trace_id,
        name=payload.name,
        trace_type=payload.trace_type,
        status="running",
        provider=payload.provider,
        model_name=payload.model_name,
        tool_name=payload.tool_name,
        started_at=_utc_now(),
        input_data=payload.input_data,
        metadata_json=payload.metadata,
    )
    db.add(trace)
    db.commit()
    db.refresh(trace)
    return trace


def finish_trace(
    db: Session,
    agent,
    run_id: int,
    external_trace_id: str,
    payload,
):
    run = get_owned_run(db, agent, run_id)
    if run is None:
        return None

    trace = db.scalar(
        select(AgentTrace).where(
            AgentTrace.run_id == run.id,
            AgentTrace.external_trace_id == external_trace_id,
        )
    )
    if trace is None:
        return None
    if trace.status != "running":
        raise ValueError("Trace is already finished")

    ended_at = _utc_now()
    trace.status = payload.status
    trace.ended_at = ended_at
    trace.latency_ms = _latency_ms(trace.started_at, ended_at)
    trace.output_data = payload.output_data
    trace.input_tokens = payload.input_tokens
    trace.output_tokens = payload.output_tokens
    trace.estimated_cost = payload.estimated_cost
    trace.retry_count = payload.retry_count
    trace.time_to_first_token_ms = payload.time_to_first_token_ms
    trace.error_type = payload.error_type
    trace.error_message = payload.error_message

    db.commit()
    db.refresh(trace)
    return trace


def create_execution_event(db: Session, agent, run_id: int, payload):
    run = get_owned_run(db, agent, run_id)
    if run is None:
        return None

    event = ExecutionEvent(
        run_id=run.id,
        organization_id=agent.organization_id,
        event_type=payload.event_type,
        severity=payload.severity,
        message=payload.message,
        trace_id=payload.trace_id,
        payload=payload.payload,
        created_at=_utc_now(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
