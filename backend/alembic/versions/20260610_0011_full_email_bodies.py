"""Store full Gmail email bodies.

Revision ID: 20260610_0011
Revises: 20260606_0010
Create Date: 2026-06-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260610_0011"
down_revision = "20260606_0010"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    bind = op.get_bind()
    return set(sa.inspect(bind).get_table_names())


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {column["name"] for column in sa.inspect(bind).get_columns(table_name)}


def upgrade() -> None:
    if "email_messages" not in _tables():
        return

    columns = _columns("email_messages")
    with op.batch_alter_table("email_messages") as batch_op:
        if "body_text" not in columns:
            batch_op.add_column(sa.Column("body_text", sa.Text(), nullable=True))
        if "body_html" not in columns:
            batch_op.add_column(sa.Column("body_html", sa.Text(), nullable=True))

    op.execute("UPDATE email_messages SET body_text = body_preview WHERE body_text IS NULL AND body_preview IS NOT NULL")


def downgrade() -> None:
    if "email_messages" not in _tables():
        return

    columns = _columns("email_messages")
    with op.batch_alter_table("email_messages") as batch_op:
        if "body_html" in columns:
            batch_op.drop_column("body_html")
        if "body_text" in columns:
            batch_op.drop_column("body_text")
