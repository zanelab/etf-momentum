"""etf pools + pool members

Revision ID: c1d2e3f4a5b6
Revises: b1c2d3e4f5a6
Create Date: 2026-06-27 00:00:00.000000

Adds two tables for user-defined strategy pools:

- etf_pools: id, name UNIQUE, description, created_at, updated_at
- etf_pool_members: (pool_id, etf_code) composite PK + position INT

pool_id references etf_pools.id with ON DELETE CASCADE so deleting a
pool cleans up its member rows in one transaction.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "etf_pools",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_etf_pools_name"),
    )
    op.create_index(op.f("ix_etf_pools_name"), "etf_pools", ["name"], unique=True)

    op.create_table(
        "etf_pool_members",
        sa.Column("pool_id", sa.Integer(), nullable=False),
        sa.Column("etf_code", sa.String(length=10), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["pool_id"], ["etf_pools.id"], name="fk_etf_pool_members_pool_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["etf_code"], ["etfs.code"], name="fk_etf_pool_members_etf_code",
        ),
        sa.PrimaryKeyConstraint("pool_id", "etf_code"),
    )
    op.create_index(
        op.f("ix_etf_pool_members_pool_id"), "etf_pool_members", ["pool_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_etf_pool_members_pool_id"), table_name="etf_pool_members")
    op.drop_table("etf_pool_members")
    op.drop_index(op.f("ix_etf_pools_name"), table_name="etf_pools")
    op.drop_table("etf_pools")
