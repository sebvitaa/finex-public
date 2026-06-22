"""Add financial and investment accounts.

Revision ID: 20260603_0007
Revises: 20260602_0006
Create Date: 2026-06-03 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260603_0007"
down_revision = "20260602_0006"
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

    if "financial_accounts" not in tables:
        op.create_table(
            "financial_accounts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("institution", sa.String(length=120), nullable=True),
            sa.Column("account_type", sa.String(length=40), nullable=False),
            sa.Column("product_name", sa.String(length=120), nullable=True),
            sa.Column("last_four", sa.String(length=4), nullable=True),
            sa.Column("currency", sa.String(length=3), nullable=False),
            sa.Column("opening_balance", sa.Numeric(14, 2), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_financial_accounts")),
        )
        op.create_index(op.f("ix_financial_accounts_account_type"), "financial_accounts", ["account_type"], unique=False)
        op.create_index(op.f("ix_financial_accounts_id"), "financial_accounts", ["id"], unique=False)
        op.create_index(op.f("ix_financial_accounts_institution"), "financial_accounts", ["institution"], unique=False)
        op.create_index(op.f("ix_financial_accounts_is_active"), "financial_accounts", ["is_active"], unique=False)
        op.create_index(op.f("ix_financial_accounts_last_four"), "financial_accounts", ["last_four"], unique=False)
        op.create_index(op.f("ix_financial_accounts_name"), "financial_accounts", ["name"], unique=False)

    tables = _tables()
    if "financial_account_snapshots" not in tables:
        op.create_table(
            "financial_account_snapshots",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("financial_account_id", sa.Integer(), nullable=False),
            sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("balance", sa.Numeric(14, 2), nullable=False),
            sa.Column("source", sa.String(length=40), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["financial_account_id"], ["financial_accounts.id"], name=op.f("fk_financial_account_snapshots_financial_account_id_financial_accounts"), ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_financial_account_snapshots")),
        )
        op.create_index(op.f("ix_financial_account_snapshots_captured_at"), "financial_account_snapshots", ["captured_at"], unique=False)
        op.create_index(op.f("ix_financial_account_snapshots_financial_account_id"), "financial_account_snapshots", ["financial_account_id"], unique=False)
        op.create_index(op.f("ix_financial_account_snapshots_id"), "financial_account_snapshots", ["id"], unique=False)

    tables = _tables()
    if "investment_accounts" not in tables:
        op.create_table(
            "investment_accounts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("institution", sa.String(length=120), nullable=True),
            sa.Column("account_type", sa.String(length=40), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False),
            sa.Column("current_value", sa.Numeric(14, 2), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_investment_accounts")),
        )
        op.create_index(op.f("ix_investment_accounts_account_type"), "investment_accounts", ["account_type"], unique=False)
        op.create_index(op.f("ix_investment_accounts_id"), "investment_accounts", ["id"], unique=False)
        op.create_index(op.f("ix_investment_accounts_institution"), "investment_accounts", ["institution"], unique=False)
        op.create_index(op.f("ix_investment_accounts_is_active"), "investment_accounts", ["is_active"], unique=False)
        op.create_index(op.f("ix_investment_accounts_name"), "investment_accounts", ["name"], unique=False)

    tables = _tables()
    if "transactions" in tables:
        columns = _columns("transactions")
        with op.batch_alter_table("transactions") as batch_op:
            if "financial_account_id" not in columns:
                batch_op.add_column(sa.Column("financial_account_id", sa.Integer(), nullable=True))
                batch_op.create_index(op.f("ix_transactions_financial_account_id"), ["financial_account_id"], unique=False)
                batch_op.create_foreign_key(op.f("fk_transactions_financial_account_id_financial_accounts"), "financial_accounts", ["financial_account_id"], ["id"], ondelete="SET NULL")
            if "investment_account_id" not in columns:
                batch_op.add_column(sa.Column("investment_account_id", sa.Integer(), nullable=True))
                batch_op.create_index(op.f("ix_transactions_investment_account_id"), ["investment_account_id"], unique=False)
                batch_op.create_foreign_key(op.f("fk_transactions_investment_account_id_investment_accounts"), "investment_accounts", ["investment_account_id"], ["id"], ondelete="SET NULL")
            if "account_detection_method" not in columns:
                batch_op.add_column(sa.Column("account_detection_method", sa.String(length=40), nullable=True))
            if "account_detection_confidence" not in columns:
                batch_op.add_column(sa.Column("account_detection_confidence", sa.Float(), nullable=True))
            if "account_detection_reason" not in columns:
                batch_op.add_column(sa.Column("account_detection_reason", sa.String(length=240), nullable=True))

    tables = _tables()
    if "investment_movements" not in tables:
        op.create_table(
            "investment_movements",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("investment_account_id", sa.Integer(), nullable=False),
            sa.Column("transaction_id", sa.Integer(), nullable=True),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("movement_type", sa.String(length=40), nullable=False),
            sa.Column("amount", sa.Numeric(14, 2), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False),
            sa.Column("units", sa.Numeric(18, 6), nullable=True),
            sa.Column("unit_price", sa.Numeric(14, 4), nullable=True),
            sa.Column("source", sa.String(length=40), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["investment_account_id"], ["investment_accounts.id"], name=op.f("fk_investment_movements_investment_account_id_investment_accounts"), ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], name=op.f("fk_investment_movements_transaction_id_transactions"), ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_investment_movements")),
        )
        op.create_index(op.f("ix_investment_movements_id"), "investment_movements", ["id"], unique=False)
        op.create_index(op.f("ix_investment_movements_investment_account_id"), "investment_movements", ["investment_account_id"], unique=False)
        op.create_index(op.f("ix_investment_movements_movement_type"), "investment_movements", ["movement_type"], unique=False)
        op.create_index(op.f("ix_investment_movements_occurred_at"), "investment_movements", ["occurred_at"], unique=False)
        op.create_index(op.f("ix_investment_movements_transaction_id"), "investment_movements", ["transaction_id"], unique=False)


def downgrade() -> None:
    tables = _tables()
    if "investment_movements" in tables:
        for index_name in _indexes("investment_movements"):
            op.drop_index(index_name, table_name="investment_movements")
        op.drop_table("investment_movements")

    tables = _tables()
    if "transactions" in tables:
        columns = _columns("transactions")
        with op.batch_alter_table("transactions") as batch_op:
            if "investment_account_id" in columns:
                batch_op.drop_constraint(op.f("fk_transactions_investment_account_id_investment_accounts"), type_="foreignkey")
                batch_op.drop_index(op.f("ix_transactions_investment_account_id"))
                batch_op.drop_column("investment_account_id")
            if "financial_account_id" in columns:
                batch_op.drop_constraint(op.f("fk_transactions_financial_account_id_financial_accounts"), type_="foreignkey")
                batch_op.drop_index(op.f("ix_transactions_financial_account_id"))
                batch_op.drop_column("financial_account_id")
            for column_name in ("account_detection_reason", "account_detection_confidence", "account_detection_method"):
                if column_name in columns:
                    batch_op.drop_column(column_name)

    for table_name in ("investment_accounts", "financial_account_snapshots", "financial_accounts"):
        tables = _tables()
        if table_name in tables:
            for index_name in _indexes(table_name):
                op.drop_index(index_name, table_name=table_name)
            op.drop_table(table_name)
