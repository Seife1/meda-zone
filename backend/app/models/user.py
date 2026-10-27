import uuid
from datetime import datetime

from sqlalchemy import ARRAY, String, Text, Boolean
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))
    profile_photo_url: Mapped[str | None] = mapped_column(Text)
    preferred_positions: Mapped[list[str]] = mapped_column(
        PG_ARRAY(String), default=list, server_default="{}"
    )
    role: Mapped[str] = mapped_column(String(20), default="PLAYER")
    # roles: PLAYER | FIELD_OWNER | SUPER_ADMIN
    fcm_token: Mapped[str | None] = mapped_column(Text)
    refresh_token_hash: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} phone={self.phone_number} role={self.role}>"
