"""
slot_service.py — Business logic for slot generation, status transitions,
soft reservations, and real-time WebSocket publishing.

Requirements: 5.5, 5.6, 10.1, 10.2, 10.3, 10.4
"""

import logging
from datetime import date, datetime, timedelta
from datetime import time as dt_time
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.slot import Slot

logger = logging.getLogger(__name__)


# ── Helper ────────────────────────────────────────────────────────────────────

async def _publish_slot_update(redis, slot: Slot) -> None:
    """Publish a SlotUpdateMessage to the field's Redis pub/sub channel."""
    from app.schemas.slot import SlotUpdateMessage

    msg = SlotUpdateMessage(
        slot_id=str(slot.id),
        status=slot.status,
        slot_date=slot.slot_date.isoformat(),
        start_time=slot.start_time.strftime("%H:%M"),
        end_time=slot.end_time.strftime("%H:%M"),
    )
    await redis.publish(f"field:{slot.field_id}:slots", msg.model_dump_json())


# ── Slot generation ───────────────────────────────────────────────────────────

async def generate_slots(
    db: AsyncSession,
    field_id,
    start_date: date,
    end_date: date,
    slot_duration_minutes: int,
    open_time_str: str,
    close_time_str: str,
) -> dict:
    """
    Generate recurring slots for a field across a date range.

    Iterates each date from start_date to end_date (inclusive). For each date,
    creates time windows from open_time to close_time with steps of
    slot_duration_minutes. Skips windows where a slot already exists.

    Returns {"created_count": N, "skipped_count": M}.

    Requirements: 10.1, 10.2
    """
    open_time: dt_time = datetime.strptime(open_time_str, "%H:%M").time()
    close_time: dt_time = datetime.strptime(close_time_str, "%H:%M").time()

    created_count = 0
    skipped_count = 0
    slots_to_insert: List[Slot] = []

    current_date = start_date
    while current_date <= end_date:
        # Build a full datetime for arithmetic convenience
        window_start = datetime.combine(current_date, open_time)
        day_close = datetime.combine(current_date, close_time)

        while True:
            window_end = window_start + timedelta(minutes=slot_duration_minutes)
            # Stop when the window would exceed close_time
            if window_end.time() > close_time or window_end > day_close:
                break

            # Check if slot already exists (field_id + slot_date + start_time)
            existing_result = await db.execute(
                select(Slot).where(
                    and_(
                        Slot.field_id == field_id,
                        Slot.slot_date == current_date,
                        Slot.start_time == window_start.time(),
                    )
                )
            )
            existing = existing_result.scalars().first()

            if existing is not None:
                skipped_count += 1
            else:
                slots_to_insert.append(
                    Slot(
                        field_id=field_id,
                        slot_date=current_date,
                        start_time=window_start.time(),
                        end_time=window_end.time(),
                        duration_minutes=slot_duration_minutes,
                        status="available",
                    )
                )
                created_count += 1

            window_start = window_end

        current_date += timedelta(days=1)

    # Bulk insert all new slots in one flush
    if slots_to_insert:
        db.add_all(slots_to_insert)
        await db.commit()

    logger.info(
        "generate_slots field=%s created=%d skipped=%d",
        field_id,
        created_count,
        skipped_count,
    )
    return {"created_count": created_count, "skipped_count": skipped_count}


# ── Slot query ────────────────────────────────────────────────────────────────

async def get_slots_for_field(db: AsyncSession, field_id) -> List[Slot]:
    """
    Return slots for a field within the next 7 days (today to today+6 inclusive),
    ordered by slot_date ASC, start_time ASC.

    Requirements: 4.2 (7-day calendar window)
    """
    today = date.today()
    week_end = today + timedelta(days=6)

    result = await db.execute(
        select(Slot)
        .where(
            and_(
                Slot.field_id == field_id,
                Slot.slot_date >= today,
                Slot.slot_date <= week_end,
            )
        )
        .order_by(Slot.slot_date.asc(), Slot.start_time.asc())
    )
    return list(result.scalars().all())


# ── Status transition ─────────────────────────────────────────────────────────

