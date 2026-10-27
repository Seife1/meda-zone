from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reference: str
    player_id: UUID
    field_id: UUID
    slot_id: UUID
    subscription_id: UUID | None
    slot_date: date
    slot_start_time: time
    slot_end_time: time
    status: str
    cancellation_reason: str | None
    cancelled_at: datetime | None
    checked_in_at: datetime | None
    created_at: datetime


class CheckInResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    booking_id: UUID
    status: str
    checked_in_at: datetime
    warning: str | None = None


class BookingVerifyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    booking_id: UUID
    reference: str
    player_name: str | None
    status: str
    slot_date: date
    start_time: time
    end_time: time
