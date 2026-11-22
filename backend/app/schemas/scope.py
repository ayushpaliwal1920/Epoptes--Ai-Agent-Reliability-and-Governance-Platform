from pydantic import BaseModel, Field
from typing import Any


class ResourceLimits(BaseModel):
    max_requests_per_minute: int = Field(default=60, ge=1)
    max_tool_calls_per_run: int = Field(default=20, ge=1)
    max_transaction_amount: float | None = Field(
        default=None,
        ge=0
    )


class AgentScopeCreate(BaseModel):

    allowed_topics: list[str] = Field(default_factory=list)

    allowed_tools: list[str] = Field(default_factory=list)

    allowed_resources: list[str] = Field(default_factory=list)

    allowed_actions: list[str] = Field(default_factory=list)

    restricted_actions: list[str] = Field(default_factory=list)

    resource_limits: ResourceLimits = Field(
        default_factory=ResourceLimits
    )

    enabled: bool = True


class AgentScopeUpdate(AgentScopeCreate):
    pass


class AgentScopeResponse(AgentScopeCreate):

    id: int

    agent_id: int

    organization_id: int

    class Config:
        from_attributes = True