import uuid
from datetime import date

from pydantic import BaseModel


class PacingSlot(BaseModel):
    time: str
    booked_covers: int
    capacity: int


class PacingResponse(BaseModel):
    venue_id: uuid.UUID
    date: date
    total_capacity: int
    slots: list[PacingSlot]
