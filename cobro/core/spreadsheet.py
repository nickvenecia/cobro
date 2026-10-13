"""Invoices out as a CSV file (one row each), for your bookkeeping or your taxes.

Numbers are plain ("1500.00", no currency sign) so a spreadsheet adds them up. Text that a spreadsheet would
run as a formula (starting with = + - @) gets a leading ' so it shows as typed. Written to a temp file beside
the target and moved into place, like every export. No Qt here.
"""

from __future__ import annotations

import csv
import io
import os
import tempfile
from decimal import Decimal
from pathlib import Path

from cobro.core import dates, document, money
from cobro.core.model import Business, Invoice

COLUMNS = [
    "Invoice", "Client", "Project", "From", "Issued", "Due", "Status", "Paid On",
    "Subtotal", "Discount", "Tax", "Total", "Deposit", "Balance", "Currency",
]  # fmt: skip


def safe_cell(value) -> object:
    """A cell for a CSV that a spreadsheet will open: text starting with = + - @ would run as a formula
    (and can fetch web pages or run commands), so it gets a leading ' (shown as text). Numbers stay."""
    if not isinstance(value, str) or not value or value[0] not in "=+-@\t\r":
        return value
    try:
        Decimal(value)
        return value  # -50 is a number, not a formula
    except ArithmeticError:
        return "'" + value


def rows(invoices: list[Invoice], businesses: dict[str, Business], today=None) -> list[list[str]]:
    """The header row, then one row per invoice."""
    out = [COLUMNS]
    for inv in invoices:
        b = businesses.get(inv.business_id)
        t = money.totals(inv)
        due = dates.due(inv.issued, inv.terms_days)
        status = document.status_of(inv, today)
        out.append(
            [
                inv.number,
                inv.client.name,
                inv.project,
                b.name if b else "",
                inv.issued,
                dates.iso(due) if due else "",
                status.title(),
                inv.paid_on if status == "paid" else "",
                f"{t.subtotal:.2f}",
                f"{t.discount:.2f}",
                f"{t.tax:.2f}",
                f"{t.total:.2f}",
                f"{t.deposit:.2f}",
                f"{t.balance:.2f}",
                (b.currency if b else "$") or "$",
            ]
        )
    return out


def write_csv(invoices: list[Invoice], businesses: dict[str, Business], path: Path) -> None:
    buf = io.StringIO()
    w = csv.writer(buf)
    for r in rows(invoices, businesses):
        w.writerow([safe_cell(c) for c in r])
    path = Path(path)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as f:  # the BOM: Excel reads it as UTF-8
            f.write(buf.getvalue())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
