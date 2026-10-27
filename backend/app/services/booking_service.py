"""
booking_service.py — Business logic for booking lifecycle:
auto-generation from subscriptions, cancellation, and check-in.

Requirements: 6.1, 6.2, 6.4, 6.5, 6.7, 6.8, 7.1, 7.3, 7.4, 7.6,
              11.2, 11.3, 11.4
"""
from __future__ import annotations

import logging
import secrets
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import asyncpg
from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.field import Field
from app.models.slot import Slot
from app.models.subscription import Subscription
from app.models.user import User

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DAY_NAME_TO_WEEKDAY: dict[str, int] = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}


# ---------------------------------------------------------------------------
# 1. Reference generation  (Requirement 6.1)
# ---------------------------------------------------------------------------


def generate_reference(slot_date: date) -> str:
    """
    Generate a unique booking reference in the format MZ-{YYYYMMDD}-{4CHAR}.

    Example: MZ-20250714-AB4F

    Requirements: 6.1
    """
    date_part = slot_date.strftime("%Y%m%d")
    random_part = secrets.token_hex(2).upper()  # 4 hex chars
    return f"MZ-{date_part}-{random_part}"


# ---------------------------------------------------------------------------
# 2. Session date calculation  (Requirement 6.2)
# ---------------------------------------------------------------------------


def get_session_dates(
    start_date: date,
    expiry_date: date,
    recurring_days: list[str],
) -> list[date]:
    """
    Return all dates between start_date and expiry_date (inclusive) whose
    weekday matches any day in recurring_days.

    Requirements: 6.2
    """
    target_weekdays = {
        DAY_NAME_TO_WEEKDAY[day]
        for day in recurring_days
        if day in DAY_NAME_TO_WEEKDAY
    }

    session_dates: list[date] = []
    current = start_date
    while current <= expiry_date:
        if current.weekday() in target_weekdays:
            session_dates.append(current)
        current += timedelta(days=1)

    return session_dates


# ---------------------------------------------------------------------------
# 3. Bulk booking generation  (Requirements 6.4, 6.5, 6.7, 6.8, 11.2)
# ---------------------------------------------------------------------------


async def generate_bookings_for_subscription(
    db: AsyncSession,
    subscription: Subscription,
    redis,
) -> list[Booking]:
    """
    Auto-generate Booking records for every session date in the subscription period.

    For each session date:
      - Find or create the Slot for (field_id, session_date, session_start_time).
      - Skip slots whose status is already 'booked'.
      - Create a Booking with a unique reference, status='confirmed', and the
        subscription_id.
      - Mark the slot as 'booked'.
      - Publish a WebSocket update via slot_service._publish_slot_update.

    Raises 409 DUPLICATE_BOOKING on asyncpg.UniqueViolationError.
    Returns the list of created Booking objects.

    Requirements: 6.4, 6.5, 6.7, 6.8, 11.2
    """
    from app.services.slot_service import _publish_slot_update  # avoid circular

    if subscription.start_date is None or subscription.expiry_date is None:
        logger.warning(
            "generate_bookings_for_subscription: subscription %s has no date range",
            subscription.id,
        )
        return []

    session_dates = get_session_dates(
        subscription.start_date,
        subscription.expiry_date,
        subscription.recurring_days,
    )

    session_start = subscription.session_start_time
    duration_hours = float(subscription.session_duration_hours)
    duration_minutes = int(duration_hours * 60)

    # Compute end time from start time + duration
    start_dt = datetime.combine(date.today(), session_start)
    session_end = (start_dt + timedelta(minutes=duration_minutes)).time()

    created_bookings: list[Booking] = []

    try:
        for session_date in session_dates:
            # ── Find or create Slot ───────────────────────────────────────
            slot_result = await db.execute(
                select(Slot).where(
                    and_(
                        Slot.field_id == subscription.field_id,
                        Slot.slot_date == session_date,
                        Slot.start_time == session_start,
                    )
                )
            )
            slot: Slot | None = slot_result.scalar_one_or_none()

            if slot is None:
                slot = Slot(
                    field_id=subscription.field_id,
                    slot_date=session_date,
                    start_time=session_start,
                    end_time=session_end,
                    duration_minutes=duration_minutes,
                    status="available",
                )
                db.add(slot)
                await db.flush()  # get slot.id without committing

            # ── Skip already-booked slots ────────────────────────────────
            if slot.status == "booked":
                logger.debug(
                    "Skipping already-booked slot for subscription %s on %s",
                    subscription.id,
                    session_date,
                )
                continue

            # ── Create Booking ────────────────────────────────────────────
            booking = Booking(
                reference=generate_reference(session_date),
                player_id=subscription.player_id,
                field_id=subscription.field_id,
                slot_id=slot.id,
                subscription_id=subscription.id,
                slot_date=session_date,
                slot_start_time=session_start,
                slot_end_time=session_end,
                status="confirmed",
            )
            db.add(booking)

            # ── Mark slot as booked ───────────────────────────────────────
            slot.status = "booked"
            db.add(slot)

            await db.flush()
            created_bookings.append(booking)

            # ── Publish WebSocket update ──────────────────────────────────
            try:
                await _publish_slot_update(redis, slot)
            except Exception as ws_exc:
                logger.error(
                    "WebSocket publish failed for slot %s: %s", slot.id, ws_exc
                )

        await db.commit()

        # Refresh all bookings so callers get populated IDs / defaults
        for booking in created_bookings:
            await db.refresh(booking)

        logger.info(
            "Generated %d bookings for subscription %s",
            len(created_bookings),
            subscription.id,
        )

    except asyncpg.UniqueViolationError as exc:
        await db.rollback()
        logger.error(
            "Duplicate booking detected for subscription %s: %s",
            subscription.id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DUPLICATE_BOOKING",
                "message": "A booking for this slot already exists.",
            },
        ) from exc

    return created_bookings


