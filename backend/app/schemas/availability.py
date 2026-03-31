import uuid
from datetime import date, time

from pydantic import BaseModel


class AvailableSlot(BaseModel):
    time: time
    access_rule_id: uuid.UUID
    access_rule_name: str


class AvailabilityResponse(BaseModel):
    venue_id: uuid.UUID
    date: date
    party_size: int
    slots: list[AvailableSlot]
