"""Request / response models. Money is integer paisa; quantity in requests is a
decimal string (e.g. "2", "1.5") converted to milli-units server side."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator

from .money import MoneyError, qty_to_milli


def _utc_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


UtcDateTime = Annotated[datetime, PlainSerializer(_utc_iso, return_type=str)]
Paisa = Annotated[int, Field(ge=0, le=10**13)]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------------ auth / users
class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(ORM):
    id: int
    username: str
    full_name: str
    phone: str | None = None
    role_name: str
    is_active: bool
    permissions: list[str] = []


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=60)
    full_name: str = Field(min_length=1, max_length=120)
    phone: str | None = None
    password: str = Field(min_length=6)
    role: Literal["owner", "manager", "cashier", "warehouse", "delivery"]


class UserUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    password: str | None = Field(default=None, min_length=6)
    role: Literal["owner", "manager", "cashier", "warehouse", "delivery"] | None = None
    is_active: bool | None = None


# ------------------------------------------------------------------ products
class CategoryOut(ORM):
    id: int
    name: str


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    name_bn: str | None = None
    sku: str = Field(min_length=1, max_length=60)
    barcode: str | None = None
    category: str | None = None  # name; created if new
    unit: Literal["piece", "carton", "kg"] = "piece"
    buy_price_paisa: Paisa = 0
    retail_price_paisa: Paisa = 0
    wholesale_price_paisa: Paisa = 0
    low_stock: str = "0"
    is_active: bool = True

    @field_validator("barcode")
    @classmethod
    def empty_barcode_is_none(cls, v):
        return v.strip() or None if v else None


class ProductOut(ORM):
    id: int
    name: str
    name_bn: str | None
    sku: str
    barcode: str | None
    category_name: str | None = None
    unit: str
    buy_price_paisa: int
    retail_price_paisa: int
    wholesale_price_paisa: int
    low_stock_milli: int
    stock_milli: int = 0
    is_active: bool


# ------------------------------------------------------------------ customers
class CustomerIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str | None = None
    address: str | None = None
    type: Literal["retail", "wholesale", "credit"] = "retail"
    credit_limit_paisa: Paisa = 0
    opening_balance_paisa: int = 0
    notes: str | None = None
    is_active: bool = True


class CustomerOut(ORM):
    id: int
    name: str
    phone: str | None
    address: str | None
    type: str
    credit_limit_paisa: int
    opening_balance_paisa: int
    notes: str | None
    is_active: bool
    balance_paisa: int = 0


class LedgerEntry(BaseModel):
    at: UtcDateTime
    kind: str
    ref: str | None
    document_id: int | None
    debit_paisa: int
    credit_paisa: int
    balance_paisa: int
    note: str | None


class LedgerOut(BaseModel):
    customer: CustomerOut
    opening_balance_paisa: int
    balance_paisa: int
    entries: list[LedgerEntry]


# ------------------------------------------------------------------ stock
class MovementIn(BaseModel):
    product_id: int
    qty: str
    type: Literal["stock_in", "return", "adjustment", "damage"]
    reason: str | None = None
    reference: str | None = None

    @field_validator("qty")
    @classmethod
    def valid_qty(cls, v):
        try:
            qty_to_milli(v)
        except MoneyError as e:
            raise ValueError(str(e))
        return v


class MovementOut(ORM):
    id: int
    created_at: UtcDateTime
    product_id: int
    product_name: str = ""
    unit: str = ""
    qty_milli: int
    type: str
    document_id: int | None
    document_number: str | None = None
    reversal_of_id: int | None
    reference: str | None
    reason: str | None
    user_name: str = ""


class LowStockOut(BaseModel):
    product_id: int
    name: str
    name_bn: str | None
    sku: str
    unit: str
    stock_milli: int
    low_stock_milli: int


# ------------------------------------------------------------------ documents
class LineIn(BaseModel):
    product_id: int
    qty: str
    discount_paisa: Paisa = 0

    @field_validator("qty")
    @classmethod
    def valid_qty(cls, v):
        try:
            if qty_to_milli(v) <= 0:
                raise ValueError("quantity must be greater than zero")
        except MoneyError as e:
            raise ValueError(str(e))
        return v


class PaymentIn(BaseModel):
    amount_paisa: Paisa
    method: Literal["cash", "bkash", "nagad", "bank"] = "cash"
    reference: str | None = None


class ApprovalIn(BaseModel):
    """Supervisor login typed at the counter when a discount/credit needs approval."""
    username: str
    password: str


class DocumentCreate(BaseModel):
    doc_type: Literal["estimate", "delivery", "invoice"]
    customer_id: int | None = None
    items: list[LineIn] = Field(min_length=1)
    notes: str | None = None
    payment: PaymentIn | None = None
    assigned_to_id: int | None = None
    discount_approval: ApprovalIn | None = None
    credit_approval: ApprovalIn | None = None


class ConvertIn(BaseModel):
    target_type: Literal["delivery", "invoice"]
    payment: PaymentIn | None = None
    assigned_to_id: int | None = None
    credit_approval: ApprovalIn | None = None


class VoidIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class ItemOut(ORM):
    id: int
    line_no: int
    product_id: int
    description: str
    unit: str
    qty_milli: int
    unit_price_paisa: int
    discount_paisa: int
    line_total_paisa: int


class PaymentOut(ORM):
    id: int
    customer_id: int | None
    document_id: int | None
    amount_paisa: int
    method: str
    reference: str | None
    note: str | None
    paid_at: UtcDateTime
    reversal_of_id: int | None
    user_name: str = ""
    document_number: str | None = None
    is_reversed: bool = False


class InstallmentOut(BaseModel):
    id: int
    seq: int
    due_date: date
    amount_paisa: int
    paid_paisa: int
    is_paid: bool
    is_overdue: bool


class DocumentSummary(ORM):
    id: int
    doc_type: str
    number: str
    status: str
    customer_id: int | None
    customer_name: str
    customer_phone: str | None
    total_paisa: int
    paid_paisa: int
    due_paisa: int
    payment_status: str | None
    created_at: UtcDateTime
    created_by_name: str = ""


class DocumentOut(DocumentSummary):
    customer_address: str | None
    price_tier: str
    subtotal_paisa: int
    discount_paisa: int
    notes: str | None
    parent_id: int | None
    parent_number: str | None = None
    children: list[dict] = []
    moves_stock: bool
    assigned_to_id: int | None
    assigned_to_name: str | None = None
    approved_by_name: str | None = None
    verify_token: str
    voided_at: UtcDateTime | None
    voided_by_name: str | None = None
    void_reason: str | None
    items: list[ItemOut]
    payments: list[PaymentOut] = []
    installments: list[InstallmentOut] = []


# ------------------------------------------------------------------ payments
class PaymentCreate(BaseModel):
    document_id: int | None = None
    customer_id: int | None = None
    amount_paisa: Paisa
    method: Literal["cash", "bkash", "nagad", "bank"] = "cash"
    reference: str | None = None
    note: str | None = None


class ReverseIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class InstallmentPlanIn(BaseModel):
    count: int | None = Field(default=None, ge=1, le=60)
    first_due: date | None = None
    interval_days: int = Field(default=30, ge=1, le=366)
    schedule: list[tuple[date, int]] | None = None


# ------------------------------------------------------------------ misc
class AuditOut(ORM):
    id: int
    at: UtcDateTime
    user_name: str | None = None
    entity: str
    entity_id: int | None
    action: str
    field: str | None
    old_value: str | None
    new_value: str | None
    reason: str | None


class VerifyOut(BaseModel):
    business_name: str
    doc_type: str
    number: str
    status: str
    customer_name: str
    total_paisa: int
    paid_paisa: int
    due_paisa: int
    created_at: UtcDateTime
    created_by_name: str


TokenOut.model_rebuild()
