"""
Subscriptions router — subscription contract lifecycle.

Routes:
  POST   /subscriptions                                    — FIELD_OWNER; propose contract
  GET    /subscriptions/stats                              — SUPER_ADMIN; platform stats
  GET    /subscriptions/player/me                          — Player; own subscriptions
  GET    /subscriptions/{sub_id}                           — Player or FIELD_OWNER; contract detail
  POST   /subscriptions/{sub_id}/request-renewal           — Player; notify owner to renew
  POST   /subscriptions/{sub_id}/slot-change               — FIELD_OWNER; propose slot change
  PATCH  /subscriptions/{sub_id}/slot-change/{proposal_id} — Player; approve/reject slot change
  GET    /subscriptions/{sub_id}/history                   — Player; full history

Requirements: 17.1, 17.4, 17.13, 17.16
"""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.field import Field
from app.models.subscription import Subscription
from app.redis_client import get_redis
from app.schemas.subscription import (
    SlotChangeApproval,
    SlotChangeProposalCreate,
    SlotChangeProposalResponse,
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionStatsItem,
    SubscriptionStatsResponse,
)
from app.services import subscription_service
from app.services.auth_service import get_current_user, require_role
from app.models.user import User

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


# NOTE: /stats and /player/me MUST come before /{sub_id} to avoid routing conflicts.

@router.post(
    "",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Propose a subscription contract",
)
async def propose_subscription(
    body: SubscriptionCreate,
    current_user: User = Depends(require_role("FIELD_OWNER", "SUPER_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    sub = await subscription_service.propose_subscription(
        db=db,
        field_owner_id=current_user.id,
        player_id=body.player_id,
        field_id=body.field_id,
        recurring_days=body.recurring_days,
        session_start_time=body.session_start_time,
        session_duration_hours=body.session_duration_hours,
        tier=body.tier,
    )
    return SubscriptionResponse.model_validate(sub)


@router.get("/stats", response_model=SubscriptionStatsResponse, summary="Subscription stats (SUPER_ADMIN)")
async def subscription_stats(
    current_user: User = Depends(require_role("SUPER_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    # Count active subscriptions per tier
    tier_result = await db.execute(
        select(Subscription.tier, func.count(Subscription.id))
        .where(Subscription.status == "active")
        .group_by(Subscription.tier)
    )
    by_tier = {row[0]: row[1] for row in tier_result.all()}

    # Count active subscriptions per field
    field_result = await db.execute(
        select(Subscription.field_id, func.count(Subscription.id))
        .where(Subscription.status == "active")
        .group_by(Subscription.field_id)
    )
    field_rows = field_result.all()

    by_field = []
    for field_id, count in field_rows:
        field_q = await db.execute(select(Field).where(Field.id == field_id))
        field = field_q.scalar_one_or_none()
        by_field.append(
            SubscriptionStatsItem(
                field_id=field_id,
                field_name=field.name if field else str(field_id),
                active_count=count,
            )
        )

    return SubscriptionStatsResponse(by_tier=by_tier, by_field=by_field)


@router.get("/player/me", response_model=list[SubscriptionResponse], summary="My subscriptions")
async def my_subscriptions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subs = await subscription_service.list_player_subscriptions(db, current_user.id)
    return [SubscriptionResponse.model_validate(s) for s in subs]


@router.get("/{sub_id}", response_model=SubscriptionResponse, summary="Get subscription detail")
async def get_subscription(
    sub_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await subscription_service.get_subscription(db, sub_id, current_user.id)
    return SubscriptionResponse.model_validate(sub)


@router.post("/{sub_id}/request-renewal", summary="Request subscription renewal")
async def request_renewal(
    sub_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    await subscription_service.request_renewal(db, sub_id, current_user.id, redis)
    return {"message": "Renewal request sent to field owner"}


@router.post(
    "/{sub_id}/slot-change",
    response_model=SlotChangeProposalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Propose a slot change (FIELD_OWNER)",
)
async def propose_slot_change(
    sub_id: UUID,
    body: SlotChangeProposalCreate,
    current_user: User = Depends(require_role("FIELD_OWNER", "SUPER_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    proposal = await subscription_service.propose_slot_change(
        db=db,
        sub_id=sub_id,
        field_owner_id=current_user.id,
        new_days=body.new_recurring_days,
        new_start_time=body.new_session_start_time,
        new_duration=body.new_session_duration_hours,
    )
    return SlotChangeProposalResponse.model_validate(proposal)


@router.patch(
    "/{sub_id}/slot-change/{proposal_id}",
    response_model=SlotChangeProposalResponse,
    summary="Approve or reject slot change (Player)",
)
async def respond_slot_change(
    sub_id: UUID,
    proposal_id: UUID,
    body: SlotChangeApproval,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    proposal = await subscription_service.respond_to_slot_change(
        db=db,
        proposal_id=proposal_id,
        player_id=current_user.id,
        approved=body.approved,
        redis=redis,
    )
    return SlotChangeProposalResponse.model_validate(proposal)


@router.get("/{sub_id}/history", response_model=list[SubscriptionResponse], summary="Subscription history")
async def subscription_history(
    sub_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    history = await subscription_service.get_history(db, current_user.id)
    return [SubscriptionResponse.model_validate(s) for s in history]
