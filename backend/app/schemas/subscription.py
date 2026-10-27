from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SubscriptionCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: UUID
    field_id: UUID
    recurring_days: list[str]
    session_start_time: time
    session_duration_hours: Decimal
    tier: Literal["1_month", "2_months", "3_months"]


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    player_id: UUID
    field_id: UUID
    proposed_by: UUID
    recurring_days: list[str]
    session_start_time: time
    session_duration_hours: Decimal
    tier: str
    total_sessions: int
    total_price: Decimal
    status: str
    start_date: date | None
    expiry_date: date | None
    payment_provider: str | None
    payment_tx_ref: str | None
    created_at: datetime
    updated_at: datetime


class SlotChangeProposalCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    new_recurring_days: list[str]
    new_session_start_time: time
    new_session_duration_hours: Decimal


class SlotChangeProposalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subscription_id: UUID
    proposed_by: UUID
    new_recurring_days: list[str]
    new_session_start_time: time
    new_session_duration_hours: Decimal
    status: str
    expires_at: datetime


class SlotChangeApproval(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    approved: bool


class SubscriptionStatsItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    field_id: UUID
    field_name: str
    active_count: int


class SubscriptionStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    by_tier: dict[str, int]
    by_field: list[SubscriptionStatsItem]
