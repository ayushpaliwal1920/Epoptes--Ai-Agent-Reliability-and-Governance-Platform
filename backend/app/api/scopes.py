from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.model import Agent, AgentScope
from app.api.dependencies import get_current_user

from app.schemas.scope import (
    AgentScopeCreate,
    AgentScopeResponse
)
from app.api.dependencies import get_current_admin

router = APIRouter(
    prefix="/api/v1/agents",
    tags=["Agent Scopes"]
)


@router.post("/{agent_id}/scopes")
def create_agent_scope(
    agent_id: int,
    payload: AgentScopeCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):

    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.organization_id == current_user.organization_id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agent not found"
        )

    existing = db.query(AgentScope).filter(
        AgentScope.agent_id == agent_id,
        AgentScope.organization_id == current_user.organization_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Scope already exists. Use PUT to update."
        )

    scope = AgentScope(
        organization_id=current_user.organization_id,
        agent_id=agent_id,
        **payload.model_dump()
    )

    db.add(scope)
    db.commit()
    db.refresh(scope)

    return scope


@router.get("/{agent_id}/scopes")
def get_agent_scope(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    scope = db.query(AgentScope).filter(
        AgentScope.agent_id == agent_id,
        AgentScope.organization_id == current_user.organization_id
    ).first()

    if not scope:
        raise HTTPException(
            status_code=404,
            detail="Agent scope not configured"
        )

    return scope


@router.put("/{agent_id}/scopes")
def update_agent_scope(
    agent_id: int,
    payload: AgentScopeCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):

    scope = db.query(AgentScope).filter(
        AgentScope.agent_id == agent_id,
        AgentScope.organization_id == current_user.organization_id
    ).first()

    if not scope:
        raise HTTPException(
            status_code=404,
            detail="Agent scope not found"
        )

    for key, value in payload.model_dump().items():
        setattr(scope, key, value)

    db.commit()
    db.refresh(scope)

    return scope