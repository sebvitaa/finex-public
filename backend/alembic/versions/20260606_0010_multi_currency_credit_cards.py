"""Add multi-currency money fields and credit card metadata.

Revision ID: 20260606_0010
Revises: 20260604_0009
Create Date: 2026-06-06 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260606_0010"
down_revision = "20260604_0009"
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

    if "transactions" in tables:
        columns = _columns("transactions")
        with op.batch_alter_table("transactions") as batch_op:
            if "original_amount" not in columns:
                batch_op.add_column(sa.Column("original_amount", sa.Numeric(14, 2), nullable=True))
            if "original_currency" not in columns:
                batch_op.add_column(sa.Column("original_currency", sa.String(length=3), nullable=False, server_default="CLP"))
            if "amount_clp" not in columns:
                batch_op.add_column(sa.Column("amount_clp", sa.Numeric(14, 2), nullable=True))
            if "exchange_rate" not in columns:
                batch_op.add_column(sa.Column("exchange_rate", sa.Numeric(14, 6), nullable=True))
            if "exchange_rate_source" not in columns:
                batch_op.add_column(sa.Column("exchange_rate_source", sa.String(length=80), nullable=True))
            if "exchange_rate_date" not in columns:
                batch_op.add_column(sa.Column("exchange_rate_date", sa.DateTime(timezone=True), nullable=True))
            if "currency_detection_confidence" not in columns:
                batch_op.add_column(sa.Column("currency_detection_confidence", sa.Float(), nullable=True))
            if "currency_detection_reason" not in columns:
                batch_op.add_column(sa.Column("currency_detection_reason", sa.String(length=240), nullable=True))

        op.execute("UPDATE transactions SET currency = UPPER(COALESCE(currency, 'CLP'))")
        op.execute("UPDATE transactions SET original_amount = amount WHERE original_amount IS NULL")
        op.execute("UPDATE transactions SET original_currency = currency WHERE original_currency IS NULL OR original_currency = ''")
        op.execute("UPDATE transactions SET original_currency = UPPER(original_currency)")
        op.execute("UPDATE transactions SET amount_clp = amount WHERE amount_clp IS NULL AND currency = 'CLP'")

    if "financial_accounts" in tables:
        columns = _columns("financial_accounts")
        with op.batch_alter_table("financial_accounts") as batch_op:
            if "credit_limit_amount" not in columns:
                batch_op.add_column(sa.Column("credit_limit_amount", sa.Numeric(14, 2), nullable=True))
            if "credit_limit_currency" not in columns:
                batch_op.add_column(sa.Column("credit_limit_currency", sa.String(length=3), nullable=True))
            if "available_credit_amount" not in columns:
                batch_op.add_column(sa.Column("available_credit_amount", sa.Numeric(14, 2), nullable=True))
            if "used_credit_amount" not in columns:
                batch_op.add_column(sa.Column("used_credit_amount", sa.Numeric(14, 2), nullable=True))
            if "billing_cycle_day" not in columns:
                batch_op.add_column(sa.Column("billing_cycle_day", sa.Integer(), nullable=True))
            if "payment_due_day" not in columns:
                batch_op.add_column(sa.Column("payment_due_day", sa.Integer(), nullable=True))
            if "statement_amount" not in columns:
                batch_op.add_column(sa.Column("statement_amount", sa.Numeric(14, 2), nullable=True))
            if "statement_currency" not in columns:
                batch_op.add_column(sa.Column("statement_currency", sa.String(length=3), nullable=True))
            if "statement_amount_overridden" not in columns:
                batch_op.add_column(sa.Column("statement_amount_overridden", sa.Boolean(), nullable=False, server_default=sa.false()))
            if "statement_override_reason" not in columns:
                batch_op.add_column(sa.Column("statement_override_reason", sa.Text(), nullable=True))
            if "card_art_variant" not in columns:
                batch_op.add_column(sa.Column("card_art_variant", sa.String(length=20), nullable=True))
            if "visual_group" not in columns:
                batch_op.add_column(sa.Column("visual_group", sa.String(length=120), nullable=True))
                batch_op.create_index(op.f("ix_financial_accounts_visual_group"), ["visual_group"], unique=False)

        op.execute("UPDATE financial_accounts SET currency = UPPER(COALESCE(currency, 'CLP'))")
        op.execute(
            "UPDATE financial_accounts "
            "SET credit_limit_currency = currency "
            "WHERE credit_limit_currency IS NULL AND credit_limit_amount IS NOT NULL"
        )
        op.execute(
            "UPDATE financial_accounts "
            "SET statement_currency = currency "
            "WHERE statement_currency IS NULL AND statement_amount IS NOT NULL"
        )

    if "financial_account_snapshots" in tables:
        columns = _columns("financial_account_snapshots")
        if "currency" not in columns:
            with op.batch_alter_table("financial_account_snapshots") as batch_op:
                batch_op.add_column(sa.Column("currency", sa.String(length=3), nullable=False, server_default="CLP"))
            op.execute("UPDATE financial_account_snapshots SET currency = UPPER(COALESCE(currency, 'CLP'))")

    tables = _tables()
    if "credit_card_statements" not in tables:
        op.create_table(
            "credit_card_statements",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("financial_account_id", sa.Integer(), nullable=False),
            sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
            sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("statement_amount", sa.Numeric(14, 2), nullable=False),
            sa.Column("statement_currency", sa.String(length=3), nullable=False),
            sa.Column("calculated_amount", sa.Numeric(14, 2), nullable=False),
            sa.Column("is_overridden", sa.Boolean(), nullable=False),
            sa.Column("override_reason", sa.Text(), nullable=True),
            sa.Column("source", sa.String(length=40), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["financial_account_id"], ["financial_accounts.id"], name=op.f("fk_credit_card_statements_financial_account_id_financial_accounts"), ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_credit_card_statements")),
        )
        op.create_index(op.f("ix_credit_card_statements_due_at"), "credit_card_statements", ["due_at"], unique=False)
        op.create_index(op.f("ix_credit_card_statements_financial_account_id"), "credit_card_statements", ["financial_account_id"], unique=False)
        op.create_index(op.f("ix_credit_card_statements_id"), "credit_card_statements", ["id"], unique=False)
        op.create_index(op.f("ix_credit_card_statements_period_end"), "credit_card_statements", ["period_end"], unique=False)
        op.create_index(op.f("ix_credit_card_statements_period_start"), "credit_card_statements", ["period_start"], unique=False)


def downgrade() -> None:
    tables = _tables()

    if "credit_card_statements" in tables:
        for index_name in _indexes("credit_card_statements"):
            op.drop_index(index_name, table_name="credit_card_statements")
        op.drop_table("credit_card_statements")

    if "financial_account_snapshots" in tables:
        columns = _columns("financial_account_snapshots")
        if "currency" in columns:
            with op.batch_alter_table("financial_account_snapshots") as batch_op:
                batch_op.drop_column("currency")

    if "financial_accounts" in tables:
        columns = _columns("financial_accounts")
        with op.batch_alter_table("financial_accounts") as batch_op:
            if "visual_group" in columns:
                if op.f("ix_financial_accounts_visual_group") in _indexes("financial_accounts"):
                    batch_op.drop_index(op.f("ix_financial_accounts_visual_group"))
                batch_op.drop_column("visual_group")
            for column_name in (
                "card_art_variant",
                "statement_override_reason",
                "statement_amount_overridden",
                "statement_currency",
                "statement_amount",
                "payment_due_day",
                "billing_cycle_day",
                "used_credit_amount",
                "available_credit_amount",
                "credit_limit_currency",
                "credit_limit_amount",
            ):
                if column_name in columns:
                    batch_op.drop_column(column_name)

    if "transactions" in tables:
        columns = _columns("transactions")
        with op.batch_alter_table("transactions") as batch_op:
            for column_name in (
                "currency_detection_reason",
                "currency_detection_confidence",
                "exchange_rate_date",
                "exchange_rate_source",
                "exchange_rate",
                "amount_clp",
                "original_currency",
                "original_amount",
            ):
                if column_name in columns:
                    batch_op.drop_column(column_name)
