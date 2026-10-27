"""Payments, customer balance / ledger, installments, due list."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..errors import BusinessError, NotFound
from ..models import PAYMENT_METHODS, Customer, Document, Installment, Payment, User
from ..money import fmt_taka, payment_status, split_installments
from . import audit


# ------------------------------------------------------------------ invoice totals
def paid_for_document(db: Session, document_id: int) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(Payment.amount_paisa), 0))
                         .where(Payment.document_id == document_id)))


def has_plan(db: Session, document_id: int) -> bool:
    return db.scalar(select(func.count(Installment.id)).where(Installment.document_id == document_id)) > 0


def refresh_document(db: Session, doc: Document) -> None:
    """Recompute the cached paid amount / status from the payments table."""
    db.flush()
    doc.paid_paisa = paid_for_document(db, doc.id)
    if doc.doc_type == "invoice" and doc.status != "void":
        doc.payment_status = payment_status(doc.total_paisa, doc.paid_paisa, has_plan(db, doc.id))
    db.flush()


# ------------------------------------------------------------------ record / reverse
def record_payment(db: Session, user: User, *, amount_paisa: int, method: str,
                   document: Document | None = None, customer: Customer | None = None,
                   reference: str | None = None, note: str | None = None,
                   paid_at: datetime | None = None) -> Payment:
    if amount_paisa <= 0:
        raise BusinessError("Payment amount must be greater than zero")
    if method not in PAYMENT_METHODS:
        raise BusinessError(f"Payment method must be one of: {', '.join(PAYMENT_METHODS)}")
    if document is not None:
        if document.doc_type != "invoice":
            raise BusinessError("Payments can only be taken on invoices")
        if document.status == "void":
            raise BusinessError("This invoice is void")
        refresh_document(db, document)
        if amount_paisa > document.due_paisa:
            raise BusinessError(f"Amount is more than the due ({fmt_taka(document.due_paisa)})",
                                code="overpayment")
        customer_id = document.customer_id
    else:
        if customer is None:
            raise BusinessError("Choose an invoice or a customer for this payment")
        customer_id = customer.id
    p = Payment(customer_id=customer_id, document_id=document.id if document else None,
                amount_paisa=amount_paisa, method=method, reference=reference, note=note,
                user_id=user.id, **({"paid_at": paid_at} if paid_at else {}))
    db.add(p)
    db.flush()
    audit.log(db, user, "payment", p.id, "create", "amount", None, fmt_taka(amount_paisa),
              f"{method} {document.number if document else 'on account'}")
    if document is not None:
        refresh_document(db, document)
    return p


def reverse_payment(db: Session, user: User, payment: Payment, reason: str) -> Payment:
    reason = (reason or "").strip()
    if not reason:
        raise BusinessError("A reason is required to reverse a payment", code="reason_required")
    if payment.amount_paisa <= 0 or payment.reversal_of_id:
        raise BusinessError("Only an original payment can be reversed")
    already = db.scalar(select(Payment.id).where(Payment.reversal_of_id == payment.id))
    if already:
        raise BusinessError("This payment is already reversed")
    r = Payment(customer_id=payment.customer_id, document_id=payment.document_id,
                amount_paisa=-payment.amount_paisa, method=payment.method,
                reference=payment.reference, note=reason, reversal_of_id=payment.id, user_id=user.id)
    db.add(r)
    db.flush()
    audit.log(db, user, "payment", payment.id, "reverse", "amount",
              fmt_taka(payment.amount_paisa), fmt_taka(0), reason)
    if payment.document_id:
        doc = db.get(Document, payment.document_id)
        refresh_document(db, doc)
    return r


def reverse_document_payments(db: Session, user: User, doc: Document, reason: str) -> int:
    payments = db.scalars(select(Payment).where(Payment.document_id == doc.id)).all()
    reversed_ids = {p.reversal_of_id for p in payments if p.reversal_of_id}
    count = 0
    for p in payments:
        if p.amount_paisa > 0 and not p.reversal_of_id and p.id not in reversed_ids:
            reverse_payment(db, user, p, reason)
            count += 1
    return count


# ------------------------------------------------------------------ customer balance
def customer_balance(db: Session, customer_id: int) -> int:
    """Opening balance + live invoices - all payments (reversals are negative rows)."""
    c = db.get(Customer, customer_id)
    if not c:
        raise NotFound("Customer")
    invoiced = db.scalar(select(func.coalesce(func.sum(Document.total_paisa), 0)).where(
        Document.customer_id == customer_id, Document.doc_type == "invoice", Document.status != "void"))
    paid = db.scalar(select(func.coalesce(func.sum(Payment.amount_paisa), 0))
                     .where(Payment.customer_id == customer_id))
    return int(c.opening_balance_paisa) + int(invoiced) - int(paid)


def balances_for(db: Session, customer_ids: list[int]) -> dict[int, int]:
    if not customer_ids:
        return {}
    opening = dict(db.execute(select(Customer.id, Customer.opening_balance_paisa)
                              .where(Customer.id.in_(customer_ids))).all())
    invoiced = dict(db.execute(
        select(Document.customer_id, func.sum(Document.total_paisa))
        .where(Document.customer_id.in_(customer_ids), Document.doc_type == "invoice", Document.status != "void")
        .group_by(Document.customer_id)).all())
    paid = dict(db.execute(
        select(Payment.customer_id, func.sum(Payment.amount_paisa))
        .where(Payment.customer_id.in_(customer_ids)).group_by(Payment.customer_id)).all())
    return {cid: int(opening.get(cid) or 0) + int(invoiced.get(cid) or 0) - int(paid.get(cid) or 0)
            for cid in customer_ids}


def customer_ledger(db: Session, customer_id: int) -> dict:
    c = db.get(Customer, customer_id)
    if not c:
        raise NotFound("Customer")
    entries: list[dict] = []
    invoices = db.scalars(select(Document).where(Document.customer_id == customer_id,
                                                 Document.doc_type == "invoice")).all()
    for d in invoices:
        entries.append({"at": d.created_at, "kind": "invoice", "ref": d.number, "document_id": d.id,
                        "debit_paisa": d.total_paisa, "credit_paisa": 0, "note": None})
        if d.status == "void" and d.voided_at:
            entries.append({"at": d.voided_at, "kind": "invoice_void", "ref": d.number, "document_id": d.id,
                            "debit_paisa": 0, "credit_paisa": d.total_paisa, "note": d.void_reason})
    for p in db.scalars(select(Payment).where(Payment.customer_id == customer_id)).all():
        doc_number = p.document.number if p.document else None
        if p.amount_paisa >= 0:
            entries.append({"at": p.paid_at, "kind": "payment", "ref": doc_number, "document_id": p.document_id,
                            "debit_paisa": 0, "credit_paisa": p.amount_paisa,
                            "note": f"{p.method}{' ' + p.reference if p.reference else ''}"})
        else:
            entries.append({"at": p.paid_at, "kind": "payment_reversal", "ref": doc_number,
                            "document_id": p.document_id, "debit_paisa": -p.amount_paisa,
                            "credit_paisa": 0, "note": p.note})
    entries.sort(key=lambda e: (e["at"], 0 if e["kind"] == "invoice" else 1))
    running = c.opening_balance_paisa
    for e in entries:
        running += e["debit_paisa"] - e["credit_paisa"]
        e["balance_paisa"] = running
    return {"customer_id": c.id, "opening_balance_paisa": c.opening_balance_paisa,
            "balance_paisa": running, "entries": entries}


# ------------------------------------------------------------------ installments
def set_installment_plan(db: Session, user: User, doc: Document, *, count: int | None = None,
                         first_due: date | None = None, interval_days: int = 30,
                         schedule: list[tuple[date, int]] | None = None) -> list[Installment]:
    """Create (or replace) the schedule. It must add up to the invoice's current due."""
    if doc.doc_type != "invoice" or doc.status == "void":
        raise BusinessError("Installments can only be set on a live invoice")
    refresh_document(db, doc)
    due = doc.due_paisa
    if due <= 0:
        raise BusinessError("This invoice has nothing due")
    if schedule is None:
        if not count or not first_due:
            raise BusinessError("Give an installment count and first due date, or a full schedule")
        parts = split_installments(due, count)
        schedule = [(first_due + timedelta(days=interval_days * i), amt) for i, amt in enumerate(parts)]
    if any(amount <= 0 for _, amount in schedule):
        raise BusinessError("Every installment must be greater than zero")
    if sum(a for _, a in schedule) != due:
        raise BusinessError(f"Installments must add up to the due amount {fmt_taka(due)}")
    old = db.scalars(select(Installment).where(Installment.document_id == doc.id)).all()
    if old:
        audit.log(db, user, "installment_plan", doc.id, "replace", "schedule",
                  "; ".join(f"{i.due_date}:{fmt_taka(i.amount_paisa)}" for i in old), None)
        for i in old:
            db.delete(i)  # a schedule is a plan, not a financial record; the change is audited
        db.flush()
    rows = [Installment(document_id=doc.id, seq=n + 1, due_date=d, amount_paisa=a)
            for n, (d, a) in enumerate(sorted(schedule))]
    db.add_all(rows)
    audit.log(db, user, "installment_plan", doc.id, "create", "schedule", None,
              "; ".join(f"{r.due_date}:{fmt_taka(r.amount_paisa)}" for r in rows))
    refresh_document(db, doc)
    return rows


