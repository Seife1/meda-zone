"""
auth_service.py — MedaZone authentication service.

Covers:
  - User lookup / creation
  - JWT access + refresh token lifecycle (python-jose)
  - Refresh token hashing (bcrypt) + Redis session revocation
  - Logout
  - FastAPI dependencies: get_current_user, require_role
"""

from __future__ import annotations

import logging
import random
import string
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, ExpiredSignatureError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.redis_client import (
    session_key,
)

logger = logging.getLogger(__name__)

# ── Bcrypt context ────────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── OAuth2 scheme (Bearer token from Authorization header) ────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


# ── 3. User creation / lookup ─────────────────────────────────────────────────

async def get_or_create_player(phone: str, db: AsyncSession) -> tuple[User, bool]:
    """
    Look up a Player by phone_number; create with role='PLAYER' if not found.

    Returns:
        (user, created) — created=True if the record was just inserted
    """
    result = await db.execute(select(User).where(User.phone_number == phone))
    user = result.scalar_one_or_none()
    if user is not None:
        return user, False

    user = User(phone_number=phone, role="PLAYER")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("New Player created for phone %s  id=%s", phone, user.id)
    return user, True


async def register_player(phone: str, password: str, display_name: str | None, db: AsyncSession) -> User:
    """Register a new player with phone + password. Raises 409 if phone already exists."""
    result = await db.execute(select(User).where(User.phone_number == phone))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "PHONE_TAKEN", "message": "This phone number is already registered."}},
        )
    user = User(
        phone_number=phone,
        display_name=display_name,
        role="PLAYER",
        password_hash=pwd_context.hash(password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("Player registered: phone=%s id=%s", phone, user.id)
    return user


async def login_player(phone: str, password: str, db: AsyncSession) -> User:
    """Authenticate player by phone + password. Raises 401 on failure."""
    result = await db.execute(select(User).where(User.phone_number == phone))
    user = result.scalar_one_or_none()
    if user is None or not user.password_hash or not pwd_context.verify(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_CREDENTIALS", "message": "Incorrect phone number or password."}},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "ACCOUNT_DISABLED", "message": "This account has been disabled."}},
        )
    return user


# ── 4. JWT token creation ─────────────────────────────────────────────────────

def create_access_token(subject: str, issued_at: datetime) -> str:
    """
    Encode access JWT.
    Payload: sub, iat, exp (iat + 24 h), jti
    """
    jti = str(uuid.uuid4())
    exp = issued_at + timedelta(hours=24)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": issued_at,
        "exp": exp,
        "jti": jti,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str, issued_at: datetime) -> str:
    """
    Encode refresh JWT.
    Payload: sub, iat, exp (iat + 30 days), jti
    """
    jti = str(uuid.uuid4())
    exp = issued_at + timedelta(days=30)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": issued_at,
        "exp": exp,
        "jti": jti,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and verify a JWT.

    Raises:
        HTTP 401 TOKEN_EXPIRED  — signature has expired
        HTTP 401 INVALID_TOKEN  — any other decode failure
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "TOKEN_EXPIRED", "message": "Token has expired."}},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Could not validate token."}},
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── 5. Refresh token management ───────────────────────────────────────────────

async def issue_tokens(user: User, db: AsyncSession, redis) -> tuple[str, str]:
    """
    Create a fresh access/refresh token pair.

    - Hashes the refresh token with bcrypt; stores hash on user.refresh_token_hash.
    - Stores Redis session key  session:{jti}  with 30-day TTL.

    Args:
        user:   The authenticated User whose tokens are being issued.
        db:     Async database session.
        redis:  Redis client (aioredis).

    Returns:
        (access_token, refresh_token)
    """
    issued_at = datetime.utcnow()

    access_token = create_access_token(str(user.id), issued_at)
    refresh_token = create_refresh_token(str(user.id), issued_at)

    # Extract jti from the refresh token to register the session
    refresh_payload = decode_token(refresh_token)
    jti = refresh_payload["jti"]

    # Hash and persist the refresh token
    user.refresh_token_hash = pwd_context.hash(refresh_token)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Register session in Redis (30-day TTL)
    await redis.set(session_key(jti), "valid", ex=60 * 60 * 24 * 30)

    return access_token, refresh_token


async def refresh_access_token(refresh_token: str, db: AsyncSession, redis) -> str:
    """
    Issue a new access token from a valid refresh token.

    Raises:
        HTTP 401 TOKEN_REVOKED  — session key not present in Redis
        HTTP 401 INVALID_TOKEN  — bcrypt hash mismatch or user not found
    """
    payload = decode_token(refresh_token)
    jti = payload.get("jti")
    subject = payload.get("sub")

    # Verify session is live in Redis
    session_exists = await redis.exists(session_key(jti))
    if not session_exists:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "TOKEN_REVOKED", "message": "Session has been revoked."}},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Load user and verify bcrypt hash
    result = await db.execute(select(User).where(User.id == uuid.UUID(subject)))
    user = result.scalar_one_or_none()
    if user is None or user.refresh_token_hash is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "User not found or no active session."}},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not pwd_context.verify(refresh_token, user.refresh_token_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Refresh token does not match stored hash."}},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Issue new access token only (refresh token stays the same)
    issued_at = datetime.utcnow()
    new_access_token = create_access_token(str(user.id), issued_at)
    return new_access_token


# ── 6. Logout ─────────────────────────────────────────────────────────────────

async def logout(user: User, refresh_token: str, db: AsyncSession, redis) -> None:
    """
    Revoke the refresh token:
      - Delete session:{jti} from Redis
      - Clear user.refresh_token_hash
    """
    try:
        payload = decode_token(refresh_token)
        jti = payload.get("jti")
        if jti:
            await redis.delete(session_key(jti))
    except HTTPException:
        # Token already expired/invalid — still clear local hash
        pass

    user.refresh_token_hash = None
    db.add(user)
    await db.commit()


# ── 7. Admin Firebase exchange ────────────────────────────────────────────────
# Removed as OTP and Firebase are completely replaced by phone + password.


# ── 8. FastAPI dependencies ───────────────────────────────────────────────────

async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency — extract and validate Bearer token, return active User.

    Raises HTTP 401 UNAUTHORIZED on any failure:
      - Missing token
      - Invalid / expired token
      - User not found
      - User is inactive
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": {"code": "UNAUTHORIZED", "message": "Could not validate credentials."}},
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = decode_token(token)
        subject: str | None = payload.get("sub")
        if subject is None:
            raise credentials_exception
    except HTTPException:
        raise credentials_exception

    try:
        user_id = uuid.UUID(subject)
    except ValueError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception

    return user


def require_role(*roles: str):
    """
    Returns a FastAPI dependency that enforces role membership.

    Usage:
        @router.get("/admin/...", dependencies=[Depends(require_role("SUPER_ADMIN"))])

    Raises HTTP 403 FORBIDDEN if the current user's role is not in `roles`.
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "FORBIDDEN", "message": f"Required role(s): {', '.join(roles)}."}},
            )
        return current_user

    return role_checker
