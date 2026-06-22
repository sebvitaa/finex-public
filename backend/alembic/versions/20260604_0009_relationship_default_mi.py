"""Default transaction relationship category to mi.

Revision ID: 20260604_0009
Revises: 20260604_0008
Create Date: 2026-06-04 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_0009"
down_revision = "20260604_0008"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    bind = op.get_bind()
    return set(sa.inspect(bind).get_table_names())


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {column["name"] for column in sa.inspect(bind).get_columns(table_name)}


def upgrade() -> None:
    if "transactions" not in _tables() or "relationship_category" not in _columns("transactions"):
        return
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.alter_column(
            "relationship_category",
            existing_type=sa.String(length=40),
            existing_nullable=False,
            server_default="mi",
        )


def downgrade() -> None:
    if "transactions" not in _tables() or "relationship_category" not in _columns("transactions"):
        return
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.alter_column(
            "relationship_category",
            existing_type=sa.String(length=40),
            existing_nullable=False,
            server_default="ninguna",
        )
