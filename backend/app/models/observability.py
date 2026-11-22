
# backend/app/models/observability.py

import uuid

from datetime import datetime, timezone

from sqlalchemy import (
    String,
    Boolean,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Text,
    Index,
    UniqueConstraint,
    JSON,
)

from sqlalchemy.orm import Mapped, mapped_column

from app.models.model import Base


def utc_now():
    return datetime.now(timezone.utc)


class AgentAPIKey(Base):
    __tablename__ = "agent_api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )

    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    key_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AgentRun(Base):
    __tablename__ = "agent_runs"

    __table_args__ = (
        UniqueConstraint(
            "agent_id",
            "external_run_id",
            name="uq_agent_external_run",
        ),
        Index("ix_runs_org_started", "organization_id", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )

    external_run_id: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20), default="running", nullable=False
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    latency_ms: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    input_tokens: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    output_tokens: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    total_tokens: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    estimated_cost: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )

    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    metadata_json: Mapped[dict] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )


class AgentTrace(Base):
    __tablename__ = "agent_traces"

    __table_args__ = (
        Index("ix_traces_run_started", "run_id", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    external_trace_id: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    parent_trace_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)

    trace_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20), default="running", nullable=False
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    latency_ms: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    input_data: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )

    output_data: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )

    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    metadata_json: Mapped[dict] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )


class ExecutionEvent(Base):
    __tablename__ = "execution_events"

    __table_args__ = (
        Index("ix_events_run_created", "run_id", "created_at"),
        Index(
            "ix_events_org_created",
            "organization_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    severity: Mapped[str] = mapped_column(
        String(20), default="info", nullable=False
    )

    message: Mapped[str] = mapped_column(
        Text, nullable=False
    )

    trace_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    payload: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
