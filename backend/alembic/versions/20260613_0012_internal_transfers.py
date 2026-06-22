"""Internal transfers between own accounts.

Revision ID: 20260613_0012
Revises: 20260610_0011
Create Date: 2026-06-13 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260613_0012"
down_revision = "20260610_0011"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    bind = op.get_bind()
    return set(sa.inspect(bind).get_table_names())


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {column["name"] for column in sa.inspect(bind).get_columns(table_name)}


def upgrade() -> None:
    if "transactions" not in _tables():
        return

    columns = _columns("transactions")
    with op.batch_alter_table("transactions") as batch_op:
        if "destination_account_id" not in columns:
            batch_op.add_column(sa.Column("destination_account_id", sa.Integer(), nullable=True))
        if "destination_amount" not in columns:
            batch_op.add_column(sa.Column("destination_amount", sa.Numeric(14, 2), nullable=True))
        if "destination_currency" not in columns:
            batch_op.add_column(sa.Column("destination_currency", sa.String(length=3), nullable=True))


def downgrade() -> None:
    if "transactions" not in _tables():
        return

    columns = _columns("transactions")
    with op.batch_alter_table("transactions") as batch_op:
        if "destination_currency" in columns:
            batch_op.drop_column("destination_currency")
        if "destination_amount" in columns:
            batch_op.drop_column("destination_amount")
        if "destination_account_id" in columns:
            batch_op.drop_column("destination_account_id")
