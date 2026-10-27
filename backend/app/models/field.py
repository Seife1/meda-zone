import uuid
from datetime import date, datetime
from decimal import Decimal

from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class Field(Base):
    __tablename__ = "fields"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    neighborhood: Mapped[str | None] = mapped_column(String(100))
    location: Mapped[WKBElement] = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=True), nullable=False
    )
    surface_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # grass | artificial | futsal
    field_size: Mapped[str | None] = mapped_column(String(20))
    # 5-a-side | 7-a-side | 11-a-side
    amenities: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )
    # {"lighting": true, "changing_rooms": false, "parking": true, "water": true}
    price_per_hour: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    operating_hours: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )
    # {"open": "06:00", "close": "22:00", "days": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]}
    photo_urls: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}"
    )
    average_rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), default=0.0, server_default="0.0"
    )
    review_count: Mapped[int] = mapped_column(default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_sponsored: Mapped[bool] = mapped_column(Boolean, default=False)
    sponsorship_start: Mapped[date | None] = mapped_column(Date)
    sponsorship_end: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Field id={self.id} name={self.name}>"
