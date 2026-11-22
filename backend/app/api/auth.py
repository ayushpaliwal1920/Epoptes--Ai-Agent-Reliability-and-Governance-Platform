
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db.model import Organization, User
from ..schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse
)
from ..core.security import (
    hash_password,
    verify_password,
    create_access_token
)
from .dependencies import get_current_admin
from ..services.audit import create_audit_event


router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db)
):
    email = str(data.email).lower()

    existing = db.query(User).filter(
        User.email == email
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    organization = Organization(name=data.organization_name)

    db.add(organization)
    db.flush()

    user = User(
        organization_id=organization.id,
        email=email,
        password_hash=hash_password(data.password),
        role="admin"
    )

    db.add(user)
    db.flush()

    create_audit_event(
        db,
        organization_id=organization.id,
        actor_user_id=user.id,
        action="organization.registered",
        resource_type="organization",
        resource_id=organization.id
    )

    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    email = str(data.email).lower()

    user = db.query(User).filter(
        User.email == email
    ).first()

    if not user or not verify_password(
        data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
        )

    token = create_access_token(
        user_id=user.id,
        organization_id=user.organization_id
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@router.get("/organization")
def get_organization(
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    organization = db.query(Organization).filter(
        Organization.id == user.organization_id
    ).first()

    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found"
        )

    return {
        "id": organization.id,
        "name": organization.name,
        "created_at": organization.created_at
    }
