"""Pure money rules (no database)."""
import pytest

from app.money import (
    MoneyError, discount_needs_approval, div_round_half_up, fmt_qty, fmt_taka, line_amounts,
    payment_status, qty_to_milli, split_installments, taka_to_paisa,
)


def test_taka_parsing_is_exact():
    assert taka_to_paisa("0.1") + taka_to_paisa("0.2") == taka_to_paisa("0.3")
    assert taka_to_paisa("1,234.50") == 123450
    with pytest.raises(MoneyError):
        taka_to_paisa("1.005")


def test_line_amounts_with_fractional_kg():
    # 1.5 kg x Tk 72.25 = Tk 108.375 -> rounds half-up to Tk 108.38
    gross, net = line_amounts(7225, qty_to_milli("1.5"), 0)
    assert gross == 10838 and net == 10838
    gross, net = line_amounts(10000, qty_to_milli("3"), 2500)
    assert (gross, net) == (30000, 27500)


def test_line_rejects_bad_input():
    with pytest.raises(MoneyError):
        line_amounts(100, 0)
    with pytest.raises(MoneyError):
        line_amounts(100, 1000, 101)


def test_rounding():
    assert div_round_half_up(5, 10) == 1
    assert div_round_half_up(4, 10) == 0
    assert div_round_half_up(-5, 10) == -1


def test_discount_threshold():
    assert not discount_needs_approval(10000, 1000, "10")   # exactly 10% is allowed
    assert discount_needs_approval(10000, 1001, "10")
    assert not discount_needs_approval(10000, 0, "0")


def test_payment_status():
    assert payment_status(1000, 1000, False) == "paid"
    assert payment_status(1000, 400, False) == "partial"
    assert payment_status(1000, 0, False) == "due"
    assert payment_status(1000, 400, True) == "installment"


def test_split_installments_keeps_every_paisa():
    parts = split_installments(100001, 3)
    assert sum(parts) == 100001 and parts == [33333, 33333, 33335]


def test_formatting():
    assert fmt_taka(123456789) == "৳1,234,567.89"
    assert fmt_qty(1500) == "1.5" and fmt_qty(2000) == "2"
