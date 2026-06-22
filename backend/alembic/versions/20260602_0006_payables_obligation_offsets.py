"""Add payables, offsets and payable transaction links.

Revision ID: 20260602_0006
Revises: 20260602_0005
Create Date: 2026-06-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260602_0006"
down_revision = "20260602_0005"
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

    if "payables" not in tables:
        op.create_table(
            "payables",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("person_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=160), nullable=False),
            sa.Column("original_amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("remaining_amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False),
            sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["person_id"], ["people.id"], name=op.f("fk_payables_person_id_people"), ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_payables")),
        )
        op.create_index(op.f("ix_payables_due_at"), "payables", ["due_at"], unique=False)
        op.create_index(op.f("ix_payables_id"), "payables", ["id"], unique=False)
        op.create_index(op.f("ix_payables_issued_at"), "payables", ["issued_at"], unique=False)
        op.create_index(op.f("ix_payables_person_id"), "payables", ["person_id"], unique=False)
        op.create_index(op.f("ix_payables_status"), "payables", ["status"], unique=False)

    tables = _tables()
    if "transactions" in tables:
        columns = _columns("transactions")
        with op.batch_alter_table("transactions") as batch_op:
            if "payable_id" not in columns:
                batch_op.add_column(sa.Column("payable_id", sa.Integer(), nullable=True))
                batch_op.create_index(op.f("ix_transactions_payable_id"), ["payable_id"], unique=False)
                batch_op.create_foreign_key(
                    op.f("fk_transactions_payable_id_payables"),
                    "payables",
                    ["payable_id"],
                    ["id"],
                    ondelete="SET NULL",
                )

    if "payable_payments" not in tables:
        op.create_table(
            "payable_payments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("payable_id", sa.Integer(), nullable=False),
            sa.Column("transaction_id", sa.Integer(), nullable=True),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["payable_id"], ["payables.id"], name=op.f("fk_payable_payments_payable_id_payables"), ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], name=op.f("fk_payable_payments_transaction_id_transactions"), ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_payable_payments")),
        )
        op.create_index(op.f("ix_payable_payments_id"), "payable_payments", ["id"], unique=False)
        op.create_index(op.f("ix_payable_payments_paid_at"), "payable_payments", ["paid_at"], unique=False)
        op.create_index(op.f("ix_payable_payments_payable_id"), "payable_payments", ["payable_id"], unique=False)
        op.create_index(op.f("ix_payable_payments_transaction_id"), "payable_payments", ["transaction_id"], unique=False)

    tables = _tables()
    if "obligation_offsets" not in tables:
        op.create_table(
            "obligation_offsets",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("person_id", sa.Integer(), nullable=False),
            sa.Column("receivable_id", sa.Integer(), nullable=True),
            sa.Column("payable_id", sa.Integer(), nullable=True),
            sa.Column("offset_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("resulting_direction", sa.String(length=40), nullable=False),
            sa.Column("resulting_amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["payable_id"], ["payables.id"], name=op.f("fk_obligation_offsets_payable_id_payables"), ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["person_id"], ["people.id"], name=op.f("fk_obligation_offsets_person_id_people"), ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["receivable_id"], ["receivables.id"], name=op.f("fk_obligation_offsets_receivable_id_receivables"), ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_obligation_offsets")),
        )
        op.create_index(op.f("ix_obligation_offsets_id"), "obligation_offsets", ["id"], unique=False)
        op.create_index(op.f("ix_obligation_offsets_offset_at"), "obligation_offsets", ["offset_at"], unique=False)
        op.create_index(op.f("ix_obligation_offsets_payable_id"), "obligation_offsets", ["payable_id"], unique=False)
        op.create_index(op.f("ix_obligation_offsets_person_id"), "obligation_offsets", ["person_id"], unique=False)
        op.create_index(op.f("ix_obligation_offsets_receivable_id"), "obligation_offsets", ["receivable_id"], unique=False)


def downgrade() -> None:
    tables = _tables()

    if "obligation_offsets" in tables:
        for index_name in _indexes("obligation_offsets"):
            op.drop_index(index_name, table_name="obligation_offsets")
        op.drop_table("obligation_offsets")

    if "payable_payments" in tables:
        for index_name in _indexes("payable_payments"):
            op.drop_index(index_name, table_name="payable_payments")
        op.drop_table("payable_payments")

    tables = _tables()
    if "transactions" in tables and "payable_id" in _columns("transactions"):
        with op.batch_alter_table("transactions") as batch_op:
            batch_op.drop_constraint(op.f("fk_transactions_payable_id_payables"), type_="foreignkey")
            batch_op.drop_index(op.f("ix_transactions_payable_id"))
            batch_op.drop_column("payable_id")

    tables = _tables()
    if "payables" in tables:
        for index_name in _indexes("payables"):
            op.drop_index(index_name, table_name="payables")
        op.drop_table("payables")
