
from datetime import datetime

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)

    description: str | None = None
    framework: str = "custom"
    integration_type: str = "sdk"
    environment: str = "development"
    risk_level: str = "medium"
    owner: str | None = None


class AgentResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    description: str | None
    framework: str
    integration_type: str
    environment: str
    risk_level: str
    owner: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentCreatedResponse(BaseModel):
    agent: AgentResponse
    api_key: str


class AgentKeyResponse(BaseModel):
    agent_id: int
    api_key: str
    message: str
