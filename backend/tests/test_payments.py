from datetime import date

import pytest
from sqlalchemy import select

from app.errors import ApprovalRequired, BusinessError
from app.models import Payment
from app.services import documents as doc_svc
from app.services import payments as pay

from .helpers import T, make


def test_price_tier_follows_customer_type(db, users, product, retail, wholesale, credit):
    assert make(db, users["cashier"], product, customer=retail, pay="100").items[0].unit_price_paisa == T("100")
    assert make(db, users["cashier"], product, customer=wholesale, pay="90").items[0].unit_price_paisa == T("90")
    # Credit customers are not wholesale buyers: retail price.
    assert make(db, users["cashier"], product, customer=credit, pay="100").items[0].unit_price_paisa == T("100")


def test_payment_statuses(db, users, product, wholesale):
    paid = make(db, users["cashier"], product, customer=wholesale, qty="2", pay="180")
    part = make(db, users["cashier"], product, customer=wholesale, qty="2", pay="50")
    due = make(db, users["cashier"], product, customer=wholesale, qty="2")
    assert (paid.payment_status, paid.due_paisa) == ("paid", 0)
    assert (part.payment_status, part.due_paisa) == ("partial", T("130"))
    assert (due.payment_status, due.due_paisa) == ("due", T("180"))
    pay.record_payment(db, users["cashier"], amount_paisa=T("130"), method="bkash", document=part)
    db.commit()
    assert part.payment_status == "paid" and part.paid_paisa == T("180")


def test_paid_amount_matches_payments_table(db, users, product, wholesale):
    inv = make(db, users["cashier"], product, customer=wholesale, qty="3", pay="100")
    pay.record_payment(db, users["cashier"], amount_paisa=T("50"), method="nagad", document=inv)
    db.commit()
    rows = db.scalars(select(Payment).where(Payment.document_id == inv.id)).all()
    assert sum(r.amount_paisa for r in rows) == inv.paid_paisa == T("150")


def test_overpayment_rejected(db, users, product, wholesale):
    with pytest.raises(BusinessError):
        make(db, users["cashier"], product, customer=wholesale, qty="1", pay="91")
    db.rollback()
    inv = make(db, users["cashier"], product, customer=wholesale, qty="1")
    with pytest.raises(BusinessError):
        pay.record_payment(db, users["cashier"], amount_paisa=T("91"), method="cash", document=inv)


def test_walk_in_must_pay_in_full(db, users, product):
    with pytest.raises(BusinessError) as e:
        make(db, users["cashier"], product, qty="1", pay="50")
    assert e.value.code == "walkin_due"
    db.rollback()
    assert make(db, users["cashier"], product, qty="1", pay="100").payment_status == "paid"


def test_credit_limit_blocks_unless_owner_approves(db, users, product, credit):
    # Limit Tk 500. Tk 400 due is fine.
    make(db, users["cashier"], product, customer=credit, qty="4")
    assert pay.customer_balance(db, credit.id) == T("400")
    # Another Tk 200 would make Tk 600 > 500.
    with pytest.raises(ApprovalRequired) as e:
        make(db, users["cashier"], product, customer=credit, qty="2")
    assert e.value.extra["kind"] == "credit"
    db.rollback()
    # A Manager cannot approve credit; only the Owner.
    with pytest.raises(ApprovalRequired):
        make(db, users["cashier"], product, customer=credit, qty="2",
             approvals=doc_svc.Approvals(credit=users["manager"]))
    db.rollback()
    inv = make(db, users["cashier"], product, customer=credit, qty="2",
               approvals=doc_svc.Approvals(credit=users["owner"]))
    assert inv.approved_by_id == users["owner"].id
    assert pay.customer_balance(db, credit.id) == T("600")


def test_big_discount_needs_manager(db, users, product, retail):
    # Default limit 10%. Tk 15 off a Tk 100 line by a cashier needs approval.
    with pytest.raises(ApprovalRequired) as e:
        make(db, users["cashier"], product, customer=retail, qty="1", discount="15", pay="85")
    assert e.value.extra["kind"] == "discount"
    db.rollback()
    inv = make(db, users["cashier"], product, customer=retail, qty="1", discount="15", pay="85",
               approvals=doc_svc.Approvals(discount=users["manager"]))
    assert inv.total_paisa == T("85") and inv.approved_by_id == users["manager"].id
    # Within the limit: no approval.
    assert make(db, users["cashier"], product, customer=retail, qty="1", discount="10", pay="90").approved_by_id is None


def test_installments(db, users, product, wholesale):
    inv = make(db, users["cashier"], product, customer=wholesale, qty="10", pay="300")  # total 900, due 600
    plan = pay.set_installment_plan(db, users["manager"], inv, count=3, first_due=date(2026, 1, 1), interval_days=30)
    db.commit()
    assert [p.amount_paisa for p in plan] == [T("200")] * 3
    assert inv.payment_status == "installment"
    view = pay.installment_view(db, inv, date(2026, 2, 15))
    assert [v["is_paid"] for v in view] == [False, False, False]
    assert [v["is_overdue"] for v in view] == [True, True, False]
    pay.record_payment(db, users["cashier"], amount_paisa=T("250"), method="cash", document=inv)
    db.commit()
    view = pay.installment_view(db, inv, date(2026, 2, 15))
    assert [v["is_paid"] for v in view] == [True, False, False]
    assert view[1]["paid_paisa"] == T("50")
    with pytest.raises(BusinessError):  # schedule must equal the due
        pay.set_installment_plan(db, users["manager"], inv, schedule=[(date(2026, 3, 1), T("100"))])


def test_reverse_payment_adds_negative_row(db, users, product, wholesale):
    inv = make(db, users["cashier"], product, customer=wholesale, qty="2", pay="180")
    p = db.scalar(select(Payment).where(Payment.document_id == inv.id))
    r = pay.reverse_payment(db, users["manager"], p, "bounced")
    db.commit()
    assert r.amount_paisa == -T("180") and r.reversal_of_id == p.id
    assert db.get(Payment, p.id).amount_paisa == T("180")  # original untouched
    assert inv.paid_paisa == 0 and inv.payment_status == "due"
    with pytest.raises(BusinessError):
        pay.reverse_payment(db, users["manager"], p, "again")


def test_customer_ledger_running_balance(db, users, product, wholesale):
    make(db, users["cashier"], product, customer=wholesale, qty="10", pay="400")  # 900 - 400
    pay.record_payment(db, users["cashier"], amount_paisa=T("100"), method="cash", customer=wholesale)
    db.commit()
    led = pay.customer_ledger(db, wholesale.id)
    assert [e["kind"] for e in led["entries"]] == ["invoice", "payment", "payment"]
    assert led["entries"][-1]["balance_paisa"] == led["balance_paisa"] == T("400")
    assert pay.customer_balance(db, wholesale.id) == T("400")
