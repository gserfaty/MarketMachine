"""create forecasts ledger

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def upgrade():
    op.create_table(
        "forecasts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("as_of", sa.Date, nullable=False),
        sa.Column("horizon", sa.Integer, nullable=False),
        sa.Column("region", sa.String, nullable=False),
        sa.Column("pred", sa.Float, nullable=False),
        sa.Column("lo", sa.Float, nullable=False),
        sa.Column("hi", sa.Float, nullable=False),
        sa.Column("model_version", sa.String),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("as_of", "horizon", "region", "model_version"),
    )
    op.create_index("ix_forecasts_as_of", "forecasts", ["as_of"])


def downgrade():
    op.drop_table("forecasts")