# ---------------------------------------------------------------------------
# 4. Get single booking  (Requirements 7.1, 7.3)
# ---------------------------------------------------------------------------


async def get_booking(
    db: AsyncSession,
    booking_id: UUID,
    player_id: UUID,
) -> Booking:
    """
    Fetch a single Booking by ID.

    Raises 404 if not found, 403 if the booking does not belong to player_id.

    Requirements: 7.1, 7.3
    """
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking: Booking | None = result.scalar_one_or_none()

    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "BOOKING_NOT_FOUND",
                "message": "Booking not found.",
            },
        )

    if booking.player_id != player_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "BOOKING_ACCESS_DENIED",
                "message": "You do not have permission to view this booking.",
            },
        )

    return booking


# ---------------------------------------------------------------------------
# 5. List player bookings  (Requirement 7.4)
# ---------------------------------------------------------------------------


async def list_player_bookings(
    db: AsyncSession,
    player_id: UUID,
) -> list[Booking]:
    """
    Return all Bookings for a player, ordered by slot_date DESC.

    Requirements: 7.4
    """
    result = await db.execute(
        select(Booking)
        .where(Booking.player_id == player_id)
        .order_by(Booking.slot_date.desc())
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# 6. Cancel booking  (Requirements 6.4, 7.6, 11.3, 11.4)
# ---------------------------------------------------------------------------


async def cancel_booking(
    db: AsyncSession,
    booking_id: UUID,
    player_id: UUID,
    redis,
) -> Booking:
    """
    Cancel a confirmed booking.

    Enforces a 2-hour cancellation window: if the session starts in less than
    2 hours, raises 400 CANCELLATION_WINDOW_PASSED.

    Sets:
      - booking.status = 'cancelled'
      - booking.cancellation_reason = 'player_initiated'
      - booking.cancelled_at = now()
      - slot.status = 'available'

    Publishes a WebSocket update and sends an FCM cancellation notification.
    Returns the updated Booking.

    Requirements: 7.6, 11.3, 11.4
    """
    from app.services.slot_service import _publish_slot_update  # avoid circular

    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking: Booking | None = result.scalar_one_or_none()

    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "BOOKING_NOT_FOUND",
                "message": "Booking not found.",
            },
        )

    if booking.player_id != player_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "BOOKING_ACCESS_DENIED",
                "message": "You do not have permission to cancel this booking.",
            },
        )

    if booking.status != "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "BOOKING_NOT_CANCELLABLE",
                "message": f"Booking with status '{booking.status}' cannot be cancelled.",
            },
        )

    # ── 2-hour cancellation window check ─────────────────────────────────
    now_utc = datetime.now(tz=timezone.utc)
    slot_datetime = datetime.combine(booking.slot_date, booking.slot_start_time).replace(
        tzinfo=timezone.utc
    )
    time_until_slot = slot_datetime - now_utc

    if time_until_slot < timedelta(hours=2):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "CANCELLATION_WINDOW_PASSED",
                "message": (
                    "Cancellations must be made at least 2 hours before the session."
                ),
            },
        )

    # ── Update booking ────────────────────────────────────────────────────
    booking.status = "cancelled"
    booking.cancellation_reason = "player_initiated"
    booking.cancelled_at = now_utc
    db.add(booking)

    # ── Release slot ──────────────────────────────────────────────────────
    slot_result = await db.execute(select(Slot).where(Slot.id == booking.slot_id))
    slot: Slot | None = slot_result.scalar_one_or_none()

    if slot is not None:
        slot.status = "available"
        db.add(slot)

    await db.commit()
    await db.refresh(booking)

    # ── Publish WebSocket update ──────────────────────────────────────────
    if slot is not None:
        await db.refresh(slot)
        try:
            await _publish_slot_update(redis, slot)
        except Exception as ws_exc:
            logger.error(
                "WebSocket publish failed on cancel for slot %s: %s",
                booking.slot_id,
                ws_exc,
            )

    # ── FCM cancellation notification (local import to avoid circulars) ──
    try:
        from app.services import notification_service  # noqa: PLC0415

        player_result = await db.execute(select(User).where(User.id == player_id))
        player: User | None = player_result.scalar_one_or_none()

        if player and player.fcm_token:
            field_result = await db.execute(
                select(Field).where(Field.id == booking.field_id)
            )
            field: Field | None = field_result.scalar_one_or_none()
            field_name = field.name if field else str(booking.field_id)

            await notification_service.send_booking_cancelled(
                token=player.fcm_token,
                booking=booking,
                field_name=field_name,
                reason="player_initiated",
            )
    except Exception as exc:
        logger.error(
            "FCM cancel notification failed for booking %s: %s", booking_id, exc
        )

    return booking


