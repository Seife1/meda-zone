from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PlayerRegisterRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    phone_number: str
    password: str
    display_name: str | None = None


class RefreshRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    refresh_token: str


class LoginRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    phone_number: str
    password: str


class UserBasic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    phone_number: str
    display_name: str | None
    role: str


class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserBasic
