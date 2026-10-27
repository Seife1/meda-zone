"""
chapa_service.py — Chapa payment gateway integration for MedaZone subscriptions.

Flow:
  1. Player selects Chapa on the payment screen.
  2. Mobile calls POST /payments/chapa/initialize → initialize_payment() returns checkout_url.
  3. Player completes payment in WebView.
  4. Chapa POSTs to /payments/chapa/webhook → verify_webhook() + handle_success().
  5. handle_success() calls subscription_service.activate() to activate subscription
     and auto-generate all booking records.

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
from app.schemas.payment import ChapaCheckoutResponse

logger = logging.getLogger(__name__)

CHAPA_BASE_URL = "https://api.chapa.co/v1"


# ---------------------------------------------------------------------------
# 1. Initialize payment  (Requirement 17.5)
# ---------------------------------------------------------------------------

async def initialize_payment(sub, return_url: Optional[str] = None) -> ChapaCheckoutResponse:
    """
    Initialize a Chapa checkout session for a subscription payment.

    Args:
        sub: Subscription ORM object with total_price, id, player_id, field_id
        return_url: optional browser redirect URL after payment

    Returns:
        ChapaCheckoutResponse with checkout_url and tx_ref

    Raises:
        HTTP 400 PAYMENT_FAILED if Chapa API call fails
    """
    if not settings.CHAPA_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "PAYMENT_FAILED", "message": "Chapa payments are not configured."}},
        )

    tx_ref = f"MZ-{sub.id}-{int(time.time())}"

    # Store tx_ref on subscription so webhook can look it up
    # (caller must commit after calling this)
    sub.payment_tx_ref = tx_ref
    sub.payment_provider = "chapa"

    webhook_url = (
        settings.CHAPA_WEBHOOK_URL
        or f"{settings.API_BASE_URL}/api/v1/payments/chapa/webhook"
    )

    payload = {
        "amount": str(sub.total_price),
        "currency": "ETB",
        "email": "player@medazone.et",  # placeholder; ideally fetched from player profile
        "first_name": "MedaZone",
        "last_name": "Player",
        "tx_ref": tx_ref,
        "description": f"MedaZone subscription {sub.tier} — {sub.total_sessions} sessions",
        "callback_url": webhook_url,
        "return_url": return_url or f"{settings.API_BASE_URL}/payment/success",
        "customization": {
            "title": "MedaZone",
            "description": "Football field subscription payment",
        },
    }

    headers = {
        "Authorization": f"Bearer {settings.CHAPA_SECRET}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{CHAPA_BASE_URL}/transaction/initialize",
                json=payload,
                headers=headers,
            )

        if resp.status_code != 200:
            logger.error("Chapa initialize returned %s: %s", resp.status_code, resp.text)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "PAYMENT_FAILED", "message": f"Chapa API error: {resp.status_code}"}},
            )

        data = resp.json()
        if data.get("status") != "success":
            logger.error("Chapa non-success response: %s", data)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "PAYMENT_FAILED", "message": data.get("message", "Chapa payment failed.")}},
            )

        checkout_url = data.get("data", {}).get("checkout_url") or data.get("checkout_url")
        if not checkout_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "PAYMENT_FAILED", "message": "Chapa did not return a checkout URL."}},
            )

        logger.info("Chapa session created: tx_ref=%s sub=%s", tx_ref, sub.id)
        return ChapaCheckoutResponse(checkout_url=checkout_url, tx_ref=tx_ref)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Chapa initialize error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "PAYMENT_FAILED", "message": "Chapa payment initialization failed."}},
        ) from exc


# ---------------------------------------------------------------------------
# 2. Verify webhook signature  (Requirement 17.7)
# ---------------------------------------------------------------------------

def verify_webhook(payload: dict, signature: str) -> bool:
    """
    Verify HMAC-SHA256 signature of a Chapa webhook.

    Chapa sends the hex digest of HMAC-SHA256(raw_body, CHAPA_WEBHOOK_SECRET)
    in the 'Chapa-Signature' header.

    Returns True if valid, False otherwise.
    """
    secret = settings.CHAPA_WEBHOOK_SECRET
    if not secret:
        logger.warning("CHAPA_WEBHOOK_SECRET not set — skipping signature verification")
        return True

    import json
    raw_body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip())


# ---------------------------------------------------------------------------
# 3. Handle successful payment  (Requirement 17.6)
# ---------------------------------------------------------------------------

async def handle_success(tx_ref: str, db: AsyncSession, redis) -> None:
    """
    Called by the Chapa webhook handler after signature verification.

    Looks up the subscription by payment_tx_ref, activates it, and triggers
    auto-generation of all booking records via subscription_service.activate().

    Requirements: 17.6
    """
    from sqlalchemy import select
    from app.models.subscription import Subscription
    from app.services import subscription_service  # local import to avoid circular

    result = await db.execute(
        select(Subscription).where(Subscription.payment_tx_ref == tx_ref)
    )
    sub = result.scalar_one_or_none()

    if sub is None:
        logger.error("Chapa handle_success: no subscription found for tx_ref=%s", tx_ref)
        return

    if sub.status == "active":
        logger.info("Chapa handle_success: subscription %s already active", sub.id)
        return

    await subscription_service.activate(db, sub.id, redis)
    logger.info("Chapa payment processed: sub=%s tx_ref=%s", sub.id, tx_ref)


# ---------------------------------------------------------------------------
# 4. Verify transaction (manual lookup)
# ---------------------------------------------------------------------------

async def verify_transaction(tx_ref: str) -> Optional[dict]:
    """Verify a Chapa transaction via the verify endpoint."""
    if not settings.CHAPA_ENABLED:
        return None

    headers = {"Authorization": f"Bearer {settings.CHAPA_SECRET}"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{CHAPA_BASE_URL}/transaction/verify/{tx_ref}",
                headers=headers,
            )
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data.get("data") if data.get("status") == "success" else None
    except Exception as exc:
        logger.error("Chapa verify error: %s", exc)
        return None
