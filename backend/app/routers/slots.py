"""
Slots router — slot generation, status management, soft reservations.

Routes:
  GET    /fields/{field_id}/slots           — 7-day slot calendar (public)
  POST   /fields/{field_id}/slots/generate  — generate recurring slots (FIELD_OWNER)
  PATCH  /slots/{slot_id}/status            — close a slot (FIELD_OWNER)
  POST   /slots/{slot_id}/reserve           — soft reservation (Player)
  DELETE /slots/{slot_id}/reserve           — release soft reservation (Player)

Requirements: 4.2, 5.5, 10.1, 10.2, 10.3
"""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.redis_client import get_redis
from app.schemas.slot import (
    SlotGenerateRequest,
    SlotGenerateResponse,
    SlotResponse,
    SlotStatusPatch,
)
from app.services import slot_service
from app.services.auth_service import get_current_user, require_role
from app.models.user import User

router = APIRouter(tags=["Slots"])


@router.get(
    "/fields/{field_id}/slots",
    response_model=list[SlotResponse],
    summary="Get 7-day slot calendar for a field",
)
async def get_slots(
    field_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    slots = await slot_service.get_slots_for_field(db, field_id)
    return [SlotResponse.model_validate(s) for s in slots]


@router.post(
    "/fields/{field_id}/slots/generate",
    response_model=SlotGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate recurring slots for a field (FIELD_OWNER)",
)
async def generate_slots(
    field_id: UUID,
    body: SlotGenerateRequest,
    current_user: User = Depends(require_role("FIELD_OWNER", "SUPER_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    result = await slot_service.generate_slots(
        db=db,
        field_id=field_id,
        start_date=body.start_date,
        end_date=body.end_date,
        slot_duration_minutes=body.slot_duration_minutes,
        open_time_str=body.open_time,
        close_time_str=body.close_time,
    )
    return SlotGenerateResponse(**result)


@router.patch(
    "/slots/{slot_id}/status",
    response_model=SlotResponse,
    summary="Change slot status (FIELD_OWNER)",
)
async def change_slot_status(
    slot_id: UUID,
    body: SlotStatusPatch,
    current_user: User = Depends(require_role("FIELD_OWNER", "SUPER_ADMIN")),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    slot = await slot_service.change_slot_status(db, slot_id, body.status, redis)
    return SlotResponse.model_validate(slot)


@router.post(
    "/slots/{slot_id}/reserve",
    response_model=SlotResponse,
    summary="Create a 5-min soft reservation (Player)",
)
async def create_reservation(
    slot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    slot = await slot_service.create_soft_reservation(db, slot_id, current_user.id, redis)
    return SlotResponse.model_validate(slot)


@router.delete(
    "/slots/{slot_id}/reserve",
    response_model=SlotResponse,
    summary="Release a soft reservation (Player)",
)
async def release_reservation(
    slot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    slot = await slot_service.release_soft_reservation(db, slot_id, current_user.id, redis)
    return SlotResponse.model_validate(slot)
