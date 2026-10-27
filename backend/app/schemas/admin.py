from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserCreateByAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    phone_number: str
    display_name: str | None = None
    role: Literal["FIELD_OWNER", "SUPER_ADMIN"]


class UserUpdateByAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    phone_number: str | None = None
    display_name: str | None = None
    role: Literal["FIELD_OWNER", "SUPER_ADMIN"] | None = None
    is_active: bool | None = None


class DailyBookingCount(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    count: int


class AnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_active_fields: int
    total_bookings_30d: int
    daily_bookings: list[DailyBookingCount]


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    phone_number: str
    display_name: str | None
    role: str
    is_active: bool
    created_at: datetime


class UserCreateResponse(UserResponse):
    temp_password: str
