"""Stock ledger. Stock on hand is always SUM(qty_milli) of a product's movements."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..errors import BusinessError, NotFound
from ..models import MOVEMENT_TYPES, Product, StockMovement, User
from ..money import fmt_qty
from . import audit, settings

MANUAL_TYPES = {"stock_in", "adjustment", "damage", "return"}


def stock_of(db: Session, product_id: int) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(StockMovement.qty_milli), 0))
                         .where(StockMovement.product_id == product_id)))


def stock_map(db: Session, product_ids: Iterable[int] | None = None) -> dict[int, int]:
    q = select(StockMovement.product_id, func.sum(StockMovement.qty_milli)).group_by(StockMovement.product_id)
    if product_ids is not None:
        ids = list(product_ids)
        if not ids:
            return {}
        q = q.where(StockMovement.product_id.in_(ids))
    return {pid: int(total or 0) for pid, total in db.execute(q)}


def _lock_products(db: Session, product_ids: list[int]) -> dict[int, Product]:
    # FOR UPDATE serialises concurrent sales of the same product on PostgreSQL.
    rows = db.scalars(select(Product).where(Product.id.in_(product_ids)).with_for_update()).all()
    found = {p.id: p for p in rows}
    missing = set(product_ids) - set(found)
    if missing:
        raise NotFound(f"Product {sorted(missing)[0]}")
    return found


def check_available(db: Session, outgoing: dict[int, int]) -> None:
    """Raise if any product would go below zero (unless the Owner allowed it)."""
    if not outgoing or settings.get_bool(db, "allow_negative_stock"):
        return
    products = _lock_products(db, list(outgoing))
    on_hand = stock_map(db, outgoing.keys())
    short = []
    for pid, qty in outgoing.items():
        have = on_hand.get(pid, 0)
        if have - qty < 0:
            p = products[pid]
            short.append(f"{p.name}: have {fmt_qty(have)} {p.unit}, need {fmt_qty(qty)}")
    if short:
        raise BusinessError("Not enough stock. " + "; ".join(short), code="insufficient_stock")


def add_movement(db: Session, user: User, product_id: int, qty_milli: int, type_: str, *,
                 document_id: int | None = None, reason: str | None = None,
                 reference: str | None = None, reversal_of_id: int | None = None) -> StockMovement:
    if type_ not in MOVEMENT_TYPES:
        raise BusinessError(f"Unknown movement type: {type_}")
    if qty_milli == 0:
        raise BusinessError("Quantity cannot be zero")
    m = StockMovement(product_id=product_id, qty_milli=qty_milli, type=type_, document_id=document_id,
                      reason=reason, reference=reference, reversal_of_id=reversal_of_id, user_id=user.id)
    db.add(m)
    db.flush()
    return m


def manual_movement(db: Session, user: User, product_id: int, qty_milli: int, type_: str,
                    reason: str | None, reference: str | None = None) -> StockMovement:
    """Stock in / out screen.

    stock_in and return must be positive; damage must be negative; adjustment can be
    either sign but needs a reason. Damage also needs a reason.
    """
    if type_ not in MANUAL_TYPES:
        raise BusinessError("Choose stock_in, return, adjustment or damage")
    if not db.get(Product, product_id):
        raise NotFound("Product")
    reason = (reason or "").strip() or None
    if type_ in ("stock_in", "return") and qty_milli <= 0:
        raise BusinessError("Stock in quantity must be positive")
    if type_ == "damage":
        qty_milli = -abs(qty_milli)
    if type_ in ("adjustment", "damage") and not reason:
        raise BusinessError("A reason is required for adjustments and damage", code="reason_required")
    if qty_milli < 0:
        check_available(db, {product_id: -qty_milli})
    before = stock_of(db, product_id)
    m = add_movement(db, user, product_id, qty_milli, type_, reason=reason, reference=reference)
    audit.log(db, user, "stock", product_id, type_, "stock", fmt_qty(before), fmt_qty(before + qty_milli), reason)
    return m


def post_document_out(db: Session, user: User, document_id: int, lines: list[tuple[int, int]]) -> None:
    """Write one `sale` row per product for a delivery challan or invoice."""
    outgoing: dict[int, int] = defaultdict(int)
    for product_id, qty in lines:
        outgoing[product_id] += qty
    check_available(db, outgoing)
    for product_id, qty in outgoing.items():
        add_movement(db, user, product_id, -qty, "sale", document_id=document_id)


def reverse_document(db: Session, user: User, document_id: int, reason: str) -> int:
    """Add an opposite row for every not-yet-reversed movement of a document.

    Never edits old rows. Returns the number of reversal rows written.
    """
    rows = db.scalars(select(StockMovement).where(StockMovement.document_id == document_id)).all()
    reversed_ids = {r.reversal_of_id for r in rows if r.reversal_of_id}
    count = 0
    for r in rows:
        if r.reversal_of_id or r.id in reversed_ids:
            continue
        add_movement(db, user, r.product_id, -r.qty_milli, "void_reversal", document_id=document_id,
                     reason=reason, reversal_of_id=r.id)
        count += 1
    return count


def low_stock(db: Session) -> list[dict]:
    products = db.scalars(select(Product).where(Product.is_active.is_(True)).order_by(Product.name)).all()
    on_hand = stock_map(db, [p.id for p in products])
    out = []
    for p in products:
        have = on_hand.get(p.id, 0)
        if have <= p.low_stock_milli:
            out.append({"product_id": p.id, "name": p.name, "name_bn": p.name_bn, "sku": p.sku, "unit": p.unit,
                        "stock_milli": have, "low_stock_milli": p.low_stock_milli})
    return out
