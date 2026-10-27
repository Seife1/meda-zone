"""
Admin router — super admin user management and platform analytics.

Routes:
  GET    /admin/users                    — list users with role filter (SUPER_ADMIN)
  POST   /admin/users                    — create field owner account (SUPER_ADMIN)
  PATCH  /admin/users/{user_id}          — edit / deactivate user (SUPER_ADMIN)
  GET    /admin/analytics                — platform analytics (SUPER_ADMIN)
  GET    /admin/analytics/subscriptions  — subscription stats (SUPER_ADMIN)

Requirements: 12.1, 12.2, 12.3, 17.16, 17.17
"""
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.booking import Booking
from app.models.field import Field
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.admin import (
    AnalyticsResponse,
    DailyBookingCount,
    UserCreateByAdmin,
    UserCreateResponse,
    UserResponse,
    UserUpdateByAdmin,
)
from app.schemas.subscription import SubscriptionStatsItem, SubscriptionStatsResponse
from app.services.auth_service import pwd_context, require_role

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=list[UserResponse], summary="List all users")
async def list_users(
    role: str | None = Query(None, description="Filter by role: PLAYER, FIELD_OWNER, SUPER_ADMIN"),
    current_user: User = Depends(require_role("SUPER_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    result = await db.execute(stmt.order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.post("/users", response_model=UserCreateResponse, summary="Create a field owner account")
async def create_field_owner(
    body: UserCreateByAdmin,
    current_user: User = Depends(require_role("SUPER_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    # Check duplicate phone
    existing = await db.execute(select(User).where(User.phone_number == body.phone_number))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "DUPLICATE_PHONE", "message": "A user with this phone number already exists."}},
        )
        
    alphabet = string.ascii_letters + string.digits
    temp_password = ''.join(secrets.choice(alphabet) for i in range(10))
    
    user = User(
        phone_number=body.phone_number,
        display_name=body.display_name,
        role=body.role,
        password_hash=pwd_context.hash(temp_password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Return UserCreateResponse which includes the generated password
    user_dict = UserResponse.model_validate(user).model_dump()
    user_dict["temp_password"] = temp_password
    return UserCreateResponse(**user_dict)


@router.patch("/users/{user_id}", response_model=UserResponse, summary="Edit or deactivate a user")
async def update_user(
    user_id: UUID,
    body: UserUpdateByAdmin,
    current_user: User = Depends(require_role("SUPER_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "User not found."}})

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.get("/analytics", response_model=AnalyticsResponse, summary="Platform analytics")
async def get_analytics(
    current_user: User = Depends(require_role("SUPER_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)

    # Total active fields
    fields_result = await db.execute(
        select(func.count(Field.id)).where(Field.is_active == True)  # noqa: E712
    )
    total_active_fields: int = fields_result.scalar() or 0

    # Total bookings last 30 days
    bookings_result = await db.execute(
        select(func.count(Booking.id)).where(
            Booking.slot_date >= thirty_days_ago,
            Booking.status != "cancelled",
        )
    )
    total_bookings_30d: int = bookings_result.scalar() or 0

    # Daily booking counts (last 30 days)
    daily_result = await db.execute(
        select(Booking.slot_date, func.count(Booking.id))
        .where(
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

    return AnalyticsResponse(
        total_active_fields=total_active_fields,
        total_bookings_30d=total_bookings_30d,
        daily_bookings=daily_bookings,
    )


@router.get(
    "/analytics/subscriptions",
    response_model=SubscriptionStatsResponse,
    summary="Subscription stats per tier and field",
)
async def get_subscription_analytics(
    current_user: User = Depends(require_role("SUPER_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    # By tier
    tier_result = await db.execute(
        select(Subscription.tier, func.count(Subscription.id))
        .where(Subscription.status == "active")
        .group_by(Subscription.tier)
    )
    by_tier = {row[0]: row[1] for row in tier_result.all()}

    # By field
    field_result = await db.execute(
        select(Subscription.field_id, func.count(Subscription.id))
        .where(Subscription.status == "active")
        .group_by(Subscription.field_id)
    )
    by_field = []
    for field_id, count in field_result.all():
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
