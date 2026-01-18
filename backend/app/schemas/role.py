from pydantic import BaseModel


class RoleRead(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class RoleAssign(BaseModel):
    user_id: int
    role_name: str
