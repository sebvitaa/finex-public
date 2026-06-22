"""manual entries, splits and receivables

Revision ID: 20260529_0002
Revises: 20260527_0001
Create Date: 2026-05-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260529_0002"
down_revision: Union[str, Sequence[str], None] = "20260527_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("categories") as batch_op:
        batch_op.add_column(sa.Column("parent_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("kind", sa.String(length=20), server_default="expense", nullable=False))
        batch_op.create_index(op.f("ix_categories_kind"), ["kind"], unique=False)
        batch_op.create_index(op.f("ix_categories_parent_id"), ["parent_id"], unique=False)
        batch_op.create_foreign_key(
            op.f("fk_categories_parent_id_categories"),
            "categories",
            ["parent_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_table(
        "people",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("alias", sa.String(length=80), nullable=True),
        sa.Column("email", sa.String(length=240), nullable=True),
        sa.Column("phone", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_people")),
    )
    op.create_index(op.f("ix_people_id"), "people", ["id"], unique=False)
    op.create_index(op.f("ix_people_name"), "people", ["name"], unique=False)

    op.create_table(
        "receivables",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("original_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("remaining_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], name=op.f("fk_receivables_person_id_people"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_receivables")),
    )
    op.create_index(op.f("ix_receivables_due_at"), "receivables", ["due_at"], unique=False)
    op.create_index(op.f("ix_receivables_id"), "receivables", ["id"], unique=False)
    op.create_index(op.f("ix_receivables_issued_at"), "receivables", ["issued_at"], unique=False)
    op.create_index(op.f("ix_receivables_person_id"), "receivables", ["person_id"], unique=False)
    op.create_index(op.f("ix_receivables_status"), "receivables", ["status"], unique=False)

    with op.batch_alter_table("transactions") as batch_op:
        batch_op.add_column(sa.Column("signed_amount", sa.Numeric(precision=12, scale=2), nullable=True))
        batch_op.add_column(sa.Column("person_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("receivable_id", sa.Integer(), nullable=True))
        batch_op.create_index(op.f("ix_transactions_person_id"), ["person_id"], unique=False)
        batch_op.create_index(op.f("ix_transactions_receivable_id"), ["receivable_id"], unique=False)
        batch_op.create_foreign_key(
            op.f("fk_transactions_person_id_people"),
            "people",
            ["person_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            op.f("fk_transactions_receivable_id_receivables"),
            "receivables",
            ["receivable_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_table(
        "transaction_splits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], name=op.f("fk_transaction_splits_category_id_categories"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], name=op.f("fk_transaction_splits_transaction_id_transactions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transaction_splits")),
    )
    op.create_index(op.f("ix_transaction_splits_category_id"), "transaction_splits", ["category_id"], unique=False)
    op.create_index(op.f("ix_transaction_splits_id"), "transaction_splits", ["id"], unique=False)
    op.create_index(op.f("ix_transaction_splits_transaction_id"), "transaction_splits", ["transaction_id"], unique=False)

    op.create_table(
        "receivable_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("receivable_id", sa.Integer(), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["receivable_id"], ["receivables.id"], name=op.f("fk_receivable_payments_receivable_id_receivables"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], name=op.f("fk_receivable_payments_transaction_id_transactions"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_receivable_payments")),
    )
    op.create_index(op.f("ix_receivable_payments_id"), "receivable_payments", ["id"], unique=False)
    op.create_index(op.f("ix_receivable_payments_paid_at"), "receivable_payments", ["paid_at"], unique=False)
    op.create_index(op.f("ix_receivable_payments_receivable_id"), "receivable_payments", ["receivable_id"], unique=False)
    op.create_index(op.f("ix_receivable_payments_transaction_id"), "receivable_payments", ["transaction_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_receivable_payments_transaction_id"), table_name="receivable_payments")
    op.drop_index(op.f("ix_receivable_payments_receivable_id"), table_name="receivable_payments")
    op.drop_index(op.f("ix_receivable_payments_paid_at"), table_name="receivable_payments")
    op.drop_index(op.f("ix_receivable_payments_id"), table_name="receivable_payments")
    op.drop_table("receivable_payments")

    op.drop_index(op.f("ix_transaction_splits_transaction_id"), table_name="transaction_splits")
    op.drop_index(op.f("ix_transaction_splits_id"), table_name="transaction_splits")
    op.drop_index(op.f("ix_transaction_splits_category_id"), table_name="transaction_splits")
    op.drop_table("transaction_splits")

    with op.batch_alter_table("transactions") as batch_op:
        batch_op.drop_constraint(op.f("fk_transactions_receivable_id_receivables"), type_="foreignkey")
        batch_op.drop_constraint(op.f("fk_transactions_person_id_people"), type_="foreignkey")
        batch_op.drop_index(op.f("ix_transactions_receivable_id"))
        batch_op.drop_index(op.f("ix_transactions_person_id"))
        batch_op.drop_column("receivable_id")
        batch_op.drop_column("person_id")
        batch_op.drop_column("signed_amount")

    op.drop_index(op.f("ix_receivables_status"), table_name="receivables")
    op.drop_index(op.f("ix_receivables_person_id"), table_name="receivables")
    op.drop_index(op.f("ix_receivables_issued_at"), table_name="receivables")
    op.drop_index(op.f("ix_receivables_id"), table_name="receivables")
    op.drop_index(op.f("ix_receivables_due_at"), table_name="receivables")
    op.drop_table("receivables")

    op.drop_index(op.f("ix_people_name"), table_name="people")
    op.drop_index(op.f("ix_people_id"), table_name="people")
    op.drop_table("people")

    with op.batch_alter_table("categories") as batch_op:
        batch_op.drop_constraint(op.f("fk_categories_parent_id_categories"), type_="foreignkey")
        batch_op.drop_index(op.f("ix_categories_parent_id"))
        batch_op.drop_index(op.f("ix_categories_kind"))
        batch_op.drop_column("kind")
        batch_op.drop_column("parent_id")
