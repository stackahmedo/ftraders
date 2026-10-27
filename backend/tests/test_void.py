import pytest
from sqlalchemy import select

from app.errors import BusinessError
from app.models import AuditLog, Payment, StockMovement
from app.money import qty_to_milli
from app.services import documents as doc_svc
from app.services import payments as pay
from app.services import stock

from .helpers import T, make


def _rows(db, model, **filters):
    return db.scalars(select(model).filter_by(**filters).order_by(model.id)).all()


def test_void_invoice_reverses_stock_and_payments_with_new_rows(db, users, product, wholesale):
    inv = make(db, users["cashier"], product, customer=wholesale, qty="4", pay="200")
    pay.record_payment(db, users["cashier"], amount_paisa=T("60"), method="bkash", document=inv)
    db.commit()
    before_moves = [(m.id, m.qty_milli) for m in _rows(db, StockMovement, document_id=inv.id)]
    before_pays = [(p.id, p.amount_paisa) for p in _rows(db, Payment, document_id=inv.id)]
    assert stock.stock_of(db, product.id) == qty_to_milli("6")

    doc_svc.void(db, users["manager"], inv, "Wrong customer")
    db.commit()

    moves = _rows(db, StockMovement, document_id=inv.id)
    pays = _rows(db, Payment, document_id=inv.id)
    # Old rows are unchanged, new opposite rows were added.
    assert [(m.id, m.qty_milli) for m in moves[:len(before_moves)]] == before_moves
    assert [(p.id, p.amount_paisa) for p in pays[:len(before_pays)]] == before_pays
    assert [m.type for m in moves] == ["sale", "void_reversal"]
    assert sum(p.amount_paisa for p in pays) == 0 and len(pays) == 4
    assert stock.stock_of(db, product.id) == qty_to_milli("10")
    assert inv.status == "void" and inv.void_reason == "Wrong customer"
    assert inv.voided_by_id == users["manager"].id and inv.voided_at is not None
    assert inv.paid_paisa == 0 and inv.due_paisa == 0
    assert pay.customer_balance(db, wholesale.id) == 0
    assert db.scalar(select(AuditLog).where(AuditLog.entity == "document", AuditLog.action == "void"))


def test_void_needs_reason_and_only_once(db, users, product, retail):
    inv = make(db, users["cashier"], product, customer=retail, qty="1", pay="100")
    with pytest.raises(BusinessError):
        doc_svc.void(db, users["manager"], inv, "  ")
    doc_svc.void(db, users["manager"], inv, "Test sale")
    db.commit()
    with pytest.raises(BusinessError):
        doc_svc.void(db, users["manager"], inv, "again")


def test_void_chain_challan_then_invoice(db, users, product, wholesale):
    dlv = make(db, users["manager"], product, customer=wholesale, qty="5", doc_type="delivery")
    inv = doc_svc.convert(db, users["manager"], dlv, "invoice", payment=doc_svc.PaymentIn(T("100"), "cash"))
    db.commit()
    assert stock.stock_of(db, product.id) == qty_to_milli("5")

    with pytest.raises(BusinessError) as e:
        doc_svc.void(db, users["manager"], dlv, "cancel")
    assert e.value.code == "has_children"

    doc_svc.void(db, users["manager"], inv, "Price error")
    db.commit()
    # Goods left with the challan, so voiding the invoice keeps stock out and reopens the challan.
    assert stock.stock_of(db, product.id) == qty_to_milli("5")
    assert dlv.status == "open"
    assert sum(p.amount_paisa for p in _rows(db, Payment, document_id=inv.id)) == 0

    # Re-invoice works, then voiding everything brings stock back.
    inv2 = doc_svc.convert(db, users["manager"], dlv, "invoice")
    db.commit()
    assert inv2.number == "INV-0002"
    doc_svc.void(db, users["manager"], inv2, "Customer returned goods")
    doc_svc.void(db, users["manager"], dlv, "Customer returned goods")
    db.commit()
    assert stock.stock_of(db, product.id) == qty_to_milli("10")


def test_void_estimate_has_nothing_to_reverse(db, users, product, retail):
    est = make(db, users["cashier"], product, customer=retail, qty="2", doc_type="estimate")
    doc_svc.void(db, users["manager"], est, "Customer declined")
    db.commit()
    assert _rows(db, StockMovement, document_id=est.id) == []
    assert est.status == "void"
