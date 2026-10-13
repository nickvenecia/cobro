"""Amounts and totals (core/money.py): exact cents, forgiving input."""

from __future__ import annotations

from decimal import Decimal

from cobro.core import billing, money
from cobro.core.model import Invoice, LineItem


def test_typed_amounts_are_read_the_way_people_write_them():
    assert money.parse("$1,500.50") == Decimal("1500.50")
    assert money.parse(" 2.5 ") == Decimal("2.5")
    assert money.parse("") == 0
    assert money.parse("abc") == 0
    assert money.parse(None) == 0


def test_formatting():
    assert money.fmt(Decimal("2700")) == "$2,700.00"
    assert money.fmt(Decimal("-50")) == "−$50.00"
    assert money.fmt(Decimal("10"), "€") == "€10.00"
    assert money.fmt_qty(Decimal("1.0")) == "1"
    assert money.fmt_qty(Decimal("2.50")) == "2.5"


def test_cents_add_up_exactly():
    inv = Invoice(items=[LineItem("a", "", "3", "0.10"), LineItem("b", "", "1", "0.20")])
    assert billing.totals(inv).total == Decimal("0.50")  # floats would give 0.5000000000000001


def test_discount_tax_and_deposit():
    inv = Invoice(
        items=[
            LineItem("Production", "", "1", "1500"),
            LineItem("Edit", "", "2", "600"),
        ],
        discount="200",
        tax_rate="8.25",
        deposit="500",
    )
    t = billing.totals(inv)
    assert t.subtotal == Decimal("2700.00")
    assert t.tax == Decimal("206.25")  # 8.25% of 2,500
    assert t.total == Decimal("2706.25")
    assert t.balance == Decimal("2206.25")


def test_a_discount_bigger_than_the_work_never_goes_negative():
    inv = Invoice(items=[LineItem("x", "", "1", "100")], discount="500")
    assert billing.totals(inv).total == 0


def test_a_number_too_big_to_be_real_counts_as_zero():
    """A 40-digit rate (a stuck key, a paste gone wrong) used to crash rounding to the cent."""
    assert money.parse("9" * 40) == 0 and money.fmt(money.parse("9" * 40)) == "$0.00"
    assert billing.line_amount("1", "9" * 40) == 0
