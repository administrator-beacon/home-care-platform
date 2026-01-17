import os

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.agency import Agency
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.services.security import get_password_hash


def get_or_create_role(db: Session, name: str) -> Role:
    role = db.query(Role).filter(Role.name == name).first()
    if not role:
        role = Role(name=name)
        db.add(role)
        db.commit()
        db.refresh(role)
    return role


def main() -> None:
    agency_name = os.environ.get("SEED_AGENCY_NAME", "Acme Home Care")
    admin_email = os.environ.get("SEED_ADMIN_EMAIL", "admin@acme.test")
    admin_password = os.environ.get("SEED_ADMIN_PASSWORD", "ChangeMe123!")

    db = SessionLocal()
    try:
        agency = db.query(Agency).filter(Agency.name == agency_name).first()
        if not agency:
            agency = Agency(name=agency_name)
            db.add(agency)
            db.commit()
            db.refresh(agency)

        admin_role = get_or_create_role(db, "admin")
        get_or_create_role(db, "clinician")

        user = db.query(User).filter(User.email == admin_email).first()
        if not user:
            user = User(
                agency_id=agency.id,
                email=admin_email,
                hashed_password=get_password_hash(admin_password),
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        assignment = (
            db.query(UserRole)
            .filter(UserRole.user_id == user.id, UserRole.role_id == admin_role.id)
            .first()
        )
        if not assignment:
            db.add(UserRole(user_id=user.id, role_id=admin_role.id))
            db.commit()

        print("Seeded agency and admin user")
    finally:
        db.close()


if __name__ == "__main__":
    main()
