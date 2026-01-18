from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_request_metadata, revoke_refresh_token, store_refresh_token
from app.core.config import settings
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest
from app.schemas.token import Token
from app.services.audit import log_event
from app.services.security import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> Token:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        metadata = get_request_metadata(request)
        log_event(
            db,
            agency_id=user.agency_id if user else None,
            actor_user_id=user.id if user else None,
            event_type="auth_failure",
            message="Invalid credentials",
            **metadata,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    refresh_token = create_refresh_token(
        subject=str(user.id),
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )
    store_refresh_token(db, user.id, refresh_token, settings.refresh_token_expire_days)
    metadata = get_request_metadata(request)
    log_event(
        db,
        agency_id=user.agency_id,
        actor_user_id=user.id,
        event_type="auth_success",
        message="User logged in",
        **metadata,
    )
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
def refresh_token(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)) -> Token:
    try:
        token_payload = jwt.decode(payload.refresh_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if token_payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        user_id = int(token_payload.get("sub"))
    except (JWTError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    token_hash = hash_refresh_token(payload.refresh_token)
    stored = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
        .first()
    )
    if not stored or stored.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")

    revoke_refresh_token(db, payload.refresh_token)

    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    new_refresh_token = create_refresh_token(
        subject=str(user.id),
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )
    store_refresh_token(db, user.id, new_refresh_token, settings.refresh_token_expire_days)

    metadata = get_request_metadata(request)
    log_event(
        db,
        agency_id=user.agency_id,
        actor_user_id=user.id,
        event_type="auth_refresh",
        message="Refresh token rotated",
        **metadata,
    )
    return Token(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/logout")
def logout(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    revoke_refresh_token(db, payload.refresh_token)
    metadata = get_request_metadata(request)
    log_event(
        db,
        agency_id=None,
        actor_user_id=None,
        event_type="auth_logout",
        message="User logged out",
        **metadata,
    )
    return {"status": "ok"}
