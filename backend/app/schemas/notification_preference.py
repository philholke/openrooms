import uuid
from datetime import datetime

from pydantic import BaseModel


NOTIFICATION_TYPES = [
    "reservation_confirmed",
    "reservation_reminder",
    "survey_invite",
    "cancellation_ack",
    "pre_shift_report",
]


class NotificationPreferenceRead(BaseModel):
    id: uuid.UUID
    venue_id: uuid.UUID
    notification_type: str
    enabled: bool

    model_config = {"from_attributes": True}


class NotificationPreferenceUpdate(BaseModel):
    notification_type: str
    enabled: bool
