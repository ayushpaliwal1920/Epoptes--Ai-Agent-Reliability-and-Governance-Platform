
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db.model import Agent, AgentCredential, User
from ..schemas.agents import (
    AgentCreate,
    AgentResponse,
    AgentCreatedResponse,
    AgentKeyResponse
)
from .dependencies import (
    get_current_admin,
    get_current_agent
)
from ..core.security import (
    generate_agent_api_key,
    hash_agent_api_key
)
from ..services.audit import create_audit_event


router = APIRouter(
    prefix="/api/v1/agents",
    tags=["Agent Management"]
)


# 1. Register an agent
@router.post(
    "",
    response_model=AgentCreatedResponse,
    status_code=201
)
def create_agent(
    data: AgentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin)
):
    agent = Agent(
        organization_id=user.organization_id,
        name=data.name,
        description=data.description,
        framework=data.framework,
        integration_type=data.integration_type,
        environment=data.environment,
        risk_level=data.risk_level,
        owner=data.owner
    )

    db.add(agent)
    db.flush()

    raw_key = generate_agent_api_key()

    credential = AgentCredential(
        agent_id=agent.id,
        key_hash=hash_agent_api_key(raw_key)
    )

    db.add(credential)

    create_audit_event(
        db,
        organization_id=user.organization_id,
        actor_user_id=user.id,
        action="agent.created",
        resource_type="agent",
        resource_id=agent.id,
        details={"name": agent.name}
    )

    db.commit()
    db.refresh(agent)

    return {
        "agent": agent,
        "api_key": raw_key
    }


# 2. List agents belonging to the logged-in organization
@router.get("", response_model=list[AgentResponse])
def list_agents(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin)
):
    return (
        db.query(Agent)
        .filter(Agent.organization_id == user.organization_id)
        .order_by(Agent.id.desc())
        .all()
    )


# 3. Agent self-authentication endpoint
# Keep this route BEFORE /{agent_id}.
@router.get("/me", response_model=AgentResponse)
def get_my_agent(
    agent: Agent = Depends(get_current_agent)
):
    return agent


# 4. Get a specific agent
@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin)
):
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.organization_id == user.organization_id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agent not found"
        )

    return agent


# 5. Deactivate an agent and revoke its credentials
@router.patch("/{agent_id}/deactivate")
def deactivate_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin)
):
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.organization_id == user.organization_id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agent not found"
        )

    if not agent.is_active:
        return {"message": "Agent is already inactive"}

    agent.is_active = False

    credentials = db.query(AgentCredential).filter(
        AgentCredential.agent_id == agent.id,
        AgentCredential.is_active.is_(True)
    ).all()

    now = datetime.now(timezone.utc)

    for credential in credentials:
        credential.is_active = False
        credential.revoked_at = now

    create_audit_event(
        db,
        organization_id=user.organization_id,
        actor_user_id=user.id,
        action="agent.deactivated",
        resource_type="agent",
        resource_id=agent.id
    )

    db.commit()

    return {"message": "Agent deactivated and credentials revoked"}


# 6. Rotate API key
@router.post(
    "/{agent_id}/rotate-key",
    response_model=AgentKeyResponse
)
def rotate_agent_key(
    agent_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin)
):
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.organization_id == user.organization_id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agent not found"
        )

    if not agent.is_active:
        raise HTTPException(
            status_code=400,
            detail="Cannot rotate key for inactive agent"
        )

    credentials = db.query(AgentCredential).filter(
        AgentCredential.agent_id == agent.id,
        AgentCredential.is_active.is_(True)
    ).all()

    now = datetime.now(timezone.utc)

    for credential in credentials:
        credential.is_active = False
        credential.revoked_at = now

    raw_key = generate_agent_api_key()

    new_credential = AgentCredential(
        agent_id=agent.id,
        key_hash=hash_agent_api_key(raw_key)
    )

    db.add(new_credential)

    create_audit_event(
        db,
        organization_id=user.organization_id,
        actor_user_id=user.id,
        action="agent.key_rotated",
        resource_type="agent",
        resource_id=agent.id
    )

    db.commit()

    return {
        "agent_id": agent.id,
        "api_key": raw_key,
        "message": "API key rotated successfully. Save this key now."
    }
