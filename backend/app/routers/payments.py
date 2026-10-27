from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import schemas
from ..db import get_db
from ..errors import NotFound
from ..models import Customer, Document, Payment, User
from ..security import has_perm, require
from ..services import payments as pay_svc
from ..services import stock as stock_svc
from ..timeutil import day_bounds_utc, local_today
from .serializers import doc_summary, payment_out

router = APIRouter(prefix="/api", tags=["payments"])


@router.get("/payments", response_model=list[schemas.PaymentOut])
def list_payments(customer_id: int | None = None, document_id: int | None = None,
                  date_from: date | None = None, date_to: date | None = None, limit: int = 200,
                  db: Session = Depends(get_db), _: User = Depends(require("payments.read"))):
    q = select(Payment).order_by(Payment.paid_at.desc(), Payment.id.desc()).limit(min(limit, 2000))
    if customer_id:
        q = q.where(Payment.customer_id == customer_id)
    if document_id:
        q = q.where(Payment.document_id == document_id)
    if date_from:
        q = q.where(Payment.paid_at >= day_bounds_utc(date_from)[0])
    if date_to:
        q = q.where(Payment.paid_at < day_bounds_utc(date_to)[1])
    rows = db.scalars(q).all()
    reversed_ids = set(db.scalars(select(Payment.reversal_of_id).where(
        Payment.reversal_of_id.in_([p.id for p in rows]))))
    return [payment_out(p, reversed_ids) for p in rows]


@router.post("/payments", response_model=schemas.PaymentOut, status_code=201)
def create_payment(body: schemas.PaymentCreate, db: Session = Depends(get_db),
                   user: User = Depends(require("payments.write"))):
    doc = customer = None
    if body.document_id:
        doc = db.get(Document, body.document_id)
        if not doc:
            raise NotFound("Invoice")
    elif body.customer_id:
        customer = db.get(Customer, body.customer_id)
        if not customer:
            raise NotFound("Customer")
    p = pay_svc.record_payment(db, user, amount_paisa=body.amount_paisa, method=body.method,
                               document=doc, customer=customer, reference=body.reference, note=body.note)
    db.commit()
    return payment_out(p)


@router.post("/payments/{payment_id}/reverse", response_model=schemas.PaymentOut)
def reverse(payment_id: int, body: schemas.ReverseIn, db: Session = Depends(get_db),
            user: User = Depends(require("payments.reverse"))):
    p = db.get(Payment, payment_id)
    if not p:
        raise NotFound("Payment")
    r = pay_svc.reverse_payment(db, user, p, body.reason)
    db.commit()
    return payment_out(r)


@router.get("/dues")
def due_list(db: Session = Depends(get_db), _: User = Depends(require("payments.read"))):
    """Due list: unpaid invoices (with next installment) and customer balances."""
    today = local_today()
    invoices = []
    for d in pay_svc.due_invoices(db):
        plan = pay_svc.installment_view(db, d, today)
        nxt = next((i for i in plan if not i["is_paid"]), None)
        row = doc_summary(d).model_dump(mode="json")
        row["days_old"] = (today - d.created_at.date()).days
        row["next_installment"] = (
            {"due_date": nxt["due_date"].isoformat(), "amount_paisa": nxt["amount_paisa"] - nxt["paid_paisa"],
             "is_overdue": nxt["is_overdue"]} if nxt else None)
        invoices.append(row)
    customers = db.scalars(select(Customer)).all()
    balances = pay_svc.balances_for(db, [c.id for c in customers])
    by_customer = sorted(
        ({"customer_id": c.id, "name": c.name, "phone": c.phone, "type": c.type,
          "credit_limit_paisa": c.credit_limit_paisa, "balance_paisa": balances[c.id]}
         for c in customers if balances.get(c.id, 0) > 0),
        key=lambda r: -r["balance_paisa"])
    return {"invoices": invoices, "customers": by_customer,
            "total_due_paisa": sum(r["balance_paisa"] for r in by_customer)}


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(require("dashboard.read"))):
    start, end = day_bounds_utc(local_today())
    out: dict = {"low_stock": stock_svc.low_stock(db)}
    if has_perm(user, "docs.read"):
        sales = db.execute(select(func.count(Document.id), func.coalesce(func.sum(Document.total_paisa), 0))
                           .where(Document.doc_type == "invoice", Document.status != "void",
                                  Document.created_at >= start, Document.created_at < end)).one()
        collected = db.scalar(select(func.coalesce(func.sum(Payment.amount_paisa), 0))
                              .where(Payment.paid_at >= start, Payment.paid_at < end))
        # "Due collected" = money received today against older invoices or on account,
        # i.e. not the payment taken at the counter for an invoice made today.
        todays_invoice_ids = select(Document.id).where(Document.doc_type == "invoice",
                                                       Document.created_at >= start, Document.created_at < end)
        due_collected = db.scalar(select(func.coalesce(func.sum(Payment.amount_paisa), 0)).where(
            Payment.paid_at >= start, Payment.paid_at < end,
            (Payment.document_id.is_(None)) | (Payment.document_id.not_in(todays_invoice_ids))))
        total_due = sum(v for v in pay_svc.balances_for(db, list(db.scalars(select(Customer.id)))).values() if v > 0)
        out.update({"sales_count": sales[0], "sales_paisa": int(sales[1]), "collected_paisa": int(collected),
                    "due_collected_paisa": int(due_collected), "total_due_paisa": int(total_due),
                    "recent": [doc_summary(d).model_dump(mode="json") for d in db.scalars(
                        select(Document).order_by(Document.created_at.desc()).limit(8))]})
    return out
