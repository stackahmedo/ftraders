"""Database models.

Conventions (portable SQLite -> PostgreSQL):
* money columns end in `_paisa` and are BIGINT (integer paisa, never float)
* quantity columns end in `_milli` and are BIGINT (1 unit = 1000)
* all timestamps are stored as naive UTC; the API converts to Asia/Dhaka for display
* enum-like columns are plain strings validated in the app, so later phases can add
  new values (e.g. purchase_order, sales_return) without rewriting constraints
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    BigInteger, Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------- enum values
ROLES = ("owner", "manager", "cashier", "warehouse", "delivery")
UNITS = ("piece", "carton", "kg")
CUSTOMER_TYPES = ("retail", "wholesale", "credit")
MOVEMENT_TYPES = ("stock_in", "sale", "return", "adjustment", "damage", "void_reversal")
DOC_TYPES = ("estimate", "delivery", "invoice")
DOC_STATUSES = ("open", "converted", "posted", "void")
PAYMENT_METHODS = ("cash", "bkash", "nagad", "bank")


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(30), unique=True)
    label: Mapped[str] = mapped_column(String(60))


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(30))
    password_hash: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

    role: Mapped[Role] = relationship(lazy="joined")

    @property
    def role_name(self) -> str:
        return self.role.name


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    name_bn: Mapped[str | None] = mapped_column(String(200))
    sku: Mapped[str] = mapped_column(String(60), unique=True)
    barcode: Mapped[str | None] = mapped_column(String(80), unique=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    unit: Mapped[str] = mapped_column(String(20), default="piece")
    buy_price_paisa: Mapped[int] = mapped_column(BigInteger, default=0)
    retail_price_paisa: Mapped[int] = mapped_column(BigInteger, default=0)
    wholesale_price_paisa: Mapped[int] = mapped_column(BigInteger, default=0)
    low_stock_milli: Mapped[int] = mapped_column(BigInteger, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

    category: Mapped[Category | None] = relationship(lazy="joined")


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    phone: Mapped[str | None] = mapped_column(String(30), index=True)
    address: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(20), default="retail")
    credit_limit_paisa: Mapped[int] = mapped_column(BigInteger, default=0)
    opening_balance_paisa: Mapped[int] = mapped_column(BigInteger, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class Document(Base):
    """Estimate / Delivery Challan / Invoice in one table."""
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("doc_type", "number", name="uq_documents_type_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doc_type: Mapped[str] = mapped_column(String(20), index=True)
    number: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), index=True)
    customer_name: Mapped[str] = mapped_column(String(200), default="Walk-in customer")
    customer_phone: Mapped[str | None] = mapped_column(String(30))
    customer_address: Mapped[str | None] = mapped_column(Text)
    price_tier: Mapped[str] = mapped_column(String(20), default="retail")
    subtotal_paisa: Mapped[int] = mapped_column(BigInteger, default=0)
    discount_paisa: Mapped[int] = mapped_column(BigInteger, default=0)
    total_paisa: Mapped[int] = mapped_column(BigInteger, default=0)
    # Cached from the payments table (kept in the same transaction); invoices only.
    paid_paisa: Mapped[int] = mapped_column(BigInteger, default=0)
    payment_status: Mapped[str | None] = mapped_column(String(20), index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"))
    # True when THIS document wrote stock movements (invoice made from a challan does not).
    moves_stock: Mapped[bool] = mapped_column(Boolean, default=False)
    assigned_to_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    verify_token: Mapped[str] = mapped_column(String(64), unique=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime)
    voided_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    void_reason: Mapped[str | None] = mapped_column(Text)

    items: Mapped[list["DocumentItem"]] = relationship(
        back_populates="document", order_by="DocumentItem.line_no", cascade="all, delete-orphan")
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id], lazy="joined")
    voided_by: Mapped[User | None] = relationship(foreign_keys=[voided_by_id])
    assigned_to: Mapped[User | None] = relationship(foreign_keys=[assigned_to_id])
    approved_by: Mapped[User | None] = relationship(foreign_keys=[approved_by_id])
    customer: Mapped[Customer | None] = relationship()
    parent: Mapped["Document | None"] = relationship(remote_side=[id])

    @property
    def due_paisa(self) -> int:
        if self.doc_type != "invoice" or self.status == "void":
            return 0
        return max(self.total_paisa - self.paid_paisa, 0)


class DocumentItem(Base):
    __tablename__ = "document_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    line_no: Mapped[int] = mapped_column(Integer)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    description: Mapped[str] = mapped_column(String(255))
    unit: Mapped[str] = mapped_column(String(20))
    qty_milli: Mapped[int] = mapped_column(BigInteger)
    unit_price_paisa: Mapped[int] = mapped_column(BigInteger)
    discount_paisa: Mapped[int] = mapped_column(BigInteger, default=0)
    line_total_paisa: Mapped[int] = mapped_column(BigInteger)
    # Cost snapshot at sale time, for the Phase 3 profit report.
    buy_price_paisa: Mapped[int] = mapped_column(BigInteger, default=0)

    document: Mapped[Document] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()


class StockMovement(Base):
    """The stock ledger. Rows are never updated or deleted."""
    __tablename__ = "stock_movements"
    __table_args__ = (Index("ix_stock_movements_product_created", "product_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    qty_milli: Mapped[int] = mapped_column(BigInteger)  # signed: + in, - out
    type: Mapped[str] = mapped_column(String(20))
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), index=True)
    reversal_of_id: Mapped[int | None] = mapped_column(ForeignKey("stock_movements.id"))
    reference: Mapped[str | None] = mapped_column(String(120))  # e.g. supplier memo no.
    reason: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    product: Mapped[Product] = relationship()
    user: Mapped[User] = relationship()
    document: Mapped[Document | None] = relationship()


class Payment(Base):
    """Money received. Rows are never updated or deleted; a reversal is a negative row."""
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), index=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), index=True)
    amount_paisa: Mapped[int] = mapped_column(BigInteger)
    method: Mapped[str] = mapped_column(String(20))
    reference: Mapped[str | None] = mapped_column(String(120))  # bKash/Nagad TrxID, cheque no.
    note: Mapped[str | None] = mapped_column(Text)
    paid_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)
    reversal_of_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

    user: Mapped[User] = relationship()
    document: Mapped[Document | None] = relationship()


class Installment(Base):
    """Schedule rows. Paid/unpaid is derived by allocating the invoice's paid amount in order."""
    __tablename__ = "installments"
    __table_args__ = (UniqueConstraint("document_id", "seq", name="uq_installments_doc_seq"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    due_date: Mapped[date] = mapped_column(Date)
    amount_paisa: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_entity", "entity", "entity_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(40))
    field: Mapped[str | None] = mapped_column(String(60))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User | None] = relationship()


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
