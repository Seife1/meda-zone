import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("player_id", name="uq_notif_pref_player"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    booking_confirmed: Mapped[bool] = mapped_column(Boolean, default=True)
    booking_reminder: Mapped[bool] = mapped_column(Boolean, default=True)
    booking_cancelled: Mapped[bool] = mapped_column(Boolean, default=True)
    slot_available: Mapped[bool] = mapped_column(Boolean, default=True)
    subscription_expiry: Mapped[bool] = mapped_column(Boolean, default=True)
    # fields the player has opted into availability alerts for
    watched_field_ids: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<NotificationPreference id={self.id} player={self.player_id}>"
        )
