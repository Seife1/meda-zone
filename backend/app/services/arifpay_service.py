"""
arifpay_service.py — ArifPay payment gateway integration for MedaZone subscriptions.

Flow mirrors Chapa:
  1. Mobile calls POST /payments/arifpay/initialize → initialize_payment() returns payment_url.
  2. Player completes payment in WebView.
  3. ArifPay POSTs to /payments/arifpay/webhook → verify_webhook() + handle_success().

Requirements: 17.5, 17.6, 17.7
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Optional

import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.payment import ArifPaySessionResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Initialize payment  (Requirement 17.5)
# ---------------------------------------------------------------------------

async def initialize_payment(sub, return_url: Optional[str] = None) -> ArifPaySessionResponse:
    """
    Initialize an ArifPay checkout session for a subscription payment.

    Returns:
        ArifPaySessionResponse with payment_url and session_id

    Raises:
        HTTP 400 PAYMENT_FAILED on any error
    """
    if not settings.ARIFPAY_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "PAYMENT_FAILED", "message": "ArifPay payments are not configured."}},
        )

    nonce = f"MZ-{sub.id}-{int(time.time())}"

    sub.payment_tx_ref = nonce
    sub.payment_provider = "arifpay"

    notify_url = f"{settings.API_BASE_URL}/api/v1/payments/arifpay/webhook"
    success_url = return_url or f"{settings.API_BASE_URL}/payment/success"
    cancel_url = f"{settings.API_BASE_URL}/payment/cancel"
    error_url = f"{settings.API_BASE_URL}/payment/error"

    payload = {
        "cancelUrl": cancel_url,
        "successUrl": success_url,
        "errorUrl": error_url,
        "notifyUrl": notify_url,
        "paymentMethods": ["TELEBIRR", "MPESA", "AWASH", "COOP", "EBIRR", "DASHEN"],
        "items": [
            {
                "name": f"MedaZone subscription {sub.tier}",
                "price": float(sub.total_price),
                "quantity": 1,
            }
        ],
        "nonce": nonce,
    }

    headers = {
        "x-arifpay-key": settings.ARIFPAY_SECRET,
        "Content-Type": "application/json",
    }

    base_url = settings.ARIFPAY_BASE_URL
    ssl_verify = not settings.ARIFPAY_SANDBOX

    try:
        async with httpx.AsyncClient(timeout=15.0, verify=ssl_verify) as client:
            resp = await client.post(
                f"{base_url}/api/checkout/session",
                json=payload,
                headers=headers,
            )

        if resp.status_code != 200:
            logger.error("ArifPay initialize returned %s: %s", resp.status_code, resp.text)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "PAYMENT_FAILED", "message": f"ArifPay API error: {resp.status_code}"}},
            )

        data = resp.json()
        payment_url = data.get("data", {}).get("paymentUrl") or data.get("paymentUrl")
        session_id = data.get("data", {}).get("sessionId") or data.get("sessionId", nonce)

        if not payment_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "PAYMENT_FAILED", "message": "ArifPay did not return a payment URL."}},
            )

        logger.info("ArifPay session created: nonce=%s session_id=%s sub=%s", nonce, session_id, sub.id)
        return ArifPaySessionResponse(payment_url=payment_url, session_id=session_id)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("ArifPay initialize error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "PAYMENT_FAILED", "message": "ArifPay payment initialization failed."}},
        ) from exc


# ---------------------------------------------------------------------------
# 2. Verify webhook signature  (Requirement 17.7)
# ---------------------------------------------------------------------------

def verify_webhook(payload: dict, signature: str) -> bool:
    """
    Verify ArifPay webhook authenticity.

    ArifPay signs the payload with HMAC-SHA256 using ARIFPAY_SECRET.
    Returns True if valid (or if secret not configured — dev mode).
    """
    secret = settings.ARIFPAY_SECRET
    if not secret:
        logger.warning("ARIFPAY_SECRET not set — skipping signature verification")
        return True

    import json
    raw_body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip())


# ---------------------------------------------------------------------------
# 3. Handle successful payment  (Requirement 17.6)
# ---------------------------------------------------------------------------

async def handle_success(session_id: str, db: AsyncSession, redis) -> None:
    """
    Activate subscription after successful ArifPay payment.

    Looks up subscription by payment_tx_ref (the nonce), activates it.
    """
    from sqlalchemy import select
    from app.models.subscription import Subscription
    from app.services import subscription_service  # local import

    result = await db.execute(
        select(Subscription).where(Subscription.payment_tx_ref == session_id)
    )
    sub = result.scalar_one_or_none()

    if sub is None:
        logger.error("ArifPay handle_success: no subscription for session_id=%s", session_id)
        return

    if sub.status == "active":
        logger.info("ArifPay handle_success: subscription %s already active", sub.id)
        return

    await subscription_service.activate(db, sub.id, redis)
    logger.info("ArifPay payment processed: sub=%s session_id=%s", sub.id, session_id)
