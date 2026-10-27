"""Estimates, delivery challans and invoices: create, convert, void."""
from __future__ import annotations

import secrets
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import ApprovalRequired, BusinessError, NotFound
from ..models import DOC_TYPES, Customer, Document, DocumentItem, Product, User, now_utc
from ..money import discount_needs_approval, fmt_taka, line_amounts
from ..security import has_perm
from . import audit, payments, settings, stock

# What each type does to stock and money.
MOVES_STOCK = {"estimate": False, "delivery": True, "invoice": True}
CONVERSIONS = {("estimate", "delivery"), ("estimate", "invoice"), ("delivery", "invoice")}


@dataclass
class LineIn:
    product_id: int
    qty_milli: int
    discount_paisa: int = 0
    unit_price_paisa: int | None = None  # only used when copying lines on conversion


@dataclass
class PaymentIn:
    amount_paisa: int
    method: str = "cash"
    reference: str | None = None


@dataclass
class Approvals:
    """Supervisor(s) who approved this action at the counter (already password-checked)."""
    discount: User | None = None
    credit: User | None = None
    used: list[User] = field(default_factory=list)


def price_tier_for(customer: Customer | None) -> str:
    return "wholesale" if customer is not None and customer.type == "wholesale" else "retail"


def build_items(db: Session, lines: list[LineIn], tier: str) -> tuple[list[DocumentItem], int, int, int]:
    if not lines:
        raise BusinessError("Add at least one item")
    items, subtotal, discount = [], 0, 0
    for n, line in enumerate(lines, start=1):
        p = db.get(Product, line.product_id)
        if not p or not p.is_active:
            raise NotFound(f"Product {line.product_id}")
        if line.unit_price_paisa is not None:
            unit_price = line.unit_price_paisa
        else:
            # The customer type picks the tier; wholesale price only for wholesale buyers.
            unit_price = p.wholesale_price_paisa if tier == "wholesale" else p.retail_price_paisa
        gross, net = line_amounts(unit_price, line.qty_milli, line.discount_paisa)
        subtotal += gross
        discount += line.discount_paisa
        items.append(DocumentItem(line_no=n, product_id=p.id, description=p.name, unit=p.unit,
                                  qty_milli=line.qty_milli, unit_price_paisa=unit_price,
                                  discount_paisa=line.discount_paisa, line_total_paisa=net,
                                  buy_price_paisa=p.buy_price_paisa))
    return items, subtotal, discount, subtotal - discount


def _check_discount(db: Session, user: User, subtotal: int, discount: int, approvals: Approvals) -> User | None:
    limit = settings.get(db, "discount_approval_percent") or "0"
    if not discount_needs_approval(subtotal, discount, limit):
        return None
    if has_perm(user, "approve.discount"):
        return user
    if approvals.discount and has_perm(approvals.discount, "approve.discount"):
        return approvals.discount
    raise ApprovalRequired("discount", f"Discount is above {limit}%. A Manager or Owner must approve.")


def _check_credit(db: Session, user: User, customer: Customer | None, due: int, approvals: Approvals) -> User | None:
    if due <= 0:
        return None
    if customer is None:
        raise BusinessError("A walk-in sale must be paid in full. Choose a customer to sell on credit.",
                            code="walkin_due")
    new_balance = payments.customer_balance(db, customer.id) + due
    if new_balance <= customer.credit_limit_paisa:
        return None
    if has_perm(user, "approve.credit"):
        return user
    if approvals.credit and has_perm(approvals.credit, "approve.credit"):
        return approvals.credit
    raise ApprovalRequired(
        "credit",
        f"Credit limit {fmt_taka(customer.credit_limit_paisa)} would be exceeded "
        f"(balance after sale {fmt_taka(new_balance)}). The Owner must approve.")