async def change_slot_status(
    db: AsyncSession,
    slot_id,
    new_status: str,
    redis,
) -> Slot:
    """
    Change a slot's status.

    Validation:
    - Cannot close a slot that is 'booked' without first cancelling the booking.
    - Can only close 'available' or 'pending' slots directly.
    - If closing a slot that has a 'booked' booking: cancel the booking, send
      FCM cancellation notification, log a rescheduling note.

    Requirements: 10.3, 10.4
    """
    result = await db.execute(select(Slot).where(Slot.id == slot_id))
    slot = result.scalars().first()
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slot not found",
        )

    current_status = slot.status

    # Validate transition: cannot move a 'booked' slot to 'closed' directly
    # without cancelling its booking first (handled below). Cannot re-open a
    # 'closed' slot via this endpoint (that would require 'available').
    if current_status == "booked" and new_status == "closed":
        # Find the active booking for this slot
        booking_result = await db.execute(
            select(Booking).where(
                and_(
                    Booking.slot_id == slot_id,
                    Booking.status.in_(["confirmed", "checked_in"]),
                )
            )
        )
        booking = booking_result.scalars().first()

        if booking is not None:
            # Cancel the booking
            booking.status = "cancelled"
            booking.cancellation_reason = "field_owner_initiated"
            booking.cancelled_at = datetime.utcnow()
            db.add(booking)

            # Send FCM cancellation notification (fire-and-forget; do not
            # roll back the slot update if FCM fails)
            try:
                from app.services.notification_service import send_push_notification
                from app.models.user import User

                player_result = await db.execute(
                    select(User).where(User.id == booking.player_id)
                )
                player = player_result.scalars().first()
                if player and player.fcm_token:
                    await send_push_notification(
                        token=player.fcm_token,
                        title="Booking Cancelled",
                        body=(
                            f"Your booking on "
                            f"{booking.slot_date.strftime('%d %b %Y')} at "
                            f"{booking.slot_start_time.strftime('%H:%M')} has been "
                            f"cancelled by the field owner."
                        ),
                        data={
                            "type": "booking_cancelled",
                            "booking_id": str(booking.id),
                            "reason": "field_owner_initiated",
                        },
                    )
            except Exception as exc:
                logger.error(
                    "FCM cancellation notification failed for booking %s: %s",
                    booking.id,
                    exc,
                )

            # Flag the subscription session for rescheduling (log for now)
            if booking.subscription_id:
                logger.info(
                    "Subscription session rescheduling required: "
                    "subscription_id=%s booking_id=%s slot_id=%s",
                    booking.subscription_id,
                    booking.id,
                    slot_id,
                )

    elif current_status == "booked" and new_status != "closed":
        # Cannot transition a booked slot to anything other than 'closed'
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_STATUS_TRANSITION",
                "message": (
                    f"Cannot change slot status from '{current_status}' "
                    f"to '{new_status}'."
                ),
            },
        )

    # Apply the status update
    slot.status = new_status
    db.add(slot)
    await db.commit()
    await db.refresh(slot)

    # Publish WebSocket update
    try:
        await _publish_slot_update(redis, slot)
    except Exception as exc:
        logger.error("Redis publish failed for slot %s: %s", slot_id, exc)

    return slot


# ── Soft reservation ──────────────────────────────────────────────────────────

async def create_soft_reservation(
    db: AsyncSession,
    slot_id,
    player_id,
    redis,
) -> Slot:
    """
    Create a 5-minute soft reservation for a slot.

    - Raises 409 SLOT_UNAVAILABLE if slot is not 'available'.
    - Sets Redis key soft_res:{slot_id} with 5-min TTL.
    - Updates slot status to 'pending', records soft_reserved_by and
      soft_reserved_until.
    - Publishes SlotUpdateMessage.

    Requirements: 5.5
    """
    result = await db.execute(select(Slot).where(Slot.id == slot_id))
    slot = result.scalars().first()
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slot not found",
        )

    if slot.status != "available":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "SLOT_UNAVAILABLE",
                "message": f"Slot is not available (current status: '{slot.status}').",
            },
        )

    # SET soft_res:{slot_id} {player_id} EX 300
    from app.redis_client import soft_reservation_key

    await redis.set(soft_reservation_key(str(slot_id)), str(player_id), ex=300)

    # Update slot in DB
    now = datetime.utcnow()
    slot.status = "pending"
    slot.soft_reserved_by = player_id
    slot.soft_reserved_until = now + timedelta(minutes=5)
    db.add(slot)
    await db.commit()
    await db.refresh(slot)

    # Publish WebSocket update
    try:
        await _publish_slot_update(redis, slot)
    except Exception as exc:
        logger.error("Redis publish failed for slot %s: %s", slot_id, exc)

    return slot


async def release_soft_reservation(
    db: AsyncSession,
    slot_id,
    player_id,
    redis,
) -> Slot:
    """
    Release a soft reservation, returning the slot to 'available'.

    - Raises 403 if the reservation is held by a different player.
    - Deletes the Redis key soft_res:{slot_id}.
    - Resets slot status to 'available', clears reservation metadata.
    - Publishes SlotUpdateMessage.

    Requirements: 5.6
    """
    result = await db.execute(select(Slot).where(Slot.id == slot_id))
    slot = result.scalars().first()
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slot not found",
        )

    # Verify the reservation belongs to this player
    if slot.soft_reserved_by is None or str(slot.soft_reserved_by) != str(player_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "RESERVATION_NOT_OWNED",
                "message": "You do not hold the soft reservation for this slot.",
            },
        )

    # Delete the Redis key
    from app.redis_client import soft_reservation_key

    await redis.delete(soft_reservation_key(str(slot_id)))

    # Reset slot state
    slot.status = "available"
    slot.soft_reserved_by = None
    slot.soft_reserved_until = None
    db.add(slot)
    await db.commit()
    await db.refresh(slot)

    # Publish WebSocket update
    try:
        await _publish_slot_update(redis, slot)
    except Exception as exc:
        logger.error("Redis publish failed for slot %s: %s", slot_id, exc)

    return slot
