import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Time
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fields.id"), nullable=False
    )
    proposed_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    # field owner's user id
    recurring_days: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False
    )
    # e.g. ["Monday", "Wednesday"]
    session_start_time: Mapped[time] = mapped_column(Time, nullable=False)
    session_duration_hours: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False
    )
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    # 1_month | 2_months | 3_months
    total_sessions: Mapped[int] = mapped_column(nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending_payment")
    # pending_payment | active | expired | cancelled
    start_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    payment_provider: Mapped[str | None] = mapped_column(String(20))
    # chapa | arifpay
    payment_tx_ref: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<Subscription id={self.id} player={self.player_id} "
            f"field={self.field_id} status={self.status}>"
        )
