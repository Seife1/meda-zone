from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ChapaInitRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subscription_id: UUID
    return_url: str | None = None


class ChapaCheckoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    checkout_url: str
    tx_ref: str


class ArifPayInitRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subscription_id: UUID
    return_url: str | None = None


class ArifPaySessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_url: str
    session_id: str
