"""Pure money / quantity helpers. No database, no floats.

* Money is stored as integer paisa (1 taka = 100 paisa).
* Quantity is stored as integer milli-units (1 piece = 1000, 0.25 kg = 250),
  so kg sales work without floating point.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

QTY_SCALE = 1000


class MoneyError(ValueError):
    pass


def div_round_half_up(numerator: int, denominator: int) -> int:
    """Integer division rounded half away from zero."""
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    sign = -1 if numerator < 0 else 1
    q, r = divmod(abs(numerator), denominator)
    if r * 2 >= denominator:
        q += 1
    return sign * q


def taka_to_paisa(value: str | int | Decimal) -> int:
    """'1234.5' -> 123450. Rejects more than 2 decimal places."""
    try:
        d = Decimal(str(value).replace(",", "").strip())
    except InvalidOperation as exc:
        raise MoneyError(f"invalid amount: {value!r}") from exc
    if d != d.quantize(Decimal("0.01")):
        raise MoneyError("amount can have at most 2 decimal places")
    return int((d * 100).to_integral_value(rounding=ROUND_HALF_UP))


def paisa_to_taka_str(paisa: int) -> str:
    sign = "-" if paisa < 0 else ""
    p = abs(paisa)
    return f"{sign}{p // 100}.{p % 100:02d}"


def fmt_taka(paisa: int, symbol: str = "৳") -> str:
    sign = "-" if paisa < 0 else ""
    p = abs(paisa)
    whole = f"{p // 100:,}"
    return f"{sign}{symbol}{whole}.{p % 100:02d}"


def qty_to_milli(value: str | int | Decimal) -> int:
    try:
        d = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise MoneyError(f"invalid quantity: {value!r}") from exc
    if d != d.quantize(Decimal("0.001")):
        raise MoneyError("quantity can have at most 3 decimal places")
    return int(d * QTY_SCALE)


def fmt_qty(milli: int) -> str:
    sign = "-" if milli < 0 else ""
    m = abs(milli)
    whole, frac = divmod(m, QTY_SCALE)
    if frac == 0:
        return f"{sign}{whole}"
    return f"{sign}{whole}.{frac:03d}".rstrip("0")


def line_amounts(unit_price_paisa: int, qty_milli: int, discount_paisa: int = 0) -> tuple[int, int]:
    """Return (gross, net) paisa for one line.

    gross = unit price x quantity (rounded half-up to the paisa)
    net   = gross - discount
    """
    if unit_price_paisa < 0:
        raise MoneyError("unit price cannot be negative")
    if qty_milli <= 0:
        raise MoneyError("quantity must be greater than zero")
    if discount_paisa < 0:
        raise MoneyError("discount cannot be negative")
    gross = div_round_half_up(unit_price_paisa * qty_milli, QTY_SCALE)
    if discount_paisa > gross:
        raise MoneyError("discount cannot exceed the line amount")
    return gross, gross - discount_paisa


def discount_needs_approval(subtotal_paisa: int, discount_paisa: int, limit_percent: Decimal | str | int) -> bool:
    """True when the discount exceeds `limit_percent` % of the subtotal."""
    if discount_paisa <= 0:
        return False
    if subtotal_paisa <= 0:
        return True
    limit = Decimal(str(limit_percent))
    # discount / subtotal > limit / 100   <=>   discount * 100 > limit * subtotal
    return Decimal(discount_paisa) * 100 > limit * Decimal(subtotal_paisa)


PAID, PARTIAL, DUE, INSTALLMENT = "paid", "partial", "due", "installment"


def payment_status(total_paisa: int, paid_paisa: int, has_installment_plan: bool) -> str:
    if paid_paisa >= total_paisa:
        return PAID
    if has_installment_plan:
        return INSTALLMENT
    if paid_paisa > 0:
        return PARTIAL
    return DUE


def split_installments(amount_paisa: int, count: int) -> list[int]:
    """Split an amount into `count` parts; the remainder paisa go on the last part."""
    if count < 1:
        raise MoneyError("installment count must be at least 1")
    if amount_paisa <= 0:
        raise MoneyError("nothing left to split")
    base = amount_paisa // count
    parts = [base] * count
    parts[-1] += amount_paisa - base * count
    return parts
