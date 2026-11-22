
from datetime import datetime, timezone, timedelta
from statistics import median

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session

from ..db.database import get_db
from .dependencies import get_current_agent

from ..db.model import AgentRun, AgentTrace


router = APIRouter(
    prefix="/api/v1/metrics",
    tags=["Observability - Metrics"],
)


def percentile(values, percentage):
    if not values:
        return 0

    values = sorted(values)

    index = (len(values) - 1) * percentage
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)

    fraction = index - lower

    return (
        values[lower] * (1 - fraction)
        + values[upper] * fraction
    )


@router.get("/overview")
def metrics_overview(
    db: Session = Depends(get_db),
    agent=Depends(get_current_agent),
):
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)

    filters = (
        AgentRun.agent_id == agent.id,
        AgentRun.organization_id == agent.organization_id,
    )

    summary = db.execute(
        select(
            func.count(AgentRun.id).label("total"),

            func.sum(
                case(
                    (AgentRun.status == "success", 1),
                    else_=0,
                )
            ).label("success"),

            func.sum(
                case(
                    (AgentRun.status == "error", 1),
                    else_=0,
                )
            ).label("failed"),

            func.sum(
                case(
                    (AgentRun.status == "cancelled", 1),
                    else_=0,
                )
            ).label("cancelled"),

            func.sum(AgentRun.total_tokens).label("tokens"),

            func.sum(AgentRun.estimated_cost).label("cost"),

            func.sum(AgentRun.llm_call_count).label("llm_calls"),

            func.sum(AgentRun.tool_call_count).label("tool_calls"),

            func.sum(AgentRun.retry_count).label("retries"),

            func.sum(
                case(
                    (AgentRun.timed_out.is_(True), 1),
                    else_=0,
                )
            ).label("timeouts"),

            func.avg(AgentRun.latency_ms).label("avg_latency"),
        )
        .where(*filters)
    ).one()

    total = summary.total or 0
    successful = summary.success or 0
    failed = summary.failed or 0
    cancelled = summary.cancelled or 0

    completed = successful + failed + cancelled

    active = db.scalar(
        select(func.count(AgentRun.id)).where(
            *filters,
            AgentRun.status == "running",
        )
    ) or 0

    # Percentiles are calculated from completed runs.
    latency_values = db.scalars(
    select(AgentRun.latency_ms).where(
        *filters,
        AgentRun.status.in_(
            ["success", "error", "cancelled"]
        ),
        AgentRun.latency_ms.is_not(None),
    )
    ).all()

    latency_values = [
        float(value) for value in latency_values
    ]

    # Completed runs in the previous hour.
    hourly_runs = db.scalar(
        select(func.count(AgentRun.id)).where(
            *filters,
            AgentRun.ended_at >= one_hour_ago,
            AgentRun.ended_at <= now,
        )
    ) or 0

    trace_summary = db.execute(
        select(
            func.count(AgentTrace.id).label("total"),

            func.sum(
                case(
                    (AgentTrace.trace_type == "llm", 1),
                    else_=0,
                )
            ).label("llm"),

            func.sum(
                case(
                    (AgentTrace.trace_type == "tool", 1),
                    else_=0,
                )
            ).label("tools"),

            func.sum(
                case(
                    (AgentTrace.status == "success", 1),
                    else_=0,
                )
            ).label("successful"),
        )
        .join(AgentRun, AgentRun.id == AgentTrace.run_id)
        .where(*filters)
    ).one()

    trace_total = trace_summary.total or 0
    trace_success = trace_summary.successful or 0
    tool_total = trace_summary.tools or 0

    successful_tools = db.scalar(
        select(func.count(AgentTrace.id))
        .join(AgentRun, AgentRun.id == AgentTrace.run_id)
        .where(
            *filters,
            AgentTrace.trace_type == "tool",
            AgentTrace.status == "success",
        )
    ) or 0

    return {
        "execution": {
            "total_runs": total,
            "successful_runs": successful,
            "failed_runs": failed,
            "cancelled_runs": cancelled,
            "active_runs": active,
            "success_rate": round(
                successful / completed * 100, 2
            ) if completed else 0,
            "error_rate": round(
                failed / completed * 100, 2
            ) if completed else 0,
            "throughput_per_hour": hourly_runs,
        },

        "performance": {
            "average_latency_ms": round(
                float(summary.avg_latency or 0), 2
            ),
            "p50_latency_ms": round(
                median(latency_values), 2
            ) if latency_values else 0,
            "p95_latency_ms": round(
                percentile(latency_values, 0.95), 2
            ),
            "p99_latency_ms": round(
                percentile(latency_values, 0.99), 2
            ),
        },

        "usage": {
            "total_tokens": summary.tokens or 0,
            "average_tokens_per_run": round(
                (summary.tokens or 0) / total, 2
            ) if total else 0,
            "llm_calls": summary.llm_calls or 0,
            "tool_calls": summary.tool_calls or 0,
            "trace_count": trace_total,
        },

        "cost": {
            "total_estimated_cost": round(
                float(summary.cost or 0), 6
            ),
            "average_cost_per_run": round(
                float(summary.cost or 0) / total, 6
            ) if total else 0,
        },

        "reliability": {
            "total_retries": summary.retries or 0,
            "timeouts": summary.timeouts or 0,
            "tool_success_rate": round(
                successful_tools / tool_total * 100, 2
            ) if tool_total else 0,
        },
    }


