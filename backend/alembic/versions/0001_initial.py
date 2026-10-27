"""Initial Phase 1 schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-27
"""
import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    roles = op.create_table(
        "roles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(30), nullable=False, unique=True),
        sa.Column("label", sa.String(60), nullable=False),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(60), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("phone", sa.String(30)),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
    )
    op.create_table(
        "products",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("name_bn", sa.String(200)),
        sa.Column("sku", sa.String(60), nullable=False, unique=True),
        sa.Column("barcode", sa.String(80), unique=True),
        sa.Column("category_id", sa.Integer, sa.ForeignKey("categories.id")),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("buy_price_paisa", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("retail_price_paisa", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("wholesale_price_paisa", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("low_stock_milli", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_products_name", "products", ["name"])

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(30)),
        sa.Column("address", sa.Text),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("credit_limit_paisa", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("opening_balance_paisa", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("notes", sa.Text),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_customers_name", "customers", ["name"])
    op.create_index("ix_customers_phone", "customers", ["phone"])

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("doc_type", sa.String(20), nullable=False),
        sa.Column("number", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("customer_id", sa.Integer, sa.ForeignKey("customers.id")),
        sa.Column("customer_name", sa.String(200), nullable=False),
        sa.Column("customer_phone", sa.String(30)),
        sa.Column("customer_address", sa.Text),
        sa.Column("price_tier", sa.String(20), nullable=False),
        sa.Column("subtotal_paisa", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("discount_paisa", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("total_paisa", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("paid_paisa", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("payment_status", sa.String(20)),
        sa.Column("notes", sa.Text),
        sa.Column("parent_id", sa.Integer, sa.ForeignKey("documents.id")),
        sa.Column("moves_stock", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("assigned_to_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("approved_by_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("verify_token", sa.String(64), nullable=False, unique=True),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("voided_at", sa.DateTime),
        sa.Column("voided_by_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("void_reason", sa.Text),
        sa.UniqueConstraint("doc_type", "number", name="uq_documents_type_number"),
    )
    op.create_index("ix_documents_doc_type", "documents", ["doc_type"])
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_customer_id", "documents", ["customer_id"])
    op.create_index("ix_documents_payment_status", "documents", ["payment_status"])
    op.create_index("ix_documents_created_at", "documents", ["created_at"])

    op.create_table(
        "document_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("line_no", sa.Integer, nullable=False),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id"), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("qty_milli", sa.BigInteger, nullable=False),
        sa.Column("unit_price_paisa", sa.BigInteger, nullable=False),
        sa.Column("discount_paisa", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("line_total_paisa", sa.BigInteger, nullable=False),
        sa.Column("buy_price_paisa", sa.BigInteger, nullable=False, server_default="0"),
    )
    op.create_index("ix_document_items_document_id", "document_items", ["document_id"])

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id"), nullable=False),
        sa.Column("qty_milli", sa.BigInteger, nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("documents.id")),
        sa.Column("reversal_of_id", sa.Integer, sa.ForeignKey("stock_movements.id")),
        sa.Column("reference", sa.String(120)),
        sa.Column("reason", sa.Text),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
    )
    op.create_index("ix_stock_movements_product_created", "stock_movements", ["product_id", "created_at"])
    op.create_index("ix_stock_movements_document_id", "stock_movements", ["document_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("customer_id", sa.Integer, sa.ForeignKey("customers.id")),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("documents.id")),
        sa.Column("amount_paisa", sa.BigInteger, nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("reference", sa.String(120)),
        sa.Column("note", sa.Text),
        sa.Column("paid_at", sa.DateTime, nullable=False),
        sa.Column("reversal_of_id", sa.Integer, sa.ForeignKey("payments.id")),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_payments_customer_id", "payments", ["customer_id"])
    op.create_index("ix_payments_document_id", "payments", ["document_id"])
    op.create_index("ix_payments_paid_at", "payments", ["paid_at"])

    op.create_table(
        "installments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("seq", sa.Integer, nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("amount_paisa", sa.BigInteger, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("document_id", "seq", name="uq_installments_doc_seq"),
    )
    op.create_index("ix_installments_document_id", "installments", ["document_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("at", sa.DateTime, nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("entity", sa.String(40), nullable=False),
        sa.Column("entity_id", sa.Integer),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("field", sa.String(60)),
        sa.Column("old_value", sa.Text),
        sa.Column("new_value", sa.Text),
        sa.Column("reason", sa.Text),
    )
    op.create_index("ix_audit_logs_at", "audit_logs", ["at"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity", "entity_id"])

    op.create_table(
        "settings",
        sa.Column("key", sa.String(60), primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
    )

    op.bulk_insert(roles, [
        {"id": 1, "name": "owner", "label": "Owner"},
        {"id": 2, "name": "manager", "label": "Manager"},
        {"id": 3, "name": "cashier", "label": "Cashier"},
        {"id": 4, "name": "warehouse", "label": "Warehouse"},
        {"id": 5, "name": "delivery", "label": "Delivery"},
    ])


def downgrade() -> None:
    for table in ("settings", "audit_logs", "installments", "payments", "stock_movements",
                  "document_items", "documents", "customers", "products", "categories",
                  "users", "roles"):
        op.drop_table(table)
