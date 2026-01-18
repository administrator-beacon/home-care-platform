from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_request_metadata, require_role
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.role import RoleAssign, RoleRead
from app.services.audit import log_event

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[RoleRead])
def list_roles(db: Session = Depends(get_db), current_user: User = Depends(require_role("admin"))) -> list[RoleRead]:
    return db.query(Role).all()


@router.post("/assign")
def assign_role(
    payload: RoleAssign,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> dict:
    user = (
        db.query(User)
        .filter(User.id == payload.user_id, User.agency_id == current_user.agency_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    role = db.query(Role).filter(Role.name == payload.role_name).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    existing = (
        db.query(UserRole)
        .filter(UserRole.user_id == user.id, UserRole.role_id == role.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role already assigned")

    assignment = UserRole(user_id=user.id, role_id=role.id)
    db.add(assignment)
    db.commit()

    metadata = get_request_metadata(request)
    log_event(
        db,
        agency_id=current_user.agency_id,
        actor_user_id=current_user.id,
        event_type="role_assigned",
        resource_type="user",
        resource_id=str(user.id),
        message=f"Assigned role {role.name}",
        **metadata,
    )
    return {"status": "assigned"}
