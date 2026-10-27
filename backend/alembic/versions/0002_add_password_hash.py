"""Add password_hash to users.

Revision ID: 0002passhash
Revises: 0001medazone
Create Date: 2025-01-02 00:00:00
"""
import sqlalchemy as sa
from alembic import op

revision = "0002passhash"
down_revision = "0001medazone"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_hash")
