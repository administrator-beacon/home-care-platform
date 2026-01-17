from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_request_metadata, require_role
from app.models.user import User
from app.schemas.user import UserRead
from app.services.audit import PHI_EVENT, log_event

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_me(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    metadata = get_request_metadata(request)
    log_event(
        db,
        agency_id=current_user.agency_id,
        actor_user_id=current_user.id,
        event_type=PHI_EVENT,
        resource_type="user",
        resource_id=str(current_user.id),
        message="User accessed own profile",
        **metadata,
    )
    return current_user


@router.get("", response_model=list[UserRead])
def list_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> list[UserRead]:
    users = db.query(User).filter(User.agency_id == current_user.agency_id).all()
    metadata = get_request_metadata(request)
    log_event(
        db,
        agency_id=current_user.agency_id,
        actor_user_id=current_user.id,
        event_type=PHI_EVENT,
        resource_type="user",
        message="Admin listed users",
        **metadata,
    )
    return users


@router.get("/{user_id}", response_model=UserRead)
def read_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> UserRead:
    user = (
        db.query(User)
        .filter(User.id == user_id, User.agency_id == current_user.agency_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    metadata = get_request_metadata(request)
    log_event(
        db,
        agency_id=current_user.agency_id,
        actor_user_id=current_user.id,
        event_type=PHI_EVENT,
        resource_type="user",
        resource_id=str(user.id),
        message="Admin viewed user profile",
        **metadata,
    )
    return user
