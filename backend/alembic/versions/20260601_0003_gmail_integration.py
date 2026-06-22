"""Add Gmail integration state.

Revision ID: 20260601_0003
Revises: 20260529_0002
Create Date: 2026-06-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260601_0003"
down_revision = "20260529_0002"
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
    if "gmail_sync_state" not in tables:
        op.create_table(
            "gmail_sync_state",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("label_id", sa.String(length=160), nullable=False),
            sa.Column("history_id", sa.String(length=160), nullable=True),
            sa.Column("watch_expiration_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_poll_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_push_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_gmail_sync_state")),
            sa.UniqueConstraint("label_id", name=op.f("uq_gmail_sync_state_label_id")),
        )
        op.create_index(op.f("ix_gmail_sync_state_history_id"), "gmail_sync_state", ["history_id"], unique=False)
        op.create_index(op.f("ix_gmail_sync_state_id"), "gmail_sync_state", ["id"], unique=False)
        op.create_index(op.f("ix_gmail_sync_state_label_id"), "gmail_sync_state", ["label_id"], unique=False)

    if "email_messages" in tables:
        columns = _columns("email_messages")
        with op.batch_alter_table("email_messages") as batch_op:
            if "gmail_message_id" not in columns:
                batch_op.add_column(sa.Column("gmail_message_id", sa.String(length=240), nullable=True))
            if "gmail_thread_id" not in columns:
                batch_op.add_column(sa.Column("gmail_thread_id", sa.String(length=240), nullable=True))
            if "gmail_history_id" not in columns:
                batch_op.add_column(sa.Column("gmail_history_id", sa.String(length=160), nullable=True))
            if "label_id" not in columns:
                batch_op.add_column(sa.Column("label_id", sa.String(length=160), nullable=True))

        indexes = _indexes("email_messages")
        if "ix_email_messages_gmail_message_id" not in indexes:
            op.create_index(op.f("ix_email_messages_gmail_message_id"), "email_messages", ["gmail_message_id"], unique=True)
        if "ix_email_messages_gmail_thread_id" not in indexes:
            op.create_index(op.f("ix_email_messages_gmail_thread_id"), "email_messages", ["gmail_thread_id"], unique=False)
        if "ix_email_messages_gmail_history_id" not in indexes:
            op.create_index(op.f("ix_email_messages_gmail_history_id"), "email_messages", ["gmail_history_id"], unique=False)
        if "ix_email_messages_label_id" not in indexes:
            op.create_index(op.f("ix_email_messages_label_id"), "email_messages", ["label_id"], unique=False)


def downgrade() -> None:
    tables = _tables()
    if "email_messages" in tables:
        indexes = _indexes("email_messages")
        for index_name in (
            "ix_email_messages_label_id",
            "ix_email_messages_gmail_history_id",
            "ix_email_messages_gmail_thread_id",
            "ix_email_messages_gmail_message_id",
        ):
            if index_name in indexes:
                op.drop_index(index_name, table_name="email_messages")

        columns = _columns("email_messages")
        with op.batch_alter_table("email_messages") as batch_op:
            for column_name in ("label_id", "gmail_history_id", "gmail_thread_id", "gmail_message_id"):
                if column_name in columns:
                    batch_op.drop_column(column_name)

    if "gmail_sync_state" in tables:
        op.drop_index(op.f("ix_gmail_sync_state_label_id"), table_name="gmail_sync_state")
        op.drop_index(op.f("ix_gmail_sync_state_id"), table_name="gmail_sync_state")
        op.drop_index(op.f("ix_gmail_sync_state_history_id"), table_name="gmail_sync_state")
        op.drop_table("gmail_sync_state")
