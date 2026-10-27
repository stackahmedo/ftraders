from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import schemas
from ..db import get_db
from ..errors import NotFound
from ..models import Document, User
from ..money import qty_to_milli
from ..pdf import render_document_pdf
from ..security import get_current_user, has_perm, require, verify_approver
from ..services import documents as doc_svc
from ..services import payments as pay_svc
from ..services import settings as settings_svc
from ..timeutil import day_bounds_utc
from .serializers import doc_out, doc_summary

router = APIRouter(prefix="/api", tags=["documents"])


def _readable(user: User, doc: Document) -> bool:
    if has_perm(user, "docs.read"):
        return True
    # Delivery staff see only the challans assigned to them.
    return (has_perm(user, "docs.read_own") and doc.doc_type == "delivery"
            and doc.assigned_to_id == user.id)


def _load(db: Session, user: User, doc_id: int) -> Document:
    doc = db.get(Document, doc_id)
    if not doc or not _readable(user, doc):
        raise NotFound("Document")
    return doc


def _approvals(db: Session, discount: schemas.ApprovalIn | None, credit: schemas.ApprovalIn | None):
    a = doc_svc.Approvals()
    if discount:
        a.discount = verify_approver(db, discount.username, discount.password, "approve.discount")
    if credit:
        a.credit = verify_approver(db, credit.username, credit.password, "approve.credit")
    return a


def _payment(p: schemas.PaymentIn | None) -> doc_svc.PaymentIn | None:
    if p is None or p.amount_paisa == 0:
        return None
    return doc_svc.PaymentIn(amount_paisa=p.amount_paisa, method=p.method, reference=p.reference)


@router.get("/documents", response_model=list[schemas.DocumentSummary])
def list_documents(type: str | None = None, status: str | None = None, payment_status: str | None = None,
                   customer_id: int | None = None, q: str | None = None,
                   date_from: date | None = None, date_to: date | None = None, limit: int = 200,
                   db: Session = Depends(get_db), user: User = Depends(require("docs.read", "docs.read_own"))):
    query = select(Document).order_by(Document.created_at.desc(), Document.id.desc()).limit(min(limit, 2000))
    if not has_perm(user, "docs.read"):
        query = query.where(Document.doc_type == "delivery", Document.assigned_to_id == user.id)
    if type:
        query = query.where(Document.doc_type == type)
    if status:
        query = query.where(Document.status == status)
    if payment_status:
        query = query.where(Document.payment_status == payment_status, Document.status != "void")
    if customer_id:
        query = query.where(Document.customer_id == customer_id)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(or_(Document.number.ilike(like), Document.customer_name.ilike(like),
                                Document.customer_phone.ilike(like)))
    if date_from:
        query = query.where(Document.created_at >= day_bounds_utc(date_from)[0])
    if date_to:
        query = query.where(Document.created_at < day_bounds_utc(date_to)[1])
    return [doc_summary(d) for d in db.scalars(query)]


@router.get("/documents/{doc_id}", response_model=schemas.DocumentOut)
def get_document(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return doc_out(db, _load(db, user, doc_id))


@router.post("/documents", response_model=schemas.DocumentOut, status_code=201)
def create_document(body: schemas.DocumentCreate, db: Session = Depends(get_db),
                    user: User = Depends(require("docs.write"))):
    approvals = _approvals(db, body.discount_approval, body.credit_approval)
    lines = [doc_svc.LineIn(product_id=i.product_id, qty_milli=qty_to_milli(i.qty),
                            discount_paisa=i.discount_paisa) for i in body.items]
    doc = doc_svc.create_document(db, user, doc_type=body.doc_type, customer_id=body.customer_id, lines=lines,
                                  notes=body.notes, payment=_payment(body.payment), approvals=approvals,
                                  assigned_to_id=body.assigned_to_id)
    db.commit()
    return doc_out(db, doc)


@router.post("/documents/{doc_id}/convert", response_model=schemas.DocumentOut, status_code=201)
def convert_document(doc_id: int, body: schemas.ConvertIn, db: Session = Depends(get_db),
                     user: User = Depends(require("docs.write"))):
    source = _load(db, user, doc_id)
    child = doc_svc.convert(db, user, source, body.target_type, payment=_payment(body.payment),
                            approvals=_approvals(db, None, body.credit_approval),
                            assigned_to_id=body.assigned_to_id)
    db.commit()
    return doc_out(db, child)


@router.post("/documents/{doc_id}/void", response_model=schemas.DocumentOut)
def void_document(doc_id: int, body: schemas.VoidIn, db: Session = Depends(get_db),
                  user: User = Depends(require("docs.void"))):
    doc = _load(db, user, doc_id)
    doc_svc.void(db, user, doc, body.reason)
    db.commit()
    return doc_out(db, doc)


@router.post("/documents/{doc_id}/installments", response_model=schemas.DocumentOut)
def set_installments(doc_id: int, body: schemas.InstallmentPlanIn, db: Session = Depends(get_db),
                     user: User = Depends(require("payments.write"))):
    doc = _load(db, user, doc_id)
    pay_svc.set_installment_plan(db, user, doc, count=body.count, first_due=body.first_due,
                                 interval_days=body.interval_days, schedule=body.schedule)
    db.commit()
    return doc_out(db, doc)


@router.get("/documents/{doc_id}/pdf")
def document_pdf(doc_id: int, layout: str = "a4", db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    if layout not in ("a4", "thermal"):
        raise HTTPException(400, "layout must be a4 or thermal")
    doc = _load(db, user, doc_id)
    pdf = render_document_pdf(doc, settings_svc.get_all(db), layout)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{doc.number}-{layout}.pdf"'})


@router.get("/public/verify/{token}", response_model=schemas.VerifyOut)
def verify(token: str, db: Session = Depends(get_db)):
    """Opened from the QR code on a printed document. No login; shows only summary facts."""
    doc = db.scalar(select(Document).where(Document.verify_token == token))
    if not doc:
        raise NotFound("Document")
    return schemas.VerifyOut(business_name=settings_svc.get(db, "business_name"), doc_type=doc.doc_type,
                             number=doc.number, status=doc.status, customer_name=doc.customer_name,
                             total_paisa=doc.total_paisa, paid_paisa=doc.paid_paisa, due_paisa=doc.due_paisa,
                             created_at=doc.created_at, created_by_name=doc.created_by.full_name)
