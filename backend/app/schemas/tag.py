import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class TagCreate(BaseModel):
    name: str = Field(..., max_length=255)
    color: str | None = Field(None, max_length=7)
    is_auto: bool = False
    description: str | None = Field(None, max_length=2000)

    @field_validator("color")
    @classmethod
    def _validate_hex_color(cls, v: str | None) -> str | None:
        if v is not None:
            import re
            if not re.match(r"^#[0-9A-Fa-f]{6}$", v):
                raise ValueError("color must be a hex color code (e.g. #FF5733)")
        return v


class TagUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    color: str | None = Field(None, max_length=7)
    description: str | None = Field(None, max_length=2000)

    @field_validator("color")
    @classmethod
    def _validate_hex_color(cls, v: str | None) -> str | None:
        if v is not None:
            import re
            if not re.match(r"^#[0-9A-Fa-f]{6}$", v):
                raise ValueError("color must be a hex color code (e.g. #FF5733)")
        return v


class TagRead(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    color: str | None
    is_auto: bool
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
