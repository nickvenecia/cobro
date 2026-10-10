"""What gets printed (core/document.py)."""

from __future__ import annotations

from datetime import date

from cobro.core import document, sample
from cobro.core.model import Invoice, LineItem


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
    inv = Invoice(number="NV-2026-001")
    inv.client.name = 'Digital: Empire/"West"'
    assert document.file_stem(inv) == "NV-2026-001 Digital- Empire--West-"
    assert document.file_stem(Invoice()) == "Invoice"