def create_document(db: Session, user: User, *, doc_type: str, customer_id: int | None,
                    lines: list[LineIn], notes: str | None = None, payment: PaymentIn | None = None,
                    approvals: Approvals | None = None, assigned_to_id: int | None = None,
                    parent: Document | None = None) -> Document:
    if doc_type not in DOC_TYPES:
        raise BusinessError(f"Unknown document type: {doc_type}")
    approvals = approvals or Approvals()
    customer = None
    if customer_id is not None:
        customer = db.get(Customer, customer_id)
        if not customer or not customer.is_active:
            raise NotFound("Customer")
    tier = parent.price_tier if parent else price_tier_for(customer)
    items, subtotal, discount, total = build_items(db, lines, tier)

    # Discounts already approved on the source document carry over on conversion.
    approver = parent.approved_by if parent and parent.approved_by_id else None
    if approver is None:
        approver = _check_discount(db, user, subtotal, discount, approvals)

    paid_now = payment.amount_paisa if (doc_type == "invoice" and payment) else 0
    if paid_now < 0:
        raise BusinessError("Paid amount cannot be negative")
    if paid_now > total:
        raise BusinessError("Paid amount is more than the invoice total", code="overpayment")
    if doc_type == "invoice":
        credit_approver = _check_credit(db, user, customer, total - paid_now, approvals)
        approver = approver or credit_approver

    doc = Document(
        doc_type=doc_type, number=settings.next_number(db, doc_type),
        status="posted" if doc_type == "invoice" else "open",
        customer_id=customer.id if customer else None,
        customer_name=customer.name if customer else "Walk-in customer",
        customer_phone=customer.phone if customer else None,
        customer_address=customer.address if customer else None,
        price_tier=tier, subtotal_paisa=subtotal, discount_paisa=discount, total_paisa=total,
        notes=notes, parent_id=parent.id if parent else None,
        assigned_to_id=assigned_to_id if doc_type == "delivery" else None,
        approved_by_id=approver.id if approver else None,
        verify_token=secrets.token_urlsafe(16), created_by_id=user.id,
        payment_status="due" if doc_type == "invoice" else None,
    )
    doc.items = items
    db.add(doc)
    db.flush()

    # An invoice made from a delivery challan does not move stock again.
    from_challan = parent is not None and parent.doc_type == "delivery"
    if MOVES_STOCK[doc_type] and not from_challan:
        stock.post_document_out(db, user, doc.id, [(i.product_id, i.qty_milli) for i in items])
        doc.moves_stock = True

    audit.log(db, user, "document", doc.id, "create", None, None,
              f"{doc.number} total {fmt_taka(total)}", None)
    if approver is not None and approver.id != user.id:
        audit.log(db, approver, "document", doc.id, "approve", None, None, doc.number,
                  f"approved for {user.username}")

    if paid_now > 0:
        payments.record_payment(db, user, amount_paisa=paid_now, method=payment.method,
                                reference=payment.reference, document=doc)
    if doc_type == "invoice":
        payments.refresh_document(db, doc)
    return doc


def convert(db: Session, user: User, source: Document, target_type: str, *,
            payment: PaymentIn | None = None, approvals: Approvals | None = None,
            assigned_to_id: int | None = None, notes: str | None = None) -> Document:
    if (source.doc_type, target_type) not in CONVERSIONS:
        raise BusinessError(f"Cannot convert {source.doc_type} to {target_type}")
    if source.status != "open":
        raise BusinessError(f"{source.number} is {source.status}; only open documents can be converted")
    lines = [LineIn(product_id=i.product_id, qty_milli=i.qty_milli, discount_paisa=i.discount_paisa,
                    unit_price_paisa=i.unit_price_paisa) for i in source.items]
    child = create_document(db, user, doc_type=target_type, customer_id=source.customer_id, lines=lines,
                            notes=notes if notes is not None else source.notes, payment=payment,
                            approvals=approvals, assigned_to_id=assigned_to_id, parent=source)
    source.status = "converted"
    audit.log(db, user, "document", source.id, "convert", "status", "open", "converted", child.number)
    db.flush()
    return child


def void(db: Session, user: User, doc: Document, reason: str) -> Document:
    """Void: never deletes. Writes reversal rows for stock and payments."""
    reason = (reason or "").strip()
    if len(reason) < 3:
        raise BusinessError("A reason is required to void a document", code="reason_required")
    if doc.status == "void":
        raise BusinessError("Already void")
    live_children = db.scalars(select(Document).where(Document.parent_id == doc.id,
                                                      Document.status != "void")).all()
    if live_children:
        raise BusinessError(f"Void {live_children[0].number} first; it was made from this document",
                            code="has_children")
    old_status = doc.status
    if doc.moves_stock:
        stock.reverse_document(db, user, doc.id, f"Void {doc.number}: {reason}")
    if doc.doc_type == "invoice":
        payments.reverse_document_payments(db, user, doc, f"Void {doc.number}: {reason}")
    doc.status = "void"
    doc.voided_at = now_utc()
    doc.voided_by_id = user.id
    doc.void_reason = reason
    audit.log(db, user, "document", doc.id, "void", "status", old_status, "void", reason)
    # The source document (if any) becomes open again so it can be re-converted.
    if doc.parent_id:
        parent = db.get(Document, doc.parent_id)
        if parent and parent.status == "converted":
            parent.status = "open"
            audit.log(db, user, "document", parent.id, "reopen", "status", "converted", "open",
                      f"{doc.number} voided")
    db.flush()
    return doc
