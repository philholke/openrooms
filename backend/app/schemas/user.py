import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., max_length=255)
    role: Literal["admin", "manager", "staff"] = "staff"


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, max_length=255)
    role: Literal["owner", "admin", "manager", "staff"] | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
