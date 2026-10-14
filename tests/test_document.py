"""What gets printed (core/document.py)."""

from __future__ import annotations

from datetime import date

from saldo.core import document, sample
from saldo.core.model import Invoice, LineItem


def test_the_sample_invoice_reads_right():
    v = document.build(sample.invoice(), sample.business(), today=date(2026, 10, 10))
    assert v.big_label == "Amount Due" and v.big_amount == "$2,700.00"
    assert v.big_note == "Due by Oct 25, 2026"
    assert v.meta == [
        ("Invoice", "JLF-2026-001"),
        ("Issued", "Oct 10, 2026"),
        ("Terms", "Net 15"),
        ("Due", "Oct 25, 2026"),
    ]
    assert v.bill_lines[0] == "Attn: Alex Rivera"
    assert v.project_lines == ["Dates: Sep 26–27, 2026", "Delivered: Oct 9, 2026"]
    assert v.rows[2].amount == "Included"
    assert v.terms_text.startswith("Payment is due within 15 days of the invoice date (Oct 25, 2026).")


def test_blank_lines_are_left_out():
    inv = sample.invoice()
    inv.items.append(LineItem())
    assert len(document.build(inv, sample.business()).rows) == 3


def test_paid_invoices_say_paid():
    inv = sample.invoice()
    inv.status, inv.paid_on = "paid", "2026-10-20"
    v = document.build(inv, sample.business())
    assert v.big_label == "Paid" and v.big_note == "Paid Oct 20, 2026" and v.balance == "$0.00"


def test_overdue_only_when_sent_and_past_due():
    inv = Invoice(issued="2026-09-01", terms_days=15, status="sent")
    assert document.status_of(inv, today=date(2026, 10, 1)) == "overdue"
    assert document.status_of(inv, today=date(2026, 9, 10)) == "sent"
    inv.status = "draft"
    assert document.status_of(inv, today=date(2026, 10, 1)) == "draft"


def test_due_on_receipt():
    inv = sample.invoice()
    inv.terms_days = 0
    v = document.build(inv, sample.business())
    assert v.big_note == "Due on receipt" and v.terms_text.startswith("Payment is due on receipt.")


def test_file_names_are_safe():
    inv = Invoice(number="JLF-2026-001")
    inv.client.name = 'Northwind: Media/"West"'
    assert document.file_stem(inv) == "JLF-2026-001 Northwind- Media--West-"
    assert document.file_stem(Invoice()) == "Invoice"


def test_work_days_read_back_what_the_calendar_wrote():
    from datetime import timedelta

    from saldo.core import dates

    for first in (date(2026, 9, 26), date(2026, 9, 30), date(2026, 12, 30)):
        for n in (0, 1, 3, 40):
            last = first + timedelta(days=n)
            assert document.work_days(dates.span(first, last)) == (first, last)
    assert document.work_days("Oct 1–3, 2026") == (date(2026, 10, 1), date(2026, 10, 3))
    for typed in ("Sep 26, 27 and Oct 2", "Feb 30, 2026", "Oct 5–3, 2026", "Fall 2026", ""):
        assert document.work_days(typed) is None  # typed in an older Saldo: kept as it is
