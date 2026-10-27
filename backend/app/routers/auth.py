"""
Auth router — Phone+Password auth for Players; Firebase exchange for Field Owners / Super Admins.

Routes:
  POST /auth/register        — public; register with phone + password
  POST /auth/login           — public; login with phone + password, return tokens
  POST /auth/refresh         — public; refresh access token
  POST /auth/logout          — Player; revoke refresh token
  POST /auth/admin/login     — public; Firebase ID-token exchange
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.redis_client import get_redis
from app.schemas.auth import (
    RefreshRequest,
    TokenResponse,
    UserBasic,
)
from app.services import auth_service
from app.services.auth_service import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    phone_number: str
    password: str
    display_name: str | None = None


class LoginRequest(BaseModel):
    phone_number: str
    password: str


@router.post("/register", response_model=TokenResponse, summary="Register with phone + password")
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    user = await auth_service.register_player(
        phone=body.phone_number,
        password=body.password,
        display_name=body.display_name,
        db=db,
    )
    access_token, refresh_token = await auth_service.issue_tokens(user, db, redis)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserBasic.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse, summary="Login with phone + password")
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    user = await auth_service.login_player(
        phone=body.phone_number,
        password=body.password,
        db=db,
    )
    access_token, refresh_token = await auth_service.issue_tokens(user, db, redis)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserBasic.model_validate(user),
    )


@router.post("/refresh", summary="Refresh access token")
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    new_access_token = await auth_service.refresh_access_token(body.refresh_token, db, redis)
    return {"access_token": new_access_token, "token_type": "bearer"}


@router.post("/logout", summary="Revoke refresh token")
async def logout(
    body: RefreshRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    await auth_service.logout(current_user, body.refresh_token, db, redis)
    return {"message": "Logged out successfully"}


@router.post("/admin/login", response_model=TokenResponse, summary="Admin login — phone+password")
async def admin_login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """
    Accepts phone_number + password to login for Admin accounts.
    """
    user = await auth_service.login_player(body.phone_number, body.password, db)
    if user.role not in ("FIELD_OWNER", "SUPER_ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Not an admin account."}},
        )

    access_token, refresh_token = await auth_service.issue_tokens(user, db, redis)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserBasic.model_validate(user),
    )
