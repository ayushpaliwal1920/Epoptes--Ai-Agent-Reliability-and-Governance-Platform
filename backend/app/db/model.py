# backend/app/db/model.py

# Add these imports if they are not already present.

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    Float,
    DateTime,
    ForeignKey,
    JSON,
    Index,
    UniqueConstraint,
)

from .database import Base
from sqlalchemy.sql import func

def utc_now():
    return datetime.now(timezone.utc)


# ==========================================
# FOUNDATION MODELS
# ==========================================

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True)

    name = Column(String(150), nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True)

    organization_id = Column(
        Integer,
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )

    name = Column(String(150), nullable=False)

    description = Column(Text, nullable=True)

    framework = Column(String(100), nullable=False)

    integration_type = Column(String(100), nullable=False)

    environment = Column(String(50), nullable=False)

    risk_level = Column(String(30), nullable=False)

    owner = Column(String(150), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    organization_id = Column(
        Integer,
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )

    email = Column(String(255), nullable=False, unique=True, index=True)

    password_hash = Column(String(255), nullable=False)

    role = Column(String(30), nullable=False, default="admin")

    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class AgentCredential(Base):
    __tablename__ = "agent_credentials"

    id = Column(Integer, primary_key=True)

    agent_id = Column(
        Integer,
        ForeignKey("agents.id"),
        nullable=False,
        index=True,
    )

    key_hash = Column(String(64), nullable=False, unique=True)

    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    revoked_at = Column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    __table_args__ = (
        Index(
            "ix_audit_events_org_created",
            "organization_id",
            "created_at",
        ),
    )

    id = Column(Integer, primary_key=True)

    organization_id = Column(
        Integer,
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )

    actor_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    action = Column(String(100), nullable=False)

    resource_type = Column(String(100), nullable=False)

    resource_id = Column(String(100), nullable=True)

    details = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


# ==========================================
# 1. AGENT RUNS
# ==========================================

class AgentRun(Base):
    __tablename__ = "agent_runs"

    __table_args__ = (
        UniqueConstraint(
            "agent_id",
            "external_run_id",
            name="uq_agent_external_run",
        ),
        Index(
            "ix_agent_runs_org_started",
            "organization_id",
            "started_at",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    agent_id = Column(
        Integer,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    external_run_id = Column(String(100), nullable=False)

    name = Column(String(200), nullable=True)

    status = Column(
        String(20),
        nullable=False,
        default="running",
    )

    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    ended_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    latency_ms = Column(Integer, nullable=True)

    queue_time_ms = Column(Integer, nullable=True)

    input_tokens = Column(Integer, default=0, nullable=False)

    output_tokens = Column(Integer, default=0, nullable=False)

    total_tokens = Column(Integer, default=0, nullable=False)

    llm_call_count = Column(Integer, default=0, nullable=False)

    tool_call_count = Column(Integer, default=0, nullable=False)

    step_count = Column(Integer, default=0, nullable=False)

    retry_count = Column(Integer, default=0, nullable=False)

    estimated_cost = Column(Float, default=0.0, nullable=False)

    timed_out = Column(Boolean, default=False, nullable=False)

    task_completed = Column(Boolean, nullable=True)

    error_type = Column(String(200), nullable=True)

    error_message = Column(Text, nullable=True)

    metadata_json = Column(JSON, default=dict, nullable=False)


# ==========================================
# 2. AGENT TRACES
# ==========================================

class AgentTrace(Base):
    __tablename__ = "agent_traces"

    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "external_trace_id",
            name="uq_run_external_trace",
        ),
        Index(
            "ix_agent_traces_run_started",
            "run_id",
            "started_at",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    run_id = Column(
        Integer,
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    external_trace_id = Column(String(100), nullable=False)

    parent_trace_id = Column(String(100), nullable=True)

    name = Column(String(200), nullable=False)

    trace_type = Column(String(30), nullable=False)

    status = Column(
        String(20),
        nullable=False,
        default="running",
    )

    provider = Column(String(100), nullable=True)

    model_name = Column(String(150), nullable=True)

    tool_name = Column(String(150), nullable=True)

    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    ended_at = Column(DateTime(timezone=True), nullable=True)

    latency_ms = Column(Integer, nullable=True)

    time_to_first_token_ms = Column(Integer, nullable=True)

    input_tokens = Column(Integer, default=0, nullable=False)

    output_tokens = Column(Integer, default=0, nullable=False)

    estimated_cost = Column(Float, default=0.0, nullable=False)

    retry_count = Column(Integer, default=0, nullable=False)

    input_data = Column(JSON, nullable=True)

    output_data = Column(JSON, nullable=True)

    error_type = Column(String(200), nullable=True)

    error_message = Column(Text, nullable=True)

    metadata_json = Column(JSON, default=dict, nullable=False)


# ==========================================
# 3. EXECUTION EVENTS
# ==========================================

class ExecutionEvent(Base):
    __tablename__ = "execution_events"

    __table_args__ = (
        Index(
            "ix_execution_events_run_created",
            "run_id",
            "created_at",
        ),
        Index(
            "ix_execution_events_org_created",
            "organization_id",
            "created_at",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    run_id = Column(
        Integer,
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_type = Column(String(100), nullable=False)

    severity = Column(
        String(20),
        default="info",
        nullable=False,
    )

    message = Column(Text, nullable=False)

    trace_id = Column(String(100), nullable=True)

    payload = Column(JSON, default=dict, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


# ==========================================
# 4. AGENT METRIC SNAPSHOTS
# ==========================================

class AgentMetricSnapshot(Base):
    __tablename__ = "agent_metric_snapshots"

    id = Column(Integer, primary_key=True, index=True)

    agent_id = Column(
        Integer,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    metric_name = Column(String(100), nullable=False)

    metric_value = Column(Float, nullable=False)

    dimensions = Column(JSON, default=dict, nullable=False)

    recorded_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class AgentScope(Base):
    __tablename__ = "agent_scopes"

    id = Column(Integer, primary_key=True, index=True)

    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    agent_id = Column(
        Integer,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    allowed_topics = Column(JSON, nullable=False, default=list)

    allowed_tools = Column(JSON, nullable=False, default=list)

    allowed_resources = Column(JSON, nullable=False, default=list)

    allowed_actions = Column(JSON, nullable=False, default=list)

    restricted_actions = Column(JSON, nullable=False, default=list)

    resource_limits = Column(
        JSON,
        nullable=False,
        default=dict
    )

    enabled = Column(Boolean, nullable=False, default=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id = Column(Integer, primary_key=True, index=True)

    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    agent_id = Column(
        Integer,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    run_id = Column(
        Integer,
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    event_type = Column(String(100), nullable=False, index=True)

    severity = Column(String(20), nullable=False, index=True)

    status = Column(
        String(30),
        nullable=False,
        default="open"
    )

    description = Column(Text, nullable=False)

    detected_content_redacted = Column(Text, nullable=True)

    detection_method = Column(String(100), nullable=False)

    blocked = Column(Boolean, default=False, nullable=False)

    metadata_json = Column(JSON, nullable=False, default=dict)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )

    __table_args__ = (
        Index(
            "ix_security_events_org_agent_created",
            "organization_id",
            "agent_id",
            "created_at"
        ),
    )


class SecurityRule(Base):
    __tablename__ = "security_rules"

    id = Column(Integer, primary_key=True, index=True)

    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    name = Column(String(150), nullable=False)

    rule_type = Column(String(100), nullable=False)

    description = Column(Text, nullable=True)

    configuration = Column(JSON, nullable=False, default=dict)

    severity = Column(String(20), default="medium")

    enabled = Column(Boolean, default=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )




class SecurityScanResult(Base):
    __tablename__ = "security_scan_results"

    id = Column(Integer, primary_key=True, index=True)

    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    agent_id = Column(
        Integer,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    run_id = Column(
        Integer,
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    scan_type = Column(String(100), nullable=False)

    risk_level = Column(String(20), nullable=False)

    passed = Column(Boolean, nullable=False)

    findings = Column(JSON, nullable=False, default=list)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )