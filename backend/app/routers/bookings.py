"""
Bookings router — booking list, cancel, check-in, verify by reference.

Routes:
  GET    /bookings/me                   — player's bookings list
  GET    /bookings/verify/{reference}   — look up by reference (FIELD_OWNER)
  GET    /bookings/{booking_id}         — booking detail + QR reference
  DELETE /bookings/{booking_id}         — cancel booking (Player, ≥2 hr window)
  POST   /bookings/{booking_id}/checkin — check-in (FIELD_OWNER)

Requirements: 6.5, 6.6, 7.1, 7.2, 7.3, 11.1, 11.2, 11.3
"""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.redis_client import get_redis
from app.schemas.booking import BookingResponse, BookingVerifyResponse, CheckInResponse
from app.services import booking_service
from app.services.auth_service import get_current_user, require_role
from app.models.user import User

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.get("/me", response_model=list[BookingResponse], summary="List my bookings")
async def list_my_bookings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bookings = await booking_service.list_player_bookings(db, current_user.id)
    return [BookingResponse.model_validate(b) for b in bookings]


# NOTE: /verify/{reference} and /me MUST come before /{booking_id}
@router.get(
    "/verify/{reference}",
    response_model=BookingVerifyResponse,
    summary="Look up booking by reference (FIELD_OWNER)",
)
async def verify_booking(
    reference: str,
    current_user: User = Depends(require_role("FIELD_OWNER", "SUPER_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    booking = await booking_service.verify_by_reference(db, reference, current_user.id)
    return BookingVerifyResponse(
        booking_id=booking.id,
        reference=booking.reference,
        player_name=None,  # Could join User table; left as None for now
        status=booking.status,
        slot_date=booking.slot_date,
        start_time=booking.slot_start_time,
        end_time=booking.slot_end_time,
    )


@router.get("/{booking_id}", response_model=BookingResponse, summary="Get booking detail")
async def get_booking(
    booking_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    booking = await booking_service.get_booking(db, booking_id, current_user.id)
    return BookingResponse.model_validate(booking)


@router.delete("/{booking_id}", response_model=BookingResponse, summary="Cancel a booking")
async def cancel_booking(
    booking_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    booking = await booking_service.cancel_booking(db, booking_id, current_user.id, redis)
    return BookingResponse.model_validate(booking)


@router.post(
    "/{booking_id}/checkin",
    response_model=CheckInResponse,
    summary="Check in a player (FIELD_OWNER)",
)
async def check_in(
    booking_id: UUID,
    current_user: User = Depends(require_role("FIELD_OWNER", "SUPER_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    booking, warning = await booking_service.check_in(db, booking_id, current_user.id)
    return CheckInResponse(
        booking_id=booking.id,
        status=booking.status,
        checked_in_at=booking.checked_in_at,
        warning=warning,
    )
