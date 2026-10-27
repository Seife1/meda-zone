"""
Payments router — Chapa and ArifPay subscription payment flows.

Routes:
  POST /payments/chapa/initialize    — Player; init Chapa checkout
  POST /payments/chapa/webhook       — Server-to-server Chapa callback
  POST /payments/arifpay/initialize  — Player; init ArifPay checkout
  POST /payments/arifpay/webhook     — Server-to-server ArifPay callback

Requirements: 17.5, 17.7
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.redis_client import get_redis
from app.models.subscription import Subscription
from app.schemas.payment import (
    ArifPayInitRequest,
    ArifPaySessionResponse,
    ChapaCheckoutResponse,
    ChapaInitRequest,
)
from app.services import arifpay_service, chapa_service
from app.services.auth_service import get_current_user
from app.models.user import User

router = APIRouter(prefix="/payments", tags=["Payments"])


# ── Chapa ─────────────────────────────────────────────────────────────────────

@router.post(
    "/chapa/initialize",
    response_model=ChapaCheckoutResponse,
    summary="Initialize Chapa payment for a subscription",
)
async def chapa_initialize(
    body: ChapaInitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription).where(Subscription.id == body.subscription_id)
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Subscription not found."}})
    if sub.player_id != current_user.id:
        raise HTTPException(status_code=403, detail={"error": {"code": "FORBIDDEN", "message": "Not your subscription."}})

    checkout = await chapa_service.initialize_payment(sub, return_url=body.return_url)
    await db.commit()
    return checkout


@router.post("/chapa/webhook", summary="Chapa server-to-server payment callback")
async def chapa_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    payload = await request.json()
    sig = request.headers.get("Chapa-Signature", "")

    if not chapa_service.verify_webhook(payload, sig):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "INVALID_SIGNATURE", "message": "Webhook signature verification failed."}},
        )

    tx_ref = payload.get("tx_ref") or payload.get("data", {}).get("tx_ref")
    if tx_ref:
        await chapa_service.handle_success(tx_ref, db, redis)

    return {"status": "ok"}


# ── ArifPay ───────────────────────────────────────────────────────────────────

@router.post(
    "/arifpay/initialize",
    response_model=ArifPaySessionResponse,
    summary="Initialize ArifPay payment for a subscription",
)
async def arifpay_initialize(
    body: ArifPayInitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription).where(Subscription.id == body.subscription_id)
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Subscription not found."}})
    if sub.player_id != current_user.id:
        raise HTTPException(status_code=403, detail={"error": {"code": "FORBIDDEN", "message": "Not your subscription."}})

    session = await arifpay_service.initialize_payment(sub, return_url=body.return_url)
    await db.commit()
    return session


@router.post("/arifpay/webhook", summary="ArifPay server-to-server payment callback")
async def arifpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    payload = await request.json()
    sig = request.headers.get("x-arifpay-signature", "")

    if not arifpay_service.verify_webhook(payload, sig):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "INVALID_SIGNATURE", "message": "Webhook signature verification failed."}},
        )

    session_id = payload.get("sessionId") or payload.get("nonce")
    if session_id:
        await arifpay_service.handle_success(session_id, db, redis)

    return {"status": "ok"}
