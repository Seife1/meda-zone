"""
Fields router — field discovery, CRUD, sponsorship management.

Routes:
  GET    /fields                      — spatial + filter search (public)
  GET    /fields/{field_id}           — field detail (public)
  POST   /fields                      — create field (FIELD_OWNER, SUPER_ADMIN)
  PUT    /fields/{field_id}           — update field
  PATCH  /fields/{field_id}/status    — activate / deactivate
  PATCH  /fields/{field_id}/sponsor   — set sponsorship (SUPER_ADMIN)

Requirements: 3.1, 9.2, 9.3, 9.4, 9.5, 9.6, 12.4
"""
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.redis_client import get_redis
from app.models.booking import Booking
from app.models.subscription import Subscription
from app.models.slot import Slot
from app.models.user import User
from app.schemas.admin import DailyBookingCount
from app.schemas.field import (
    FieldCreate,
    FieldFilterParams,
    FieldResponse,
    FieldUpdate,
    SponsorshipPatch,
    FieldAnalyticsResponse,
    TodaySlotSummary,
)
from app.services import field_service
from app.services.auth_service import get_current_user, require_role
from app.models.user import User

router = APIRouter(prefix="/fields", tags=["Fields"])


@router.get("", response_model=list[FieldResponse], summary="Discover nearby fields")
async def search_fields(
    params: FieldFilterParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    fields = await field_service.search(
        db=db,
        lat=params.lat,
        lng=params.lng,
        radius_km=params.radius_km,
        surface_type=params.surface_type,
        amenities=params.amenities,
        min_price=params.min_price,
        max_price=params.max_price,
        available_date=params.available_date,
        q=params.q,
    )
    return [FieldResponse.model_validate(f) for f in fields]


@router.get("/{field_id}", response_model=FieldResponse, summary="Get field detail")
async def get_field(
    field_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    field = await field_service.get_field(db, field_id)
    if field is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Field not found."}})
    return FieldResponse.model_validate(field)


@router.post(
    "",
    response_model=FieldResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a field (FIELD_OWNER)",
)
async def create_field(
    body: FieldCreate,
    current_user: User = Depends(require_role("FIELD_OWNER", "SUPER_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    field = await field_service.create_field(db, owner_id=current_user.id, data=body)
    return FieldResponse.model_validate(field)


@router.put("/{field_id}", response_model=FieldResponse, summary="Update a field")
async def update_field(
    field_id: UUID,
    body: FieldUpdate,
    current_user: User = Depends(require_role("FIELD_OWNER", "SUPER_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == "SUPER_ADMIN"
    field = await field_service.update_field(db, field_id, current_user.id, body, is_admin=is_admin)
    return FieldResponse.model_validate(field)


@router.patch("/{field_id}/status", response_model=FieldResponse, summary="Activate or deactivate a field")
async def set_field_status(
    field_id: UUID,
    is_active: bool,
    current_user: User = Depends(require_role("FIELD_OWNER", "SUPER_ADMIN")),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    field = await field_service.set_field_status(db, field_id, is_active, redis)
    return FieldResponse.model_validate(field)


@router.patch("/{field_id}/sponsor", response_model=FieldResponse, summary="Set field sponsorship (SUPER_ADMIN)")
async def set_sponsorship(
    field_id: UUID,
    body: SponsorshipPatch,
    current_user: User = Depends(require_role("SUPER_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    field = await field_service.set_sponsorship(db, field_id, body.sponsorship_start, body.sponsorship_end)
    return FieldResponse.model_validate(field)


@router.get("/{field_id}/analytics", response_model=FieldAnalyticsResponse, summary="Field analytics (FIELD_OWNER)")
async def get_field_analytics(
    field_id: UUID,
    current_user: User = Depends(require_role("FIELD_OWNER", "SUPER_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    field = await field_service.get_field(db, field_id)
    if not field:
        raise HTTPException(status_code=404, detail="Field not found.")
    if current_user.role != "SUPER_ADMIN" and field.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized.")

    today = date.today()
    thirty_days_ago = today - timedelta(days=30)

    # Total bookings last 30 days
    bookings_result = await db.execute(
        select(func.count(Booking.id)).where(
            Booking.field_id == field_id,
            Booking.slot_date >= thirty_days_ago,
            Booking.status != "cancelled",
        )
    )
    total_bookings_30d: int = bookings_result.scalar() or 0

    # Total revenue last 30 days (Subscriptions only for now)
    revenue_result = await db.execute(
        select(func.sum(Subscription.total_price)).where(
            Subscription.field_id == field_id,
            Subscription.status == "active",
            Subscription.start_date >= thirty_days_ago,
        )
    )
    from decimal import Decimal
    total_revenue_30d: Decimal = revenue_result.scalar() or Decimal("0.00")

    # Daily booking counts
    daily_result = await db.execute(
        select(Booking.slot_date, func.count(Booking.id))
        .where(
            Booking.field_id == field_id,
            Booking.slot_date >= thirty_days_ago,
            Booking.status != "cancelled",
        )
        .group_by(Booking.slot_date)
        .order_by(Booking.slot_date.asc())
    )
    daily_bookings = [
        DailyBookingCount(date=row[0], count=row[1])
        for row in daily_result.all()
    ]

    return FieldAnalyticsResponse(
        total_bookings_30d=total_bookings_30d,
        total_revenue_30d=total_revenue_30d,
        daily_bookings=daily_bookings,
    )


@router.get("/{field_id}/today", response_model=list[TodaySlotSummary], summary="Command Center view for today")
async def get_field_today(
    field_id: UUID,
    current_user: User = Depends(require_role("FIELD_OWNER", "SUPER_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    field = await field_service.get_field(db, field_id)
    if not field:
        raise HTTPException(status_code=404, detail="Field not found.")
    if current_user.role != "SUPER_ADMIN" and field.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized.")

    today = date.today()

    # Get all slots for today
    slots_result = await db.execute(
        select(Slot).where(
            Slot.field_id == field_id,
            Slot.slot_date == today,
        ).order_by(Slot.start_time)
    )
    slots = slots_result.scalars().all()

    # Get all bookings for today
    bookings_result = await db.execute(
        select(Booking, User).join(User, Booking.player_id == User.id).where(
            Booking.field_id == field_id,
            Booking.slot_date == today,
            Booking.status != "cancelled",
        )
    )
    
    booking_map = {}
    for booking, player in bookings_result.all():
        booking_map[booking.slot_id] = {
            "booking_id": booking.id,
            "player_name": player.display_name or player.phone_number,
        }

    summaries = []
    for slot in slots:
        b_info = booking_map.get(slot.id, {})
        summaries.append(TodaySlotSummary(
            id=slot.id,
            start_time=slot.start_time,
            end_time=slot.end_time,
            status=slot.status,
            booking_id=b_info.get("booking_id"),
            player_name=b_info.get("player_name"),
        ))

    return summaries