@router.get("/agent/{agent_id}")
def agent_metrics(
    agent_id: int,
    db: Session = Depends(get_db),
    agent=Depends(get_current_agent),
):
    # An SDK key can only inspect its own agent.
    if agent_id != agent.id:
        from fastapi import HTTPException
        raise HTTPException(404, "Agent not found")

    return metrics_overview(db, agent)


@router.get("/models")
def model_usage(
    db: Session = Depends(get_db),
    agent=Depends(get_current_agent),
):
    rows = db.execute(
        select(
            AgentTrace.provider,
            AgentTrace.model_name,
            func.count(AgentTrace.id).label("calls"),
            func.sum(AgentTrace.input_tokens).label("input_tokens"),
            func.sum(AgentTrace.output_tokens).label("output_tokens"),
            func.sum(AgentTrace.estimated_cost).label("cost"),
            func.avg(AgentTrace.latency_ms).label("avg_latency"),
        )
        .join(AgentRun, AgentRun.id == AgentTrace.run_id)
        .where(
            AgentRun.agent_id == agent.id,
            AgentRun.organization_id == agent.organization_id,
            AgentTrace.trace_type == "llm",
        )
        .group_by(
            AgentTrace.provider,
            AgentTrace.model_name,
        )
    ).all()

    return {
        "models": [
            {
                "provider": row.provider,
                "model": row.model_name,
                "calls": row.calls,
                "input_tokens": row.input_tokens or 0,
                "output_tokens": row.output_tokens or 0,
                "cost": float(row.cost or 0),
                "average_latency_ms": float(
                    row.avg_latency or 0
                ),
            }
            for row in rows
        ]
    }


@router.get("/tools")
def tool_usage(
    db: Session = Depends(get_db),
    agent=Depends(get_current_agent),
):
    rows = db.execute(
        select(
            AgentTrace.tool_name,
            func.count(AgentTrace.id).label("calls"),
            func.avg(AgentTrace.latency_ms).label("latency"),
            func.sum(
                case(
                    (AgentTrace.status == "success", 1),
                    else_=0,
                )
            ).label("successes"),
        )
        .join(AgentRun, AgentRun.id == AgentTrace.run_id)
        .where(
            AgentRun.agent_id == agent.id,
            AgentRun.organization_id == agent.organization_id,
            AgentTrace.trace_type == "tool",
        )
        .group_by(AgentTrace.tool_name)
    ).all()

    return {
        "tools": [
            {
                "tool_name": row.tool_name,
                "calls": row.calls,
                "successful_calls": row.successes or 0,
                "average_latency_ms": float(row.latency or 0),
                "success_rate": round(
                    (row.successes or 0) / row.calls * 100, 2
                ) if row.calls else 0,
            }
            for row in rows
        ]
    }