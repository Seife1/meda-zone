import uuid
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Time
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class SlotChangeProposal(Base):
    __tablename__ = "slot_change_proposals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subscriptions.id"), nullable=False
    )
    proposed_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    new_recurring_days: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False
    )
    new_session_start_time: Mapped[time] = mapped_column(Time, nullable=False)
    new_session_duration_hours: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending | approved | rejected | expired
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return (
            f"<SlotChangeProposal id={self.id} subscription={self.subscription_id} "
            f"status={self.status}>"
        )
