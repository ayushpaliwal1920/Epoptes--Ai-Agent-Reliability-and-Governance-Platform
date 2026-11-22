from pydantic import BaseModel, Field
from typing import Any
from typing import Literal

class SecurityScanRequest(BaseModel):

    content: str = Field(min_length=1, max_length=100000)

    scan_type: Literal["input", "output"] = "input"

    run_id: int | None = None


class SecurityFinding(BaseModel):

    event_type: str

    severity: str

    description: str

    detection_method: str

    blocked: bool = False

    redacted_content: str | None = None


class SecurityScanResponse(BaseModel):

    passed: bool

    risk_level: str

    findings: list[SecurityFinding]
    

class AuthorizationRequest(BaseModel):
    tool_name: str = Field(min_length=1, max_length=150)
    action: str = Field(min_length=1, max_length=150)
    resource: str = Field(min_length=1, max_length=200)

    transaction_amount: float | None = Field(
        default=None,
        ge=0,
    )

    run_id: int | None = Field(
        default=None,
        gt=0,
    )