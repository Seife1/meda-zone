"""
field_service.py — Business logic for Field CRUD, spatial search,
sponsorship management, and field deactivation.

All DB access uses SQLAlchemy 2.0 async sessions.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from geoalchemy2 import Geography
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import and_, cast, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.field import Field
from app.models.slot import Slot
from app.models.user import User
from app.schemas.field import FieldCreate, FieldUpdate

logger = logging.getLogger(__name__)

# Default centre: Addis Ababa (lat, lng)
_DEFAULT_LAT = 9.0054
_DEFAULT_LNG = 38.7636


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _geography_point(lat: float, lng: float):
    """Return a PostGIS geography literal for the given coordinates."""
    return func.ST_GeogFromText(f"SRID=4326;POINT({lng} {lat})")


def _to_location(lat: float, lng: float):
    """Convert float lat/lng to a GeoAlchemy2 WKBElement (SRID 4326)."""
    return from_shape(Point(lng, lat), srid=4326)


# ---------------------------------------------------------------------------
# 1. Search
# ---------------------------------------------------------------------------

async def search(
    db: AsyncSession,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_km: float = 10.0,
    surface_type: Optional[str] = None,
    amenities: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    available_date: Optional[date] = None,
    q: Optional[str] = None,
) -> list[Field]:
    """
    Spatially-filtered field discovery.

    Requirements: 3.1, 3.2, 3.5, 14.1, 14.2, 14.3
    """
    # Use provided coordinates or fall back to Addis Ababa centre
    centre_lat = lat if lat is not None else _DEFAULT_LAT
    centre_lng = lng if lng is not None else _DEFAULT_LNG

    geography_point = _geography_point(centre_lat, centre_lng)

    # Base statement: fields within radius, ordered sponsored-first then by distance
    stmt = (
        select(
            Field,
            func.ST_Distance(
                cast(Field.location, Geography),
                geography_point,
            ).label("distance_meters"),
        )
        .where(
            func.ST_DWithin(
                cast(Field.location, Geography),
                geography_point,
                radius_km * 1000,
            )
        )
        .where(Field.is_active == True)  # noqa: E712
    )

    # ── Optional filter predicates ────────────────────────────────────────

    if surface_type is not None:
        stmt = stmt.where(Field.surface_type == surface_type)

    if amenities:
        for amenity in amenities.split(","):
            amenity = amenity.strip()
            if amenity:
                # JSONB key access: field.amenities->>amenity = 'true'
                stmt = stmt.where(
                    Field.amenities[amenity].astext == "true"
                )

    if min_price is not None:
        stmt = stmt.where(Field.price_per_hour >= min_price)

    if max_price is not None:
        stmt = stmt.where(Field.price_per_hour <= max_price)

    if available_date is not None:
        # Only return fields that have at least one available slot on this date
        stmt = stmt.where(
            Field.id.in_(
                select(Slot.field_id)
                .where(
                    and_(
                        Slot.slot_date == available_date,
                        Slot.status == "available",
                    )
                )
                .scalar_subquery()
            )
        )

    if q is not None and q.strip():
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Field.name.ilike(pattern),
                Field.neighborhood.ilike(pattern),
            )
        )

    # ── Sort: sponsored first, then nearest ──────────────────────────────
    stmt = stmt.order_by(
        Field.is_sponsored.desc(),
        func.ST_Distance(
            cast(Field.location, Geography),
            geography_point,
        ).asc(),
    )

    result = await db.execute(stmt)
    rows = result.all()  # list of (Field, distance_meters)

    # Attach distance_km as a dynamic attribute on each Field instance
    fields: list[Field] = []
    for field, distance_meters in rows:
        field.distance_km = round(distance_meters / 1000, 3) if distance_meters is not None else None
        fields.append(field)

    return fields


# ---------------------------------------------------------------------------
# 2. Get single field
# ---------------------------------------------------------------------------

async def get_field(db: AsyncSession, field_id: UUID) -> Optional[Field]:
    """
    Return a single Field by primary key, or None if not found.

    Requirements: 3.1
    """
    result = await db.execute(select(Field).where(Field.id == field_id))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# 3. Create field
# ---------------------------------------------------------------------------

async def create_field(
    db: AsyncSession,
    owner_id: UUID,
    data: FieldCreate,
) -> Field:
    """
    Persist a new Field owned by owner_id.

    Requirements: 9.2, 9.3
    """
    field = Field(
        owner_id=owner_id,
        name=data.name,
        address=data.address,
        neighborhood=data.neighborhood,
        location=_to_location(data.lat, data.lng),
        surface_type=data.surface_type,
        field_size=data.field_size,
        amenities=data.amenities,
        price_per_hour=data.price_per_hour,
        operating_hours=data.operating_hours,
        photo_urls=data.photo_urls,
    )
    db.add(field)
    await db.commit()
    await db.refresh(field)
    logger.info("Field created: id=%s owner=%s name=%s", field.id, owner_id, field.name)
    return field


# ---------------------------------------------------------------------------
# 4. Update field
# ---------------------------------------------------------------------------

async def update_field(
    db: AsyncSession,
    field_id: UUID,
    owner_id: UUID,
    data: FieldUpdate,
    is_admin: bool = False,
) -> Field:
    """
    Update mutable Field attributes.

    Only the field's owner (or a super admin) may update it.
    Requirements: 9.4
    """
    field = await get_field(db, field_id)
    if field is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Field not found.",
        )

    if not is_admin and field.owner_id != owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this field.",
        )

    # Apply only the provided (non-None) fields
    update_data = data.model_dump(exclude_none=True)

    # Convert lat/lng → WKBElement when both are present in the patch
    lat = update_data.pop("lat", None)
    lng = update_data.pop("lng", None)
    if lat is not None and lng is not None:
        update_data["location"] = _to_location(lat, lng)

    for key, value in update_data.items():
        setattr(field, key, value)

    await db.commit()
    await db.refresh(field)
    logger.info("Field updated: id=%s", field_id)
    return field


# ---------------------------------------------------------------------------
# 5. Set field active / inactive
# ---------------------------------------------------------------------------

async def set_field_status(
    db: AsyncSession,
    field_id: UUID,
    is_active: bool,
    redis,
) -> Field:
    """
    Activate or deactivate a Field.

    When deactivating:
    - All future *available* slots are closed.
    - Players with upcoming confirmed bookings receive a cancellation notification.

    Requirements: 9.5
    """
    # Import notification_service here to avoid circular imports at module level
    from app.services import notification_service  # noqa: PLC0415

    field = await get_field(db, field_id)
    if field is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Field not found.",
        )

    if not is_active and field.is_active:
        today = date.today()

        # ── 1. Close all future available slots ───────────────────────────
        await db.execute(
            update(Slot)
            .where(
                and_(
                    Slot.field_id == field_id,
                    Slot.slot_date >= today,
                    Slot.status == "available",
                )
            )
            .values(status="closed")
        )

        # ── 2. Find players with upcoming confirmed bookings ───────────────
        upcoming_bookings_result = await db.execute(
            select(Booking)
            .where(
                and_(
                    Booking.field_id == field_id,
                    Booking.status == "confirmed",
                    Booking.slot_date >= today,
                )
            )
        )
        upcoming_bookings: list[Booking] = upcoming_bookings_result.scalars().all()

        # ── 3. Cancel those bookings and notify players ───────────────────
        if upcoming_bookings:
            player_ids = list({b.player_id for b in upcoming_bookings})
            players_result = await db.execute(
                select(User).where(User.id.in_(player_ids))
            )
            players_by_id: dict[UUID, User] = {
                u.id: u for u in players_result.scalars().all()
            }

            for booking in upcoming_bookings:
                booking.status = "cancelled"
                booking.cancellation_reason = "field_owner_initiated"

                player = players_by_id.get(booking.player_id)
                if player and player.fcm_token:
                    try:
                        await notification_service.send_booking_cancelled(
                            token=player.fcm_token,
                            booking=booking,
                            field_name=field.name,
                            reason="field_owner_initiated",
                        )
                    except Exception as exc:
                        logger.error(
                            "Failed to send cancellation notification for booking %s: %s",
                            booking.id,
                            exc,
                        )

    field.is_active = is_active
    await db.commit()
    await db.refresh(field)
    logger.info("Field %s set is_active=%s", field_id, is_active)
    return field


# ---------------------------------------------------------------------------
# 6. Set sponsorship
# ---------------------------------------------------------------------------

async def set_sponsorship(
    db: AsyncSession,
    field_id: UUID,
    start_date: date,
    end_date: date,
) -> Field:
    """
    Apply a sponsorship window to a Field.

    Requirements: 9.6, 14.1
    """
    field = await get_field(db, field_id)
    if field is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Field not found.",
        )

    field.is_sponsored = True
    field.sponsorship_start = start_date
    field.sponsorship_end = end_date

    await db.commit()
    await db.refresh(field)
    logger.info(
        "Sponsorship set: field=%s start=%s end=%s",
        field_id,
        start_date,
        end_date,
    )
    return field
