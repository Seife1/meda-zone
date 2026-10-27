"""
APScheduler jobs for MedaZone periodic maintenance.

Jobs:
  1. expire_soft_reservations  — every 2 min  — release unpaid slot reservations
  2. send_booking_reminders    — every 1 min  — FCM reminder 60 min before session
  3. expire_sponsorships       — every 60 min — remove expired field sponsorships
  4. process_subscription_expiry — every 60 min — expire subscriptions + send FCM
  5. expire_slot_change_proposals — every 30 min — expire unresponded proposals

Requirements: 16.1, 16.2, 16.3, 16.4, 17.9, 17.10, 17.11, 17.15
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


# ---------------------------------------------------------------------------
# Job 1: Expire soft reservations (every 2 min)
# ---------------------------------------------------------------------------

async def _expire_soft_reservations() -> None:
    """
    Find slots with status='pending' and soft_reserved_until < now().
    Set status='available', clear soft_reserved_by/until.
    Publish WebSocket update per affected field.
    """
    try:
        from sqlalchemy import and_, select, update
        from app.database import AsyncSessionLocal
        from app.models.slot import Slot
        from app.redis_client import get_redis
        from app.services.slot_service import _publish_slot_update

        now = datetime.now(tz=timezone.utc)
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Slot).where(
                    and_(
                        Slot.status == "pending",
                        Slot.soft_reserved_until < now,
                    )
                )
            )
            expired_slots = result.scalars().all()

            if not expired_slots:
                return

            redis = await get_redis()

            for slot in expired_slots:
                slot.status = "available"
                slot.soft_reserved_by = None
                slot.soft_reserved_until = None

            await db.commit()

            for slot in expired_slots:
                await db.refresh(slot)
                try:
                    await _publish_slot_update(redis, slot)
                except Exception as exc:
                    logger.error("Redis publish failed for slot %s: %s", slot.id, exc)

            logger.info("expire_soft_reservations: released %d slots", len(expired_slots))

    except Exception as exc:
        logger.error(
            "APScheduler job failed: job=expire_soft_reservations timestamp=%s exception=%s",
            datetime.utcnow().isoformat(),
            exc,
        )


# ---------------------------------------------------------------------------
# Job 2: Send booking reminders (every 1 min)
# ---------------------------------------------------------------------------

async def _send_booking_reminders() -> None:
    """
    Find confirmed bookings whose slot starts in 55–65 minutes.
    Send FCM reminder if player has booking_reminder preference enabled.
    """
    try:
        from sqlalchemy import and_, select
        from app.database import AsyncSessionLocal
        from app.models.booking import Booking
        from app.models.notification_preference import NotificationPreference
        from app.models.user import User
        from app.models.field import Field
        from app.services.notification_service import send_booking_reminder

        now = datetime.now(tz=timezone.utc)
        window_start = now + timedelta(minutes=55)
        window_end = now + timedelta(minutes=65)

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Booking).where(Booking.status == "confirmed")
            )
            confirmed = result.scalars().all()

            dispatched = 0
            for booking in confirmed:
                slot_dt = datetime.combine(booking.slot_date, booking.slot_start_time).replace(
                    tzinfo=timezone.utc
                )
                if not (window_start <= slot_dt <= window_end):
                    continue

                # Check player preference
                pref_result = await db.execute(
                    select(NotificationPreference).where(
                        NotificationPreference.player_id == booking.player_id
                    )
                )
                pref = pref_result.scalar_one_or_none()
                if pref and not pref.booking_reminder:
                    continue

                player_result = await db.execute(
                    select(User).where(User.id == booking.player_id)
                )
                player = player_result.scalar_one_or_none()
                if not player or not player.fcm_token:
                    continue

                field_result = await db.execute(
                    select(Field).where(Field.id == booking.field_id)
                )
                field = field_result.scalar_one_or_none()
                field_name = field.name if field else str(booking.field_id)

                await send_booking_reminder(booking, player.fcm_token, field_name)
                dispatched += 1

            if dispatched:
                logger.info("send_booking_reminders: dispatched %d reminders", dispatched)

    except Exception as exc:
        logger.error(
            "APScheduler job failed: job=send_booking_reminders timestamp=%s exception=%s",
            datetime.utcnow().isoformat(),
            exc,
        )


# ---------------------------------------------------------------------------
# Job 3: Expire sponsorships (every 60 min)
# ---------------------------------------------------------------------------

async def _expire_sponsorships() -> None:
    """Find fields with is_sponsored=True and sponsorship_end < today. Clear sponsorship."""
    try:
        from sqlalchemy import and_, select
        from app.database import AsyncSessionLocal
        from app.models.field import Field

        today = date.today()
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Field).where(
                    and_(
                        Field.is_sponsored == True,  # noqa: E712
                        Field.sponsorship_end < today,
                    )
                )
            )
            expired = result.scalars().all()
            for field in expired:
                field.is_sponsored = False
                field.sponsorship_start = None
                field.sponsorship_end = None

            if expired:
                await db.commit()
                logger.info("expire_sponsorships: cleared %d fields", len(expired))

    except Exception as exc:
        logger.error(
            "APScheduler job failed: job=expire_sponsorships timestamp=%s exception=%s",
            datetime.utcnow().isoformat(),
            exc,
        )


# ---------------------------------------------------------------------------
# Job 4: Process subscription expiry (every 60 min)
# ---------------------------------------------------------------------------

async def _process_subscription_expiry() -> None:
    """
    - Subscriptions with expiry_date = today+3: send "expiring soon" FCM.
    - Subscriptions with expiry_date = today and status='active': expire + send FCM.
    """
    try:
        from sqlalchemy import and_, select
        from app.database import AsyncSessionLocal
        from app.models.subscription import Subscription
        from app.models.user import User
        from app.models.field import Field
        from app.services.notification_service import (
            send_subscription_expiring_soon,
            send_subscription_expired,
        )

        today = date.today()
        expiry_warning_date = today + timedelta(days=3)

        async with AsyncSessionLocal() as db:
            # Expiring soon
            warn_result = await db.execute(
                select(Subscription).where(
                    and_(
                        Subscription.expiry_date == expiry_warning_date,
                        Subscription.status == "active",
                    )
                )
            )
            for sub in warn_result.scalars().all():
                player_q = await db.execute(select(User).where(User.id == sub.player_id))
                player = player_q.scalar_one_or_none()
                field_q = await db.execute(select(Field).where(Field.id == sub.field_id))
                field = field_q.scalar_one_or_none()
                if player and player.fcm_token and field:
                    await send_subscription_expiring_soon(sub, player.fcm_token, field.name)

            # Expired today
            expired_result = await db.execute(
                select(Subscription).where(
                    and_(
                        Subscription.expiry_date == today,
                        Subscription.status == "active",
                    )
                )
            )
            expired_subs = expired_result.scalars().all()
            for sub in expired_subs:
                sub.status = "expired"
                player_q = await db.execute(select(User).where(User.id == sub.player_id))
                player = player_q.scalar_one_or_none()
                field_q = await db.execute(select(Field).where(Field.id == sub.field_id))
                field = field_q.scalar_one_or_none()
                if player and player.fcm_token and field:
                    await send_subscription_expired(sub, player.fcm_token, field.name)

            if expired_subs:
                await db.commit()
                logger.info("process_subscription_expiry: expired %d subscriptions", len(expired_subs))

    except Exception as exc:
        logger.error(
            "APScheduler job failed: job=process_subscription_expiry timestamp=%s exception=%s",
            datetime.utcnow().isoformat(),
            exc,
        )


# ---------------------------------------------------------------------------
# Job 5: Expire slot change proposals (every 30 min)
# ---------------------------------------------------------------------------

async def _expire_slot_change_proposals() -> None:
    """Find pending SlotChangeProposals past their expires_at. Set status='expired'."""
    try:
        from sqlalchemy import and_, select
        from app.database import AsyncSessionLocal
        from app.models.slot_change_proposal import SlotChangeProposal

        now = datetime.now(tz=timezone.utc)
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(SlotChangeProposal).where(
                    and_(
                        SlotChangeProposal.status == "pending",
                        SlotChangeProposal.expires_at < now,
                    )
                )
            )
            expired = result.scalars().all()
            for proposal in expired:
                proposal.status = "expired"

            if expired:
                await db.commit()
                logger.info("expire_slot_change_proposals: expired %d proposals", len(expired))

    except Exception as exc:
        logger.error(
            "APScheduler job failed: job=expire_slot_change_proposals timestamp=%s exception=%s",
            datetime.utcnow().isoformat(),
            exc,
        )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_medazone_jobs() -> None:
    scheduler.add_job(
        _expire_soft_reservations,
        trigger=IntervalTrigger(minutes=2),
        id="expire_soft_reservations",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=30,
    )
    scheduler.add_job(
        _send_booking_reminders,
        trigger=IntervalTrigger(minutes=1),
        id="send_booking_reminders",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=30,
    )
    scheduler.add_job(
        _expire_sponsorships,
        trigger=IntervalTrigger(minutes=60),
        id="expire_sponsorships",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=120,
    )
    scheduler.add_job(
        _process_subscription_expiry,
        trigger=IntervalTrigger(minutes=60),
        id="process_subscription_expiry",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=120,
    )
    scheduler.add_job(
        _expire_slot_change_proposals,
        trigger=IntervalTrigger(minutes=30),
        id="expire_slot_change_proposals",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=60,
    )
    logger.info("Registered 5 MedaZone APScheduler jobs")
