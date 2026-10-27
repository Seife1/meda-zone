import uuid
from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, ForeignKey, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint(
            "field_id",
            "slot_date",
            "slot_start_time",
            name="uq_booking_field_slot",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reference: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    # e.g. "MZ-20250612-AB4F"
    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fields.id"), nullable=False
    )
    slot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("slots.id"), nullable=False
    )
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("subscriptions.id", use_alter=True, name="fk_booking_subscription"),
        nullable=True,
    )
    slot_date: Mapped[date] = mapped_column(Date, nullable=False)
    slot_start_time: Mapped[time] = mapped_column(Time, nullable=False)
    slot_end_time: Mapped[time] = mapped_column(Time, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    # confirmed | checked_in | cancelled
    cancellation_reason: Mapped[str | None] = mapped_column(String(50))
    # player_initiated | field_owner_initiated
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return (
            f"<Booking id={self.id} ref={self.reference} "
            f"player={self.player_id} status={self.status}>"
        )
