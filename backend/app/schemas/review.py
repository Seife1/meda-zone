from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    field_id: UUID
    booking_id: UUID
    rating: int = Field(ge=1, le=5)
    review_text: str | None = None


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    player_id: UUID
    field_id: UUID
    booking_id: UUID
    rating: int
    review_text: str | None
    created_at: datetime
