from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    player_id: UUID
    booking_confirmed: bool
    booking_reminder: bool
    booking_cancelled: bool
    slot_available: bool
    subscription_expiry: bool
    watched_field_ids: list[str]
    created_at: datetime
    updated_at: datetime


class NotificationPreferenceUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    booking_confirmed: bool | None = None
    booking_reminder: bool | None = None
    booking_cancelled: bool | None = None
    slot_available: bool | None = None
    subscription_expiry: bool | None = None
    watched_field_ids: list[str] | None = None
