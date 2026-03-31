import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TableRead(BaseModel):
    id: uuid.UUID
    floor_plan_id: uuid.UUID
    label: str
    min_capacity: int
    max_capacity: int
    section: str | None
    x_position: float | None
    y_position: float | None
    shape: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FloorPlanRead(BaseModel):
    id: uuid.UUID
    venue_id: uuid.UUID
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FloorPlanCreate(BaseModel):
    name: str = Field(..., max_length=255)


class TableCreate(BaseModel):
    label: str = Field(..., max_length=100)
    min_capacity: int = Field(1, ge=1)
    max_capacity: int = Field(..., ge=1)
    section: str | None = Field(None, max_length=100)
    x_position: float | None = None
    y_position: float | None = None
    shape: str = Field("rectangle", max_length=50)
