from datetime import date, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    field_id: UUID
    slot_date: date
    start_time: time
    end_time: time
    duration_minutes: int
    status: str


class SlotGenerateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start_date: date
    end_date: date
    slot_duration_minutes: Literal[30, 60, 90]
    open_time: str  # HH:MM format
    close_time: str  # HH:MM format


class SlotGenerateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    created_count: int
    skipped_count: int


class SlotStatusPatch(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: Literal["available", "closed"]


class SlotUpdateMessage(BaseModel):
    """WebSocket message payload for slot status updates."""

    model_config = ConfigDict(from_attributes=True)

    type: str = "slot_update"
    slot_id: str
    status: str
    slot_date: str
    start_time: str
    end_time: str
