"""signal_snapshot nullable score rank

Revision ID: a1b2c3d4e5f6
Revises: 8c872b9f6bda
Create Date: 2026-06-26 17:00:00.000000

Makes signal_snapshots.momentum_score and signal_snapshots.rank nullable
so WATCH rows (insufficient price history) can be persisted with NULL
score/rank instead of being dropped or coerced to a sentinel.

SQLite does not support `ALTER COLUMN ... DROP NOT NULL`, so the table
is rebuilt via batch_alter_table.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "8c872b9f6bda"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("signal_snapshots") as batch_op:
        batch_op.alter_column("momentum_score", nullable=True)
        batch_op.alter_column("rank", nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("signal_snapshots") as batch_op:
        batch_op.alter_column("rank", nullable=False)
        batch_op.alter_column("momentum_score", nullable=False)
