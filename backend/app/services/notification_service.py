"""
notification_service.py — MedaZone FCM push notification service.

Covers:
  - Core FCM v1 helper via Firebase Admin SDK (lazy init, retry once, never raises)
  - Booking notifications: confirmed, reminder, cancelled
  - Slot availability alerts (broadcast to multiple tokens)
  - Subscription notifications: proposed, expiring soon, expired

Design notes:
  - No function in this module raises — FCM failures are logged and False is returned.
  - Transactions must NOT be rolled back due to FCM errors.
  - Each dispatch logs success at INFO level with the last 6 chars of the token.
  - On failure the send is retried once; if the retry also fails, the error is logged.

Channel IDs (Android notification channels):
  - medazone_bookings       — booking-related notifications
  - medazone_subscriptions  — subscription-related notifications
  - medazone_alerts         — general alerts (slot availability, etc.)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Channel ID constants ──────────────────────────────────────────────────────
CHANNEL_BOOKINGS = "medazone_bookings"
CHANNEL_SUBSCRIPTIONS = "medazone_subscriptions"
CHANNEL_ALERTS = "medazone_alerts"


# ── Core FCM helper ───────────────────────────────────────────────────────────

async def send_push_notification(
    token: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
    channel_id: str = "medazone_default",
) -> bool:
    """Send an FCM v1 message via Firebase Admin SDK.

    Returns True on success, logs and returns False on failure.
    Does NOT raise — never roll back transactions due to FCM errors.
    Retries once on failure before giving up.
    """
    import firebase_admin
    from firebase_admin import messaging
    from app.services.auth_service import _init_firebase

    # Lazy-init Firebase Admin SDK (safe to call multiple times)
    if not firebase_admin._apps:
        _init_firebase()

    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
        android=messaging.AndroidConfig(
            notification=messaging.AndroidNotification(channel_id=channel_id)
        ),
        token=token,
    )

    notification_type = (data or {}).get("type", "unknown")

    def _do_send() -> str:
        return messaging.send(message)

    loop = asyncio.get_running_loop()

    # First attempt
    try:
        await loop.run_in_executor(None, _do_send)
        logger.info("FCM sent: type=%s token=...%s", notification_type, token[-6:])
        return True
    except Exception as exc:
        logger.warning("FCM send attempt 1 failed (type=%s token=...%s): %s",
                       notification_type, token[-6:], exc)

    # Retry once
    try:
        await loop.run_in_executor(None, _do_send)
        logger.info("FCM sent (retry): type=%s token=...%s", notification_type, token[-6:])
        return True
    except Exception as exc:
        logger.error("FCM send failed: %s", exc)
        return False


async def _broadcast(
    tokens: list[str],
    title: str,
    body: str,
    data: dict,
    channel_id: str = CHANNEL_ALERTS,
) -> None:
    """Fire-and-forget push to a list of FCM tokens (concurrent, max 20 at once)."""
    sem = asyncio.Semaphore(20)

    async def _send(token: str) -> None:
        async with sem:
            await send_push_notification(token, title, body, data, channel_id)

    await asyncio.gather(*[_send(t) for t in tokens], return_exceptions=True)


# ── Booking notifications ─────────────────────────────────────────────────────

async def send_booking_confirmed(
    booking,
    player_fcm_token: Optional[str],
    field_name: str,
) -> bool:
    """Notify a player their booking is confirmed.

    Sends FCM with field name, slot date, start time, and booking reference.
    Requirements: 8.1
    """
    if not player_fcm_token:
        logger.warning(
            "send_booking_confirmed: no FCM token for booking %s",
            getattr(booking, "id", "?"),
        )
        return False

    slot_date = getattr(booking, "slot_date", "")
    start_time = getattr(booking, "slot_start_time", "")
    reference = getattr(booking, "reference", "")

    return await send_push_notification(
        token=player_fcm_token,
        title="✅ Booking Confirmed",
        body=(
            f"{field_name} — {slot_date} at {start_time}. "
            f"Ref: {reference}"
        ),
        data={
            "type": "booking_confirmed",
            "booking_id": str(getattr(booking, "id", "")),
            "field_name": field_name,
            "slot_date": str(slot_date),
            "start_time": str(start_time),
            "reference": str(reference),
        },
        channel_id=CHANNEL_BOOKINGS,
    )


async def send_booking_reminder(
    booking,
    player_fcm_token: Optional[str],
    field_name: str,
) -> bool:
    """Send a 1-hour-before session reminder to a player.

    Requirements: 8.2
    """
    if not player_fcm_token:
        logger.warning(
            "send_booking_reminder: no FCM token for booking %s",
            getattr(booking, "id", "?"),
        )
        return False

    return await send_push_notification(
        token=player_fcm_token,
        title="⏰ Session Reminder",
        body=f"Your game starts in 1 hour at {field_name}",
        data={
            "type": "booking_reminder",
            "booking_id": str(getattr(booking, "id", "")),
            "field_name": field_name,
        },
        channel_id=CHANNEL_BOOKINGS,
    )


async def send_booking_cancelled(
    booking,
    player_fcm_token: Optional[str],
    field_name: str,
    reason: str = "field_owner_initiated",
) -> bool:
    """Notify a player their booking has been cancelled.

    Requirements: 8.3
    """
    if not player_fcm_token:
        logger.warning(
            "send_booking_cancelled: no FCM token for booking %s",
            getattr(booking, "id", "?"),
        )
        return False

    slot_date = getattr(booking, "slot_date", "")
    start_time = getattr(booking, "slot_start_time", "")
    reference = getattr(booking, "reference", "")

    return await send_push_notification(
        token=player_fcm_token,
        title="❌ Booking Cancelled",
        body=f"Your booking at {field_name} has been cancelled",
        data={
            "type": "booking_cancelled",
            "booking_id": str(getattr(booking, "id", "")),
            "reference": str(reference),
            "field_name": field_name,
            "slot_date": str(slot_date),
            "start_time": str(start_time),
            "reason": reason,
        },
        channel_id=CHANNEL_BOOKINGS,
    )


# ── Slot availability notifications ──────────────────────────────────────────

async def send_slot_available(
    field_id: str,
    field_name: str,
    player_fcm_tokens: list[str],
) -> None:
    """Notify all watching players that a slot opened at a field.

    Fire-and-forget — sends to all tokens concurrently.
    Requirements: 8.4
    """
    if not player_fcm_tokens:
        return

    await _broadcast(
        tokens=player_fcm_tokens,
        title="🟢 Slot Available",
        body=f"A slot just opened up at {field_name}. Book it before it's gone!",
        data={
            "type": "slot_available",
            "field_id": str(field_id),
            "field_name": field_name,
        },
        channel_id=CHANNEL_ALERTS,
    )


# ── Subscription notifications ────────────────────────────────────────────────

async def send_subscription_expiring_soon(
    subscription,
    player_fcm_token: Optional[str],
    field_name: str,
) -> bool:
    """Notify a player that their subscription expires in 3 days.

    Requirements: 8.5, 17.10
    """
    if not player_fcm_token:
        logger.warning(
            "send_subscription_expiring_soon: no FCM token for subscription %s",
            getattr(subscription, "id", "?"),
        )
        return False

    return await send_push_notification(
        token=player_fcm_token,
        title="⚠️ Subscription Expiring Soon",
        body=f"Your subscription at {field_name} expires in 3 days",
        data={
            "type": "subscription_expiring_soon",
            "subscription_id": str(getattr(subscription, "id", "")),
            "field_name": field_name,
            "expiry_date": str(getattr(subscription, "expiry_date", "")),
        },
        channel_id=CHANNEL_SUBSCRIPTIONS,
    )


async def send_subscription_expired(
    subscription,
    player_fcm_token: Optional[str],
    field_name: str,
) -> bool:
    """Notify a player that their subscription has expired.

    Requirements: 8.6, 17.11
    """
    if not player_fcm_token:
        logger.warning(
            "send_subscription_expired: no FCM token for subscription %s",
            getattr(subscription, "id", "?"),
        )
        return False

    return await send_push_notification(
        token=player_fcm_token,
        title="🔴 Subscription Expired",
        body=f"Your subscription at {field_name} has expired",
        data={
            "type": "subscription_expired",
            "subscription_id": str(getattr(subscription, "id", "")),
            "field_name": field_name,
            "expiry_date": str(getattr(subscription, "expiry_date", "")),
        },
        channel_id=CHANNEL_SUBSCRIPTIONS,
    )


async def send_subscription_proposed(
    subscription,
    player_fcm_token: Optional[str] = None,
    field_name: Optional[str] = None,
) -> bool:
    """Notify a player that a field owner has proposed a subscription contract.

    If player_fcm_token is None, fetches it from the DB.
    If field_name is None, fetches it from the DB.
    Requirements: 17.3
    """
    # Resolve FCM token and field name from DB if not provided
    if player_fcm_token is None or field_name is None:
        try:
            from sqlalchemy import select
            from app.database import AsyncSessionLocal
            from app.models.user import User
            from app.models.field import Field

            async with AsyncSessionLocal() as db:
                if player_fcm_token is None:
                    player_result = await db.execute(
                        select(User).where(User.id == subscription.player_id)
                    )
                    player = player_result.scalar_one_or_none()
                    if player:
                        player_fcm_token = player.fcm_token

                if field_name is None:
                    field_result = await db.execute(
                        select(Field).where(Field.id == subscription.field_id)
                    )
                    field = field_result.scalar_one_or_none()
                    if field:
                        field_name = field.name
        except Exception as exc:
            logger.error(
                "send_subscription_proposed: failed to fetch player/field from DB: %s", exc
            )

    if not player_fcm_token:
        logger.warning(
            "send_subscription_proposed: no FCM token for subscription %s player %s",
            getattr(subscription, "id", "?"),
            getattr(subscription, "player_id", "?"),
        )
        return False

    resolved_field_name = field_name or str(getattr(subscription, "field_id", ""))
    days_str = ", ".join(getattr(subscription, "recurring_days", []))
    total_sessions = getattr(subscription, "total_sessions", "")
    total_price = getattr(subscription, "total_price", "")

    return await send_push_notification(
        token=player_fcm_token,
        title="📋 New Subscription Proposal",
        body=(
            f"New subscription proposal from {resolved_field_name}: "
            f"{days_str}, {total_sessions} sessions, ETB {total_price}"
        ),
        data={
            "type": "subscription_proposed",
            "subscription_id": str(getattr(subscription, "id", "")),
            "field_name": resolved_field_name,
            "recurring_days": days_str,
            "total_sessions": str(total_sessions),
            "total_price": str(total_price),
        },
        channel_id=CHANNEL_SUBSCRIPTIONS,
    )
