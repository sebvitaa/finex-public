"""initial schema

Revision ID: 20260527_0001
Revises:
Create Date: 2026-05-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260527_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column("icon", sa.String(length=40), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
        sa.UniqueConstraint("name", name=op.f("uq_categories_name")),
    )
    op.create_index(op.f("ix_categories_id"), "categories", ["id"], unique=False)
    op.create_index(op.f("ix_categories_name"), "categories", ["name"], unique=False)

    op.create_table(
        "import_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("messages_seen", sa.Integer(), nullable=False),
        sa.Column("messages_imported", sa.Integer(), nullable=False),
        sa.Column("transactions_created", sa.Integer(), nullable=False),
        sa.Column("errors_count", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_runs")),
    )
    op.create_index(op.f("ix_import_runs_id"), "import_runs", ["id"], unique=False)
    op.create_index(op.f("ix_import_runs_source"), "import_runs", ["source"], unique=False)
    op.create_index(op.f("ix_import_runs_status"), "import_runs", ["status"], unique=False)

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

    op.create_table(
        "classification_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("field", sa.String(length=60), nullable=False),
        sa.Column("operator", sa.String(length=40), nullable=False),
        sa.Column("pattern", sa.String(length=240), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_from_correction", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], name=op.f("fk_classification_rules_category_id_categories")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_classification_rules")),
    )
    op.create_index(op.f("ix_classification_rules_category_id"), "classification_rules", ["category_id"], unique=False)
    op.create_index(op.f("ix_classification_rules_id"), "classification_rules", ["id"], unique=False)

    op.create_table(
        "email_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gmail_message_id", sa.String(length=240), nullable=True),
        sa.Column("gmail_thread_id", sa.String(length=240), nullable=True),
        sa.Column("gmail_history_id", sa.String(length=160), nullable=True),
        sa.Column("internet_message_id", sa.String(length=240), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sender_name", sa.String(length=160), nullable=True),
        sa.Column("sender_email", sa.String(length=240), nullable=True),
        sa.Column("subject", sa.String(length=240), nullable=False),
        sa.Column("body_preview", sa.Text(), nullable=True),
        sa.Column("body_hash", sa.String(length=128), nullable=True),
        sa.Column("label_id", sa.String(length=160), nullable=True),
        sa.Column("import_run_id", sa.Integer(), nullable=True),
        sa.Column("parse_status", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(["import_run_id"], ["import_runs.id"], name=op.f("fk_email_messages_import_run_id_import_runs")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_messages")),
        sa.UniqueConstraint("gmail_message_id", name=op.f("uq_email_messages_gmail_message_id")),
    )
    op.create_index(op.f("ix_email_messages_body_hash"), "email_messages", ["body_hash"], unique=False)
    op.create_index(op.f("ix_email_messages_gmail_history_id"), "email_messages", ["gmail_history_id"], unique=False)
    op.create_index(op.f("ix_email_messages_gmail_message_id"), "email_messages", ["gmail_message_id"], unique=False)
    op.create_index(op.f("ix_email_messages_gmail_thread_id"), "email_messages", ["gmail_thread_id"], unique=False)
    op.create_index(op.f("ix_email_messages_id"), "email_messages", ["id"], unique=False)
    op.create_index(op.f("ix_email_messages_import_run_id"), "email_messages", ["import_run_id"], unique=False)
    op.create_index(op.f("ix_email_messages_internet_message_id"), "email_messages", ["internet_message_id"], unique=False)
    op.create_index(op.f("ix_email_messages_label_id"), "email_messages", ["label_id"], unique=False)
    op.create_index(op.f("ix_email_messages_parse_status"), "email_messages", ["parse_status"], unique=False)
    op.create_index(op.f("ix_email_messages_received_at"), "email_messages", ["received_at"], unique=False)

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("merchant_name", sa.String(length=160), nullable=True),
        sa.Column("counterparty", sa.String(length=160), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("subject", sa.String(length=240), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("source_message_id", sa.String(length=160), nullable=True),
        sa.Column("payment_method", sa.String(length=80), nullable=True),
        sa.Column("transaction_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("classification_method", sa.String(length=40), nullable=True),
        sa.Column("classification_reason", sa.String(length=240), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], name=op.f("fk_transactions_category_id_categories"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transactions")),
    )
    op.create_index(op.f("ix_transactions_category_id"), "transactions", ["category_id"], unique=False)
    op.create_index(op.f("ix_transactions_id"), "transactions", ["id"], unique=False)
    op.create_index(op.f("ix_transactions_merchant_name"), "transactions", ["merchant_name"], unique=False)
    op.create_index(op.f("ix_transactions_occurred_at"), "transactions", ["occurred_at"], unique=False)
    op.create_index(op.f("ix_transactions_source"), "transactions", ["source"], unique=False)
    op.create_index(op.f("ix_transactions_source_message_id"), "transactions", ["source_message_id"], unique=False)
    op.create_index(op.f("ix_transactions_status"), "transactions", ["status"], unique=False)
    op.create_index(op.f("ix_transactions_transaction_type"), "transactions", ["transaction_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_transactions_transaction_type"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_status"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_source_message_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_source"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_occurred_at"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_merchant_name"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_category_id"), table_name="transactions")
    op.drop_table("transactions")
    op.drop_index(op.f("ix_email_messages_received_at"), table_name="email_messages")
    op.drop_index(op.f("ix_email_messages_parse_status"), table_name="email_messages")
    op.drop_index(op.f("ix_email_messages_label_id"), table_name="email_messages")
    op.drop_index(op.f("ix_email_messages_internet_message_id"), table_name="email_messages")
    op.drop_index(op.f("ix_email_messages_import_run_id"), table_name="email_messages")
    op.drop_index(op.f("ix_email_messages_id"), table_name="email_messages")
    op.drop_index(op.f("ix_email_messages_gmail_thread_id"), table_name="email_messages")
    op.drop_index(op.f("ix_email_messages_gmail_message_id"), table_name="email_messages")
    op.drop_index(op.f("ix_email_messages_gmail_history_id"), table_name="email_messages")
    op.drop_index(op.f("ix_email_messages_body_hash"), table_name="email_messages")
    op.drop_table("email_messages")
    op.drop_index(op.f("ix_classification_rules_id"), table_name="classification_rules")
    op.drop_index(op.f("ix_classification_rules_category_id"), table_name="classification_rules")
    op.drop_table("classification_rules")
    op.drop_index(op.f("ix_gmail_sync_state_label_id"), table_name="gmail_sync_state")
    op.drop_index(op.f("ix_gmail_sync_state_id"), table_name="gmail_sync_state")
    op.drop_index(op.f("ix_gmail_sync_state_history_id"), table_name="gmail_sync_state")
    op.drop_table("gmail_sync_state")
    op.drop_index(op.f("ix_import_runs_status"), table_name="import_runs")
    op.drop_index(op.f("ix_import_runs_source"), table_name="import_runs")
    op.drop_index(op.f("ix_import_runs_id"), table_name="import_runs")
    op.drop_table("import_runs")
    op.drop_index(op.f("ix_categories_name"), table_name="categories")
    op.drop_index(op.f("ix_categories_id"), table_name="categories")
    op.drop_table("categories")
