import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("player_id", "booking_id", name="uq_review_player_booking"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fields.id"), nullable=False
    )
    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id"), nullable=False
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    # 1–5
    review_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return (
            f"<Review id={self.id} player={self.player_id} "
            f"field={self.field_id} rating={self.rating}>"
        )
