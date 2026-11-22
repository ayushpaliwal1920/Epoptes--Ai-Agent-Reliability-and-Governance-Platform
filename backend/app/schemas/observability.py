
from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field, ConfigDict


class RunStart(BaseModel):
    external_run_id: str = Field(
        min_length=1,
        max_length=100,
    )

    name: Optional[str] = Field(
        default=None,
        max_length=200,
    )

    metadata: dict = Field(default_factory=dict)


class RunFinish(BaseModel):
    status: Literal["success", "error", "cancelled"]

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)

    llm_call_count: int = Field(default=0, ge=0)
    tool_call_count: int = Field(default=0, ge=0)

    step_count: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0)

    estimated_cost: float = Field(default=0, ge=0)

    task_completed: Optional[bool] = None

    timed_out: bool = False

    error_type: Optional[str] = None
    error_message: Optional[str] = Field(
        default=None,
        max_length=10000,
    )


class TraceStart(BaseModel):
    external_trace_id: str = Field(
        min_length=1,
        max_length=100,
    )

    parent_trace_id: Optional[str] = None

    name: str = Field(
        min_length=1,
        max_length=200,
    )

    trace_type: Literal[
        "llm",
        "tool",
        "retrieval",
        "agent",
        "chain",
        "custom",
    ]

    provider: Optional[str] = None
    model_name: Optional[str] = None
    tool_name: Optional[str] = None

    input_data: Optional[dict] = None

    metadata: dict = Field(default_factory=dict)


class TraceFinish(BaseModel):
    status: Literal["success", "error"]

    output_data: Optional[dict] = None

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)

    estimated_cost: float = Field(default=0, ge=0)

    retry_count: int = Field(default=0, ge=0)

    time_to_first_token_ms: Optional[int] = Field(
        default=None,
        ge=0,
    )

    error_type: Optional[str] = None
    error_message: Optional[str] = Field(
        default=None,
        max_length=10000,
    )


class EventCreate(BaseModel):
    event_type: str = Field(
        min_length=1,
        max_length=100,
    )

    severity: Literal[
        "debug",
        "info",
        "warning",
        "error",
        "critical",
    ] = "info"

    message: str = Field(
        min_length=1,
        max_length=5000,
    )

    trace_id: Optional[str] = None

    payload: dict = Field(default_factory=dict)


class RunResponse(BaseModel):
    id: int
    external_run_id: str
    name: Optional[str]
    status: str

    started_at: datetime
    ended_at: Optional[datetime]

    latency_ms: Optional[int]

    input_tokens: int
    output_tokens: int
    total_tokens: int

    estimated_cost: float

    model_config = ConfigDict(from_attributes=True)
