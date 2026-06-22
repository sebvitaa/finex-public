"""Add Gmail visibility and people relationship category.

Revision ID: 20260602_0004
Revises: 20260601_0003
Create Date: 2026-06-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260602_0004"
down_revision = "20260601_0003"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    bind = op.get_bind()
    return set(sa.inspect(bind).get_table_names())


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {column["name"] for column in sa.inspect(bind).get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}


def upgrade() -> None:
    tables = _tables()

    if "email_messages" in tables:
        columns = _columns("email_messages")
        with op.batch_alter_table("email_messages") as batch_op:
            if "is_visible" not in columns:
                batch_op.add_column(sa.Column("is_visible", sa.Boolean(), server_default=sa.true(), nullable=False))
        indexes = _indexes("email_messages")
        if "ix_email_messages_is_visible" not in indexes:
            op.create_index(op.f("ix_email_messages_is_visible"), "email_messages", ["is_visible"], unique=False)

    if "people" in tables:
        columns = _columns("people")
        with op.batch_alter_table("people") as batch_op:
            if "relationship_category" not in columns:
                batch_op.add_column(
                    sa.Column("relationship_category", sa.String(length=40), server_default="ninguna", nullable=False)
                )
        indexes = _indexes("people")
        if "ix_people_relationship_category" not in indexes:
            op.create_index(op.f("ix_people_relationship_category"), "people", ["relationship_category"], unique=False)


def downgrade() -> None:
    tables = _tables()

    if "people" in tables:
        indexes = _indexes("people")
        if "ix_people_relationship_category" in indexes:
            op.drop_index(op.f("ix_people_relationship_category"), table_name="people")
        columns = _columns("people")
        if "relationship_category" in columns:
            with op.batch_alter_table("people") as batch_op:
                batch_op.drop_column("relationship_category")

    if "email_messages" in tables:
        indexes = _indexes("email_messages")
        if "ix_email_messages_is_visible" in indexes:
            op.drop_index(op.f("ix_email_messages_is_visible"), table_name="email_messages")
        columns = _columns("email_messages")
        if "is_visible" in columns:
            with op.batch_alter_table("email_messages") as batch_op:
                batch_op.drop_column("is_visible")
