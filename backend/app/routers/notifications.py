"""
Notifications router — player notification preferences and FCM token management.

Routes:
  GET    /notifications/preferences        — get preferences (Player)
  PUT    /notifications/preferences        — update preferences (Player)
  POST   /notifications/watch/{field_id}   — watch a field (Player)
  DELETE /notifications/watch/{field_id}   — unwatch a field (Player)
  PUT    /users/me/fcm-token               — register / update FCM token (Player)

Requirements: 8.4, 8.5
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.notification_preference import NotificationPreference
from app.models.user import User
from app.schemas.notification import NotificationPreferenceResponse, NotificationPreferenceUpdate
from app.services.auth_service import get_current_user

router = APIRouter(tags=["Notifications"])


async def _get_or_create_prefs(db: AsyncSession, player_id) -> NotificationPreference:
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.player_id == player_id)
    )
    prefs = result.scalar_one_or_none()
    if prefs is None:
        prefs = NotificationPreference(player_id=player_id)
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)
    return prefs


@router.get(
    "/notifications/preferences",
    response_model=NotificationPreferenceResponse,
    summary="Get notification preferences",
)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = await _get_or_create_prefs(db, current_user.id)
    return NotificationPreferenceResponse.model_validate(prefs)


@router.put(
    "/notifications/preferences",
    response_model=NotificationPreferenceResponse,
    summary="Update notification preferences",
)
async def update_preferences(
    body: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = await _get_or_create_prefs(db, current_user.id)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(prefs, field, value)
    await db.commit()
    await db.refresh(prefs)
    return NotificationPreferenceResponse.model_validate(prefs)


@router.post(
    "/notifications/watch/{field_id}",
    summary="Watch a field for slot availability",
)
async def watch_field(
    field_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = await _get_or_create_prefs(db, current_user.id)
    field_id_str = str(field_id)
    if field_id_str not in (prefs.watched_field_ids or []):
        prefs.watched_field_ids = list(prefs.watched_field_ids or []) + [field_id_str]
        await db.commit()
    return {"message": "Now watching field for availability"}


@router.delete(
    "/notifications/watch/{field_id}",
    summary="Unwatch a field",
)
async def unwatch_field(
    field_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = await _get_or_create_prefs(db, current_user.id)
    field_id_str = str(field_id)
    prefs.watched_field_ids = [fid for fid in (prefs.watched_field_ids or []) if fid != field_id_str]
    await db.commit()
    return {"message": "Stopped watching field"}


@router.put("/users/me/fcm-token", summary="Register or update FCM token")
async def update_fcm_token(
    token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.fcm_token = token
    db.add(current_user)
    await db.commit()
    return {"message": "FCM token updated"}
