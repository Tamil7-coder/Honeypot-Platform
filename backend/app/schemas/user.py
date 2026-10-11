import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import RoleName


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    full_name: str
    email: EmailStr
    is_active: bool
    is_email_verified: bool
    role: RoleName
    created_at: datetime
    last_login_at: datetime | None = None


class UserCreate(BaseModel):
    username: str
    full_name: str
    email: EmailStr
    password: str
    role: RoleName = RoleName.VIEWER