def installment_view(db: Session, doc: Document, today: date) -> list[dict]:
    """Paid/unpaid mark per installment.

    Payments made after the plan are allocated to installments in order of due date.
    `covered` = everything paid beyond what had been paid when the plan was made
    (plan total = due at that moment, so pre-plan paid = total - plan total).
    """
    rows = db.scalars(select(Installment).where(Installment.document_id == doc.id)
                      .order_by(Installment.seq)).all()
    if not rows:
        return []
    plan_total = sum(r.amount_paisa for r in rows)
    covered = max(doc.paid_paisa - (doc.total_paisa - plan_total), 0) if doc.status != "void" else 0
    out = []
    for r in rows:
        applied = min(covered, r.amount_paisa)
        covered -= applied
        paid = applied >= r.amount_paisa
        out.append({"id": r.id, "seq": r.seq, "due_date": r.due_date, "amount_paisa": r.amount_paisa,
                    "paid_paisa": applied, "is_paid": paid,
                    "is_overdue": (not paid) and r.due_date < today})
    return out


# ------------------------------------------------------------------ due list
def due_invoices(db: Session) -> list[Document]:
    return db.scalars(select(Document).where(
        Document.doc_type == "invoice", Document.status != "void",
        Document.total_paisa > Document.paid_paisa).order_by(Document.created_at)).all()
