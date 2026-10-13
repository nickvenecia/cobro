"""Amounts and totals, in exact decimals (never floats, so cents always add up)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from cobro.core.model import Invoice

CENT = Decimal("0.01")
ZERO = Decimal(0)
MINUS = "−"  # a real minus sign, the width of a digit


def parse(text: str | int | float | Decimal | None) -> Decimal:
    """What someone typed -> a number. "$1,500.50", "1500", " 2.5 " all work; anything else is 0."""
    if isinstance(text, Decimal):
        return text
    if text is None:
        return ZERO
    s = re.sub(r"[^\d.\-]", "", str(text))
    if s in ("", "-", ".", "-."):
        return ZERO
    try:
        return Decimal(s)
    except InvalidOperation:
        return ZERO


def cents(d: Decimal) -> Decimal:
    return d.quantize(CENT, rounding=ROUND_HALF_UP)


def fmt(d: Decimal, symbol: str = "$") -> str:
    """2700 -> "$2,700.00"; -50 -> "−$50.00"."""
    d = cents(d)
    sign = MINUS if d < 0 else ""
    return f"{sign}{symbol}{abs(d):,.2f}"


def fmt_qty(d: Decimal) -> str:
    """1 -> "1", 2.50 -> "2.5"."""
    if d == d.to_integral_value():
        return f"{int(d):,}"
    return f"{d.normalize():f}"


def fmt_rate(text: str) -> str:
    """A tax rate as typed -> "8.25%"."""
    return f"{fmt_qty(parse(text))}%"


@dataclass(frozen=True)
class Totals:
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total: Decimal
    deposit: Decimal
    balance: Decimal


def line_amount(qty: str, rate: str) -> Decimal:
    return cents(parse(qty) * parse(rate))


def totals(inv: Invoice) -> Totals:
    subtotal = sum((line_amount(i.qty, i.rate) for i in inv.items), ZERO)
    discount = cents(max(ZERO, parse(inv.discount)))
    taxable = max(ZERO, subtotal - discount)
    tax = cents(taxable * max(ZERO, parse(inv.tax_rate)) / 100)
    total = taxable + tax
    deposit = cents(max(ZERO, parse(inv.deposit)))
    return Totals(subtotal, discount, tax, total, deposit, total - deposit)
