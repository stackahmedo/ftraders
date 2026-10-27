from app.money import qty_to_milli, taka_to_paisa
from app.services import documents as doc_svc


def T(amount: str) -> int:
    """Taka string -> paisa."""
    return taka_to_paisa(amount)


def make(db, user, product, *, customer=None, qty="1", doc_type="invoice", pay=None, method="cash",
         discount="0", approvals=None, assigned_to_id=None):
    payment = doc_svc.PaymentIn(T(pay), method) if pay is not None else None
    doc = doc_svc.create_document(
        db, user, doc_type=doc_type, customer_id=customer.id if customer else None,
        lines=[doc_svc.LineIn(product.id, qty_to_milli(qty), T(discount))],
        payment=payment, approvals=approvals, assigned_to_id=assigned_to_id)
    db.commit()
    return doc
