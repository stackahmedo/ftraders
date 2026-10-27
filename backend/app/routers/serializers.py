"""Model -> response dict helpers shared by routers."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import schemas
from ..models import Document, Payment, Product, StockMovement, User
from ..security import ROLE_PERMISSIONS
from ..services import payments as pay_svc
from ..timeutil import local_today


def user_out(u: User) -> schemas.UserOut:
    return schemas.UserOut(id=u.id, username=u.username, full_name=u.full_name, phone=u.phone,
                           role_name=u.role_name, is_active=u.is_active,
                           permissions=sorted(ROLE_PERMISSIONS.get(u.role_name, set())))


def product_out(p: Product, stock_milli: int = 0) -> schemas.ProductOut:
    out = schemas.ProductOut.model_validate(p)
    out.category_name = p.category.name if p.category else None
    out.stock_milli = stock_milli
    return out


def movement_out(m: StockMovement) -> schemas.MovementOut:
    out = schemas.MovementOut.model_validate(m)
    out.product_name = m.product.name
    out.unit = m.product.unit
    out.user_name = m.user.full_name
    out.document_number = m.document.number if m.document else None
    return out


def payment_out(p: Payment, reversed_ids: set[int] | None = None) -> schemas.PaymentOut:
    out = schemas.PaymentOut.model_validate(p)
    out.user_name = p.user.full_name
    out.document_number = p.document.number if p.document else None
    out.is_reversed = bool(reversed_ids and p.id in reversed_ids)
    return out


def doc_summary(d: Document) -> schemas.DocumentSummary:
    out = schemas.DocumentSummary.model_validate(d)
    out.created_by_name = d.created_by.full_name
    return out


def doc_out(db: Session, d: Document) -> schemas.DocumentOut:
    out = schemas.DocumentOut.model_validate(d)
    out.created_by_name = d.created_by.full_name
    out.parent_number = d.parent.number if d.parent else None
    out.children = [{"id": c.id, "number": c.number, "doc_type": c.doc_type, "status": c.status}
                    for c in db.scalars(select(Document).where(Document.parent_id == d.id))]
    out.assigned_to_name = d.assigned_to.full_name if d.assigned_to else None
    out.approved_by_name = d.approved_by.full_name if d.approved_by else None
    out.voided_by_name = d.voided_by.full_name if d.voided_by else None
    pays = db.scalars(select(Payment).where(Payment.document_id == d.id).order_by(Payment.paid_at, Payment.id)).all()
    reversed_ids = {p.reversal_of_id for p in pays if p.reversal_of_id}
    out.payments = [payment_out(p, reversed_ids) for p in pays]
    out.installments = [schemas.InstallmentOut(**row) for row in pay_svc.installment_view(db, d, local_today())]
    return out
