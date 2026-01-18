from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr


class UserRead(UserBase):
    id: int
    agency_id: int
    is_active: bool

    class Config:
        from_attributes = True
