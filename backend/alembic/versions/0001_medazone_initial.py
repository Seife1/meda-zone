"""MedaZone initial schema.

Revision ID: 0001medazone
Revises:
Create Date: 2025-01-01 00:00:00

Creates all 8 MedaZone tables:
  users → fields → slots → subscriptions → bookings →
  slot_change_proposals → reviews → notification_preferences
"""

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "0001medazone"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("profile_photo_url", sa.Text(), nullable=True),
        sa.Column("preferred_positions", postgresql.ARRAY(sa.String()), server_default="{}", nullable=True),
        sa.Column("role", sa.String(20), nullable=False, server_default="PLAYER"),
        sa.Column("fcm_token", sa.Text(), nullable=True),
        sa.Column("refresh_token_hash", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone_number"),
    )

    op.create_table(
        "fields",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("neighborhood", sa.String(100), nullable=True),
        sa.Column("location", geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column("surface_type", sa.String(20), nullable=False),
        sa.Column("field_size", sa.String(20), nullable=True),
        sa.Column("amenities", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=True),
        sa.Column("price_per_hour", sa.Numeric(10, 2), nullable=False),
        sa.Column("operating_hours", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=True),
        sa.Column("photo_urls", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=True),
        sa.Column("average_rating", sa.Numeric(3, 2), nullable=False, server_default="0.0"),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_sponsored", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sponsorship_start", sa.Date(), nullable=True),
        sa.Column("sponsorship_end", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_fields_location", "fields", ["location"], postgresql_using="gist")

    op.create_table(
        "slots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("field_id", sa.UUID(), nullable=False),
        sa.Column("slot_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="available"),
        sa.Column("soft_reserved_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("soft_reserved_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["field_id"], ["fields.id"]),
        sa.ForeignKeyConstraint(["soft_reserved_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("field_id", "slot_date", "start_time", name="uq_slot_field_date_time"),
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("player_id", sa.UUID(), nullable=False),
        sa.Column("field_id", sa.UUID(), nullable=False),
        sa.Column("proposed_by", sa.UUID(), nullable=False),
        sa.Column("recurring_days", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("session_start_time", sa.Time(), nullable=False),
        sa.Column("session_duration_hours", sa.Numeric(4, 2), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("total_sessions", sa.Integer(), nullable=False),
        sa.Column("total_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending_payment"),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("payment_provider", sa.String(20), nullable=True),
        sa.Column("payment_tx_ref", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["field_id"], ["fields.id"]),
        sa.ForeignKeyConstraint(["player_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["proposed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "bookings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("reference", sa.String(20), nullable=False),
        sa.Column("player_id", sa.UUID(), nullable=False),
        sa.Column("field_id", sa.UUID(), nullable=False),
        sa.Column("slot_id", sa.UUID(), nullable=False),
        sa.Column("subscription_id", sa.UUID(), nullable=True),
        sa.Column("slot_date", sa.Date(), nullable=False),
        sa.Column("slot_start_time", sa.Time(), nullable=False),
        sa.Column("slot_end_time", sa.Time(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="confirmed"),
        sa.Column("cancellation_reason", sa.String(50), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["field_id"], ["fields.id"]),
        sa.ForeignKeyConstraint(["player_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["slot_id"], ["slots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference"),
        sa.UniqueConstraint("field_id", "slot_date", "slot_start_time", name="uq_booking_field_slot"),
    )
    op.create_foreign_key("fk_booking_subscription", "bookings", "subscriptions", ["subscription_id"], ["id"])

    op.create_table(
        "slot_change_proposals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("subscription_id", sa.UUID(), nullable=False),
        sa.Column("proposed_by", sa.UUID(), nullable=False),
        sa.Column("new_recurring_days", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("new_session_start_time", sa.Time(), nullable=False),
        sa.Column("new_session_duration_hours", sa.Numeric(4, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["proposed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "reviews",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("player_id", sa.UUID(), nullable=False),
        sa.Column("field_id", sa.UUID(), nullable=False),
        sa.Column("booking_id", sa.UUID(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("review_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"]),
        sa.ForeignKeyConstraint(["field_id"], ["fields.id"]),
        sa.ForeignKeyConstraint(["player_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", "booking_id", name="uq_review_player_booking"),
    )

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("player_id", sa.UUID(), nullable=False),
        sa.Column("booking_confirmed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("booking_reminder", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("booking_cancelled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("slot_available", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("subscription_expiry", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("watched_field_ids", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["player_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", name="uq_notif_pref_player"),
    )


def downgrade() -> None:
    op.drop_table("notification_preferences")
    op.drop_table("reviews")
    op.drop_table("slot_change_proposals")
    op.drop_constraint("fk_booking_subscription", "bookings", type_="foreignkey")
    op.drop_table("bookings")
    op.drop_table("subscriptions")
    op.drop_index("idx_fields_location", table_name="fields")
    op.drop_table("slots")
    op.drop_table("fields")
    op.drop_table("users")
