import pytest
from sqlalchemy import func, select

from app.errors import BusinessError
from app.models import Document, StockMovement
from app.money import qty_to_milli
from app.services import documents as doc_svc
from app.services import settings, stock

from .helpers import make


def test_stock_is_sum_of_ledger(db, users, product, retail):
    assert stock.stock_of(db, product.id) == qty_to_milli("10")
    make(db, users["cashier"], product, customer=retail, qty="3", pay="300")
    assert stock.stock_of(db, product.id) == qty_to_milli("7")
    rows = db.scalars(select(StockMovement).where(StockMovement.product_id == product.id)).all()
    assert [r.type for r in rows] == ["stock_in", "sale"]
    assert sum(r.qty_milli for r in rows) == qty_to_milli("7")


def test_stock_cannot_go_negative(db, users, product, retail):
    with pytest.raises(BusinessError) as e:
        make(db, users["cashier"], product, customer=retail, qty="11", pay="1100")
    assert e.value.code == "insufficient_stock"
    db.rollback()
    assert stock.stock_of(db, product.id) == qty_to_milli("10")
    assert db.scalar(select(func.count(Document.id))) == 0


def test_owner_can_allow_negative_stock(db, users, product, retail):
    settings.update(db, users["owner"], {"allow_negative_stock": "true"})
    db.commit()
    make(db, users["cashier"], product, customer=retail, qty="11", pay="1100")
    assert stock.stock_of(db, product.id) == qty_to_milli("-1")


def test_estimate_has_no_stock_effect_and_challan_does(db, users, product, wholesale):
    est = make(db, users["manager"], product, customer=wholesale, qty="4", doc_type="estimate")
    assert stock.stock_of(db, product.id) == qty_to_milli("10")
    dlv = doc_svc.convert(db, users["manager"], est, "delivery")
    db.commit()
    assert stock.stock_of(db, product.id) == qty_to_milli("6")
    inv = doc_svc.convert(db, users["manager"], dlv, "invoice")
    db.commit()
    # The invoice made from the challan must not take stock out a second time.
    assert stock.stock_of(db, product.id) == qty_to_milli("6")
    assert not inv.moves_stock and dlv.moves_stock
    assert est.status == "converted" and dlv.status == "converted"
    assert [i.qty_milli for i in inv.items] == [qty_to_milli("4")]
    assert inv.number == "INV-0001" and dlv.number == "DLV-0001" and est.number == "EST-0001"


def test_adjustment_and_damage_need_reason(db, users, product):
    with pytest.raises(BusinessError):
        stock.manual_movement(db, users["warehouse"], product.id, qty_to_milli("-1"), "adjustment", None)
    stock.manual_movement(db, users["warehouse"], product.id, qty_to_milli("-1"), "adjustment", "count fix")
    stock.manual_movement(db, users["warehouse"], product.id, qty_to_milli("2"), "damage", "torn bags")
    db.commit()
    assert stock.stock_of(db, product.id) == qty_to_milli("7")  # damage is always taken out


def test_manual_out_cannot_go_negative(db, users, product):
    with pytest.raises(BusinessError):
        stock.manual_movement(db, users["warehouse"], product.id, qty_to_milli("11"), "damage", "flood")


def test_low_stock_list(db, users, product, retail):
    assert stock.low_stock(db) == []
    make(db, users["cashier"], product, customer=retail, qty="7", pay="700")
    low = stock.low_stock(db)
    assert [r["product_id"] for r in low] == [product.id]
