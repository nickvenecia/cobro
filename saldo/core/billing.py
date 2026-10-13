"""An invoice's sums (subtotal, discount, tax, total, deposit, balance) and its due date from the payment terms.

Saldo's own invoice math, on top of the shared money.py and dates.py. No Qt here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from saldo.core import dates
from saldo.core.model import Invoice
from saldo.core.money import ZERO, cents, parse


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


def due(issued: str, terms_days: int) -> date | None:
    """When an invoice issued on `issued` ("2026-10-13") is due."""
    d = dates.parse(issued)
    return d + timedelta(days=max(0, terms_days)) if d else None


def terms_label(days: int) -> str:
    return "Due on Receipt" if days <= 0 else f"Net {days}"
