from datetime import date, time
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas.admin import DailyBookingCount


class SlotSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slot_date: date
    start_time: time
    end_time: time
    status: str


class FieldCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    address: str
    neighborhood: str | None = None
    lat: float
    lng: float
    surface_type: Literal["grass", "artificial", "futsal"]
    field_size: str | None = None
    amenities: dict = Field(default_factory=dict)
    price_per_hour: Decimal
    operating_hours: dict = Field(default_factory=dict)
    photo_urls: list[str] = Field(default_factory=list)


class FieldUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str | None = None
    address: str | None = None
    neighborhood: str | None = None
    lat: float | None = None
    lng: float | None = None
    surface_type: Literal["grass", "artificial", "futsal"] | None = None
    field_size: str | None = None
    amenities: dict | None = None
    price_per_hour: Decimal | None = None
    operating_hours: dict | None = None
    photo_urls: list[str] | None = None


class FieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    name: str
    address: str
    neighborhood: str | None = None
    lat: float | None = None
    lng: float | None = None
    surface_type: str
    field_size: str | None = None
    amenities: dict
    price_per_hour: Decimal
    operating_hours: dict
    photo_urls: list[str]
    average_rating: Decimal
    review_count: int
    is_active: bool
    is_sponsored: bool
    sponsorship_start: date | None = None
    sponsorship_end: date | None = None
    distance_km: float | None = None
    next_available_slot: SlotSummary | None = None

    @model_validator(mode="before")
    @classmethod
    def extract_location(cls, data: Any) -> Any:
        """
        Extract lat/lng from a GeoAlchemy2 WKBElement or a plain dict.
        Handles both ORM model instances and raw dict data.
        """
        # If data is an ORM object with a 'location' attribute
        if hasattr(data, "location") and data.location is not None:
            try:
                from geoalchemy2.shape import to_shape
                point = to_shape(data.location)
                # Build a dict from the ORM object so we can add lat/lng
                obj_dict = {
                    col: getattr(data, col)
                    for col in data.__class__.__table__.columns.keys()
                    if col != "location"
                }
                obj_dict["lat"] = point.y
                obj_dict["lng"] = point.x
                # Carry over computed fields if present
                if hasattr(data, "distance_km"):
                    obj_dict["distance_km"] = data.distance_km
                if hasattr(data, "next_available_slot"):
                    obj_dict["next_available_slot"] = data.next_available_slot
                return obj_dict
            except Exception:
                pass
        # If it's a dict with a 'location' key we skip it (already stripped)
        return data


class FieldSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    surface_type: str
    price_per_hour: Decimal
    distance_km: float | None = None
    average_rating: Decimal
    is_sponsored: bool
    next_available_slot: SlotSummary | None = None


class SponsorshipPatch(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sponsorship_start: date
    sponsorship_end: date


class FieldFilterParams(BaseModel):
    """Query parameters model for field discovery / search endpoint."""

    model_config = ConfigDict(from_attributes=True)

    lat: float | None = None
    lng: float | None = None
    radius_km: float = 10.0
    surface_type: str | None = None
    amenities: str | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    available_date: date | None = None
    q: str | None = None


class FieldAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_bookings_30d: int
    total_revenue_30d: Decimal
    daily_bookings: list[DailyBookingCount]


class TodaySlotSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    start_time: time
    end_time: time
    status: str
    booking_id: UUID | None = None
    player_name: str | None = None
