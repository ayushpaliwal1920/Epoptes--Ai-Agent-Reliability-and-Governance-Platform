
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt

from fastapi import Header
from ..db.database import get_db
from ..db.model import User, Agent, AgentCredential
from ..core.security import (
    decode_access_token,
    hash_agent_api_key
)


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    try:
        payload = decode_access_token(credentials.credentials)

        user_id = int(payload["sub"])
        organization_id = int(payload["org_id"])

    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    user = db.query(User).filter(
        User.id == user_id,
        User.organization_id == organization_id,
        User.is_active.is_(True)
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found or inactive"
        )

    return user


def get_current_admin(
    user: User = Depends(get_current_user)
):
    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Administrator access required"
        )

    return user


def get_current_agent(
    x_agent_key: str | None = Header(default=None, alias="X-Agent-Key"),
    db: Session = Depends(get_db)
):
    if not x_agent_key:
        raise HTTPException(
            status_code=401,
            detail="Agent API key required"
        )

    key_hash = hash_agent_api_key(x_agent_key)

    credential = db.query(AgentCredential).filter(
        AgentCredential.key_hash == key_hash,
        AgentCredential.is_active.is_(True)
    ).first()

    if not credential:
        raise HTTPException(
            status_code=401,
            detail="Invalid or revoked agent API key"
        )

    agent = db.query(Agent).filter(
        Agent.id == credential.agent_id,
        Agent.is_active.is_(True)
    ).first()

    if not agent:
        raise HTTPException(
            status_code=401,
            detail="Agent is inactive"
        )

    return agent