# ---------------------------------------------------------------------------
# 7. Check-in  (Requirements 11.2, 11.3)
# ---------------------------------------------------------------------------


async def check_in(
    db: AsyncSession,
    booking_id: UUID,
    field_owner_id: UUID,
) -> tuple[Booking, str | None]:
    """
    Mark a booking as checked-in.

    Authorization:
      - The requesting user must be the Field Owner of the booking's field, or
        have the SUPER_ADMIN role.

    Timing warning:
      - If the check-in is more than 30 minutes before or after the scheduled
        slot start time, a warning string is returned alongside the booking.

    Sets:
      - booking.status = 'checked_in'
      - booking.checked_in_at = now()

    Returns (booking, warning_message | None).

    Requirements: 11.2, 11.3
    """
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking: Booking | None = result.scalar_one_or_none()

    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "BOOKING_NOT_FOUND",
                "message": "Booking not found.",
            },
        )

    # ── Verify field ownership or SUPER_ADMIN ─────────────────────────────
    user_result = await db.execute(select(User).where(User.id == field_owner_id))
    user: User | None = user_result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requesting user not found.",
        )

    is_super_admin = user.role == "SUPER_ADMIN"

    if not is_super_admin:
        field_result = await db.execute(
            select(Field).where(Field.id == booking.field_id)
        )
        field: Field | None = field_result.scalar_one_or_none()

        if field is None or field.owner_id != field_owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "CHECK_IN_ACCESS_DENIED",
                    "message": "You do not have permission to check in this booking.",
                },
            )

    if booking.status != "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "BOOKING_NOT_CONFIRMABLE",
                "message": (
                    f"Cannot check in a booking with status '{booking.status}'."
                ),
            },
        )

    # ── 30-minute mismatch warning ────────────────────────────────────────
    now_utc = datetime.now(tz=timezone.utc)
    slot_datetime = datetime.combine(booking.slot_date, booking.slot_start_time).replace(
        tzinfo=timezone.utc
    )
    mismatch = abs((now_utc - slot_datetime).total_seconds())
    warning: str | None = None

    if mismatch > 1800:  # 30 minutes in seconds
        direction = "early" if now_utc < slot_datetime else "late"
        minutes_off = int(mismatch // 60)
        warning = (
            f"Check-in is {minutes_off} minutes {direction} "
            f"relative to the scheduled slot time."
        )

    # ── Update booking ────────────────────────────────────────────────────
    booking.status = "checked_in"
    booking.checked_in_at = now_utc
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    logger.info(
        "Check-in recorded: booking=%s field_owner=%s warning=%s",
        booking_id,
        field_owner_id,
        warning,
    )

    return booking, warning


# ---------------------------------------------------------------------------
# 8. Verify by reference  (Requirement 11.4)
# ---------------------------------------------------------------------------


async def verify_by_reference(
    db: AsyncSession,
    reference: str,
    field_owner_id: UUID,
) -> Booking:
    """
    Look up a Booking by its reference string and verify field ownership.

    Raises 404 if no booking with the given reference exists.
    Raises 403 if the field does not belong to field_owner_id (unless
    SUPER_ADMIN).

    Requirements: 11.4
    """
    result = await db.execute(
        select(Booking).where(Booking.reference == reference)
    )
    booking: Booking | None = result.scalar_one_or_none()

    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "BOOKING_NOT_FOUND",
                "message": f"No booking found with reference '{reference}'.",
            },
        )

    # ── Verify field ownership or SUPER_ADMIN ─────────────────────────────
    user_result = await db.execute(select(User).where(User.id == field_owner_id))
    user: User | None = user_result.scalar_one_or_none()

    is_super_admin = user is not None and user.role == "SUPER_ADMIN"

    if not is_super_admin:
        field_result = await db.execute(
            select(Field).where(Field.id == booking.field_id)
        )
        field: Field | None = field_result.scalar_one_or_none()

        if field is None or field.owner_id != field_owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "BOOKING_ACCESS_DENIED",
                    "message": "You do not have permission to access this booking.",
                },
            )

    return booking
