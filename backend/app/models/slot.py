import uuid
from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, ForeignKey, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class Slot(Base):
    __tablename__ = "slots"
    __table_args__ = (
        UniqueConstraint(
            "field_id", "slot_date", "start_time", name="uq_slot_field_date_time"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fields.id"), nullable=False
    )
    slot_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(nullable=False)
    # 30 | 60 | 90
    status: Mapped[str] = mapped_column(String(20), default="available")
    # available | pending | booked | closed
    soft_reserved_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    soft_reserved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return (
            f"<Slot id={self.id} field={self.field_id} "
            f"date={self.slot_date} start={self.start_time} status={self.status}>"
        )
