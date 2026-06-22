"""Extend classification rules and feedback.

Revision ID: 20260604_0008
Revises: 20260603_0007
Create Date: 2026-06-04 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_0008"
down_revision = "20260603_0007"
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
    if "classification_rules" in tables:
        columns = _columns("classification_rules")
        with op.batch_alter_table("classification_rules") as batch_op:
            if "category_id" in columns:
                batch_op.alter_column("category_id", existing_type=sa.Integer(), nullable=True)
            if "transaction_type" not in columns:
                batch_op.add_column(sa.Column("transaction_type", sa.String(length=40), nullable=True))
                batch_op.create_index(op.f("ix_classification_rules_transaction_type"), ["transaction_type"], unique=False)
            if "financial_account_id" not in columns:
                batch_op.add_column(sa.Column("financial_account_id", sa.Integer(), nullable=True))
                batch_op.create_index(op.f("ix_classification_rules_financial_account_id"), ["financial_account_id"], unique=False)
                batch_op.create_foreign_key(
                    op.f("fk_classification_rules_financial_account_id_financial_accounts"),
                    "financial_accounts",
                    ["financial_account_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
            if "investment_account_id" not in columns:
                batch_op.add_column(sa.Column("investment_account_id", sa.Integer(), nullable=True))
                batch_op.create_index(op.f("ix_classification_rules_investment_account_id"), ["investment_account_id"], unique=False)
                batch_op.create_foreign_key(
                    op.f("fk_classification_rules_investment_account_id_investment_accounts"),
                    "investment_accounts",
                    ["investment_account_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
            if "confidence" not in columns:
                batch_op.add_column(sa.Column("confidence", sa.Float(), nullable=False, server_default="0.75"))
            if "notes" not in columns:
                batch_op.add_column(sa.Column("notes", sa.Text(), nullable=True))

    tables = _tables()
    if "classification_feedback" not in tables:
        op.create_table(
            "classification_feedback",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("transaction_id", sa.Integer(), nullable=True),
            sa.Column("source_message_id", sa.String(length=160), nullable=True),
            sa.Column("field", sa.String(length=60), nullable=False),
            sa.Column("pattern", sa.String(length=240), nullable=False),
            sa.Column("merchant_name", sa.String(length=160), nullable=True),
            sa.Column("sender_email", sa.String(length=240), nullable=True),
            sa.Column("subject", sa.String(length=240), nullable=True),
            sa.Column("previous_category_id", sa.Integer(), nullable=True),
            sa.Column("new_category_id", sa.Integer(), nullable=True),
            sa.Column("previous_financial_account_id", sa.Integer(), nullable=True),
            sa.Column("new_financial_account_id", sa.Integer(), nullable=True),
            sa.Column("previous_investment_account_id", sa.Integer(), nullable=True),
            sa.Column("new_investment_account_id", sa.Integer(), nullable=True),
            sa.Column("previous_transaction_type", sa.String(length=40), nullable=True),
            sa.Column("new_transaction_type", sa.String(length=40), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["new_category_id"], ["categories.id"], name=op.f("fk_classification_feedback_new_category_id_categories"), ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["new_financial_account_id"], ["financial_accounts.id"], name=op.f("fk_classification_feedback_new_financial_account_id_financial_accounts"), ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["new_investment_account_id"], ["investment_accounts.id"], name=op.f("fk_classification_feedback_new_investment_account_id_investment_accounts"), ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["previous_category_id"], ["categories.id"], name=op.f("fk_classification_feedback_previous_category_id_categories"), ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["previous_financial_account_id"], ["financial_accounts.id"], name=op.f("fk_classification_feedback_previous_financial_account_id_financial_accounts"), ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["previous_investment_account_id"], ["investment_accounts.id"], name=op.f("fk_classification_feedback_previous_investment_account_id_investment_accounts"), ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], name=op.f("fk_classification_feedback_transaction_id_transactions"), ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_classification_feedback")),
        )
        for column_name in (
            "id",
            "transaction_id",
            "source_message_id",
            "pattern",
            "merchant_name",
            "sender_email",
            "new_category_id",
            "new_financial_account_id",
            "new_investment_account_id",
            "new_transaction_type",
        ):
            op.create_index(op.f(f"ix_classification_feedback_{column_name}"), "classification_feedback", [column_name], unique=False)


def downgrade() -> None:
    tables = _tables()
    if "classification_feedback" in tables:
        for index_name in _indexes("classification_feedback"):
            op.drop_index(index_name, table_name="classification_feedback")
        op.drop_table("classification_feedback")

    tables = _tables()
    if "classification_rules" in tables:
        columns = _columns("classification_rules")
        with op.batch_alter_table("classification_rules") as batch_op:
            for column_name in ("notes", "confidence"):
                if column_name in columns:
                    batch_op.drop_column(column_name)
            if "investment_account_id" in columns:
                batch_op.drop_constraint(op.f("fk_classification_rules_investment_account_id_investment_accounts"), type_="foreignkey")
                batch_op.drop_index(op.f("ix_classification_rules_investment_account_id"))
                batch_op.drop_column("investment_account_id")
            if "financial_account_id" in columns:
                batch_op.drop_constraint(op.f("fk_classification_rules_financial_account_id_financial_accounts"), type_="foreignkey")
                batch_op.drop_index(op.f("ix_classification_rules_financial_account_id"))
                batch_op.drop_column("financial_account_id")
            if "transaction_type" in columns:
                batch_op.drop_index(op.f("ix_classification_rules_transaction_type"))
                batch_op.drop_column("transaction_type")
            if "category_id" in columns:
                batch_op.alter_column("category_id", existing_type=sa.Integer(), nullable=False)
