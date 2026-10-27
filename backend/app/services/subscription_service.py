"""
subscription_service.py — Business logic for subscription contract lifecycle:
price calculation, proposal, activation, history, renewal, and slot-change workflow.

All DB access uses SQLAlchemy 2.0 async sessions.
Circular imports (booking_service, notification_service) are resolved via
local imports inside function bodies.

Requirements: 17.1–17.18
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.field import Field
from app.models.slot_change_proposal import SlotChangeProposal
from app.models.subscription import Subscription
from app.models.user import User

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TIER_MONTHS: dict[str, int] = {
    "1_month": 1,
    "2_months": 2,
    "3_months": 3,
}

# ---------------------------------------------------------------------------
# Pure calculation helpers  (Requirements 17.2)
# ---------------------------------------------------------------------------


def calculate_total_sessions(tier: str, days_per_week: int) -> int:
    """
    Compute the total number of sessions in a subscription period.

    total_sessions = round(days_per_week × 4.33 × months)
    """
    months = TIER_MONTHS[tier]
    return round(days_per_week * 4.33 * months)


def calculate_price(
    hourly_rate: Decimal,
    session_hours: Decimal,
    total_sessions: int,
) -> Decimal:
    """
    Calculate the total subscription price, rounded to 2 decimal places.

    total_price = hourly_rate × session_hours × total_sessions
    """
    return (hourly_rate * session_hours * total_sessions).quantize(Decimal("0.01"))


# ---------------------------------------------------------------------------
# 1. Propose subscription  (Requirements 17.1, 17.2, 17.3)
# ---------------------------------------------------------------------------


async def propose_subscription(
    db: AsyncSession,
    field_owner_id: UUID,
    player_id: UUID,
    field_id: UUID,
    recurring_days: list[str],
    session_start_time,
    session_duration_hours: Decimal,
    tier: str,
) -> Subscription:
    """
    Create a new Subscription proposal with status 'pending_payment'.

    - Verifies field exists and belongs to field_owner_id (403 if not).
    - Verifies player exists (404 if not).
    - Computes total_sessions and total_price.
    - Persists the Subscription record.
    - Sends FCM notification to the player.

    Requirements: 17.1, 17.2, 17.3
    """
    # ── Verify field exists and belongs to this owner ─────────────────────
    field_result = await db.execute(select(Field).where(Field.id == field_id))
    field: Field | None = field_result.scalar_one_or_none()

    if field is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Field not found.",
        )

    if field.owner_id != field_owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to propose a subscription for this field.",
        )

    # ── Verify player exists ──────────────────────────────────────────────
    player_result = await db.execute(select(User).where(User.id == player_id))
    player: User | None = player_result.scalar_one_or_none()

    if player is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found.",
        )

    # ── Compute sessions and price ────────────────────────────────────────
    days_per_week = len(recurring_days)
    total_sessions = calculate_total_sessions(tier, days_per_week)
    total_price = calculate_price(field.price_per_hour, session_duration_hours, total_sessions)

    # ── Persist subscription ──────────────────────────────────────────────
    subscription = Subscription(
        player_id=player_id,
        field_id=field_id,
        proposed_by=field_owner_id,
        recurring_days=recurring_days,
        session_start_time=session_start_time,
        session_duration_hours=session_duration_hours,
        tier=tier,
        total_sessions=total_sessions,
        total_price=total_price,
        status="pending_payment",
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)

    logger.info(
        "Subscription proposed: id=%s player=%s field=%s tier=%s total_price=%s",
        subscription.id,
        player_id,
        field_id,
        tier,
        total_price,
    )

    # ── Send FCM notification (local import avoids circular dependency) ───
    try:
        from app.services import notification_service  # noqa: PLC0415

        await notification_service.send_subscription_proposed(subscription)
    except Exception as exc:
        logger.error("Failed to send subscription_proposed notification: %s", exc)

    return subscription


# ---------------------------------------------------------------------------
# 2. Get a single subscription  (Requirements 17.4, 17.13)
# ---------------------------------------------------------------------------


async def get_subscription(
    db: AsyncSession,
    sub_id: UUID,
    requesting_user_id: UUID,
) -> Subscription:
    """
    Fetch a Subscription by ID with authorization check.

    The requesting user must be the player or the proposing field owner.
    Raises 404 if not found, 403 if unauthorized.

    Requirements: 17.4
    """
    result = await db.execute(select(Subscription).where(Subscription.id == sub_id))
    subscription: Subscription | None = result.scalar_one_or_none()

    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found.",
        )

    if requesting_user_id not in (subscription.player_id, subscription.proposed_by):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this subscription.",
        )

    return subscription


# ---------------------------------------------------------------------------
# 3. List all subscriptions for a player  (Requirement 17.13)
# ---------------------------------------------------------------------------


async def list_player_subscriptions(
    db: AsyncSession,
    player_id: UUID,
) -> list[Subscription]:
    """
    Return all Subscription records for a player, ordered by created_at DESC.

    Requirements: 17.13
    """
    result = await db.execute(
        select(Subscription)
        .where(Subscription.player_id == player_id)
        .order_by(Subscription.created_at.desc())
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# 4. Activate subscription  (Requirements 17.6)
# ---------------------------------------------------------------------------


async def activate(
    db: AsyncSession,
    sub_id: UUID,
    redis,
) -> Subscription:
    """
    Activate a Subscription after successful payment.

    Sets status='active', start_date=today, expiry_date=today + tier months.
    Triggers auto-generation of all Booking records via booking_service.
    Sends a summary FCM notification to the player.

    Requirements: 17.6
    """
    result = await db.execute(select(Subscription).where(Subscription.id == sub_id))
    subscription: Subscription | None = result.scalar_one_or_none()

    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found.",
        )

    today = date.today()
    months = TIER_MONTHS[subscription.tier]
    expiry = today + timedelta(days=30 * months)

    subscription.status = "active"
    subscription.start_date = today
    subscription.expiry_date = expiry

    await db.commit()
    await db.refresh(subscription)

    logger.info(
        "Subscription activated: id=%s start=%s expiry=%s",
        sub_id,
        today,
        expiry,
    )

    # ── Generate bookings (local import avoids circular dependency) ───────
    bookings_count = 0
    try:
        from app.services import booking_service  # noqa: PLC0415

        bookings = await booking_service.generate_bookings_for_subscription(
            db, subscription, redis
        )
        bookings_count = len(bookings)
        logger.info(
            "Generated %d bookings for subscription %s", bookings_count, sub_id
        )
    except Exception as exc:
        logger.error(
            "Failed to generate bookings for subscription %s: %s", sub_id, exc
        )

    # ── Send summary FCM notification ─────────────────────────────────────
    try:
        from app.services import notification_service  # noqa: PLC0415

        player_result = await db.execute(
            select(User).where(User.id == subscription.player_id)
        )
        player: User | None = player_result.scalar_one_or_none()

        if player and player.fcm_token:
            await notification_service.send_push_notification(
                token=player.fcm_token,
                title="✅ Subscription Active",
                body=(
                    f"Your subscription is active. "
                    f"{bookings_count} sessions have been booked."
                ),
                data={
                    "type": "subscription_activated",
                    "subscription_id": str(subscription.id),
                    "total_sessions": str(bookings_count),
                },
                channel_id="medazone_subscriptions",
            )
    except Exception as exc:
        logger.error(
            "Failed to send activation notification for subscription %s: %s",
            sub_id,
            exc,
        )

    return subscription


# ---------------------------------------------------------------------------
# 5. Get subscription history  (Requirement 17.18)
# ---------------------------------------------------------------------------


async def get_history(
    db: AsyncSession,
    player_id: UUID,
) -> list[Subscription]:
    """
    Return the full subscription history for a player, ordered by created_at DESC.

    Kept separate from list_player_subscriptions per spec so the history
    endpoint carries its own semantics (all-time, immutable record).

    Requirements: 17.18
    """
    result = await db.execute(
        select(Subscription)
        .where(Subscription.player_id == player_id)
        .order_by(Subscription.created_at.desc())
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# 6. Request renewal  (Requirement 17.12, 17.13)
# ---------------------------------------------------------------------------


async def request_renewal(
    db: AsyncSession,
    sub_id: UUID,
    player_id: UUID,
    redis,
) -> None:
    """
    Player requests the field owner to initiate a new subscription contract.

    Verifies the subscription belongs to the player, then sends an FCM
    notification to the field owner (proposed_by user).

    Requirements: 17.12, 17.13
    """
    result = await db.execute(select(Subscription).where(Subscription.id == sub_id))
    subscription: Subscription | None = result.scalar_one_or_none()

    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found.",
        )

    if subscription.player_id != player_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to request renewal for this subscription.",
        )

    logger.info(
        "Renewal requested: subscription=%s player=%s field_owner=%s",
        sub_id,
        player_id,
        subscription.proposed_by,
    )

    # ── Notify field owner ────────────────────────────────────────────────
    try:
        from app.services import notification_service  # noqa: PLC0415

        owner_result = await db.execute(
            select(User).where(User.id == subscription.proposed_by)
        )
        owner: User | None = owner_result.scalar_one_or_none()

        if owner and owner.fcm_token:
            tier_label = subscription.tier.replace("_", " ")
            days_str = ", ".join(subscription.recurring_days)

            await notification_service.send_push_notification(
                token=owner.fcm_token,
                title="🔄 Subscription Renewal Request",
                body=(
                    f"A player is requesting a renewal for their "
                    f"{tier_label} subscription ({days_str}). "
                    f"Please initiate a new contract."
                ),
                data={
                    "type": "renewal_requested",
                    "subscription_id": str(subscription.id),
                    "player_id": str(player_id),
                },
                channel_id="medazone_subscriptions",
            )
        else:
            logger.warning(
                "request_renewal: field owner %s has no FCM token",
                subscription.proposed_by,
            )
    except Exception as exc:
        logger.error(
            "Failed to send renewal notification for subscription %s: %s",
            sub_id,
            exc,
        )


# ---------------------------------------------------------------------------
# 7. Propose slot change  (Requirement 17.14)
# ---------------------------------------------------------------------------


async def propose_slot_change(
    db: AsyncSession,
    sub_id: UUID,
    field_owner_id: UUID,
    new_days: list[str],
    new_start_time,
    new_duration: Decimal,
) -> SlotChangeProposal:
    """
    Field owner proposes a change to the recurring slot schedule.

    Creates a SlotChangeProposal with status='pending' and a 48-hour expiry.
    Raises 404 if subscription not found, 403 if field_owner_id is not the proposer.

    Requirements: 17.14
    """
    result = await db.execute(select(Subscription).where(Subscription.id == sub_id))
    subscription: Subscription | None = result.scalar_one_or_none()

    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found.",
        )

    if subscription.proposed_by != field_owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the proposing field owner may initiate a slot change.",
        )

    expires_at = datetime.now(tz=timezone.utc) + timedelta(hours=48)

    proposal = SlotChangeProposal(
        subscription_id=sub_id,
        proposed_by=field_owner_id,
        new_recurring_days=new_days,
        new_session_start_time=new_start_time,
        new_session_duration_hours=new_duration,
        status="pending",
        expires_at=expires_at,
    )
    db.add(proposal)
    await db.commit()
    await db.refresh(proposal)

    logger.info(
        "SlotChangeProposal created: id=%s subscription=%s expires_at=%s",
        proposal.id,
        sub_id,
        expires_at,
    )
    return proposal


# ---------------------------------------------------------------------------
# 8. Respond to slot change  (Requirement 17.14, 17.15)
# ---------------------------------------------------------------------------


async def respond_to_slot_change(
    db: AsyncSession,
    proposal_id: UUID,
    player_id: UUID,
    approved: bool,
    redis,
) -> SlotChangeProposal:
    """
    Player approves or rejects a slot-change proposal.

    If approved:
      - Updates subscription.recurring_days / session_start_time / session_duration_hours.
      - Cancels future confirmed bookings beyond today.
      - Regenerates future sessions via booking_service.
      - Sets proposal.status='approved'.

    If rejected:
      - Sets proposal.status='rejected'.

    Requirements: 17.14, 17.15
    """
    proposal_result = await db.execute(
        select(SlotChangeProposal).where(SlotChangeProposal.id == proposal_id)
    )
    proposal: SlotChangeProposal | None = proposal_result.scalar_one_or_none()

    if proposal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slot change proposal not found.",
        )

    # Fetch associated subscription to verify player ownership
    sub_result = await db.execute(
        select(Subscription).where(Subscription.id == proposal.subscription_id)
    )
    subscription: Subscription | None = sub_result.scalar_one_or_none()

    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated subscription not found.",
        )

    if subscription.player_id != player_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to respond to this slot change proposal.",
        )

    if approved:
        # ── Update subscription schedule ───────────────────────────────────
        subscription.recurring_days = proposal.new_recurring_days
        subscription.session_start_time = proposal.new_session_start_time
        subscription.session_duration_hours = proposal.new_session_duration_hours

        # ── Cancel future bookings beyond today ───────────────────────────
        try:
            from app.models.booking import Booking  # noqa: PLC0415
            from sqlalchemy import and_, update  # noqa: PLC0415

            today = date.today()
            await db.execute(
                update(Booking)
                .where(
                    and_(
                        Booking.subscription_id == subscription.id,
                        Booking.slot_date > today,
                        Booking.status == "confirmed",
                    )
                )
                .values(
                    status="cancelled",
                    cancellation_reason="field_owner_initiated",
                )
            )
        except Exception as exc:
            logger.error(
                "Failed to cancel future bookings for slot change proposal %s: %s",
                proposal_id,
                exc,
            )

        # ── Regenerate future sessions ────────────────────────────────────
        try:
            from app.services import booking_service  # noqa: PLC0415

            await booking_service.generate_bookings_for_subscription(
                db, subscription, redis
            )
        except Exception as exc:
            logger.error(
                "Failed to regenerate bookings after slot change approval %s: %s",
                proposal_id,
                exc,
            )

        proposal.status = "approved"
        logger.info(
            "SlotChangeProposal approved: id=%s subscription=%s",
            proposal_id,
            subscription.id,
        )
    else:
        proposal.status = "rejected"
        logger.info(
            "SlotChangeProposal rejected: id=%s subscription=%s",
            proposal_id,
            subscription.id,
        )

    await db.commit()
    await db.refresh(proposal)
    return proposal
