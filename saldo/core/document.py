"""An invoice turned into the words and numbers that get printed, ready to draw.

build() decides every string on the page (dates spelled out, amounts formatted, empty parts left
out); doc/render.py only places them. Keeping this here means it's tested without Qt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from saldo.core import billing, dates, money
from saldo.core.model import Business, Invoice


@dataclass
class Row:
    description: str
    details: str
    qty: str
    rate: str
    amount: str


@dataclass
class InvoiceView:
    name: str
    tagline: str
    from_lines: list[str]  # business address and contact lines
    bill_to: str  # the client's name
    bill_lines: list[str]  # contact, address, email
    number: str
    issued: str
    terms: str
    due: str
    status: str  # draft / sent / paid / overdue
    big_label: str  # "Amount Due" or "Paid"
    big_amount: str
    big_note: str  # "Due by Oct 25, 2026" / "Due on receipt" / "Paid Oct 30, 2026"
    project: str
    project_lines: list[str]
    rows: list[Row]
    totals: list[tuple[str, str]]  # label, value (above the balance line)
    balance_label: str
    balance: str
    payment: str
    terms_text: str
    note: str
    footer: str
    logo: str = ""
    meta: list[tuple[str, str]] = field(default_factory=list)  # the strip: Invoice / Issued / Terms / Due


_MONTH = r"([A-Za-z]{3,9})"
_DAY = r"(\d{1,2})"
_YEAR = r"(\d{4})"
_TO = r"\s*[–—-]\s*"
_SPANS = [  # each as dates.span writes it, its parts in the order (first month, day, year, last month, day, year)
    (re.compile(rf"{_MONTH} {_DAY}, {_YEAR}"), (0, 1, 2, 0, 1, 2)),  # Sep 26, 2026
    (re.compile(rf"{_MONTH} {_DAY}{_TO}{_DAY}, {_YEAR}"), (0, 1, 3, 0, 2, 3)),  # Sep 26–27, 2026
    (
        re.compile(rf"{_MONTH} {_DAY}{_TO}{_MONTH} {_DAY}, {_YEAR}"),
        (0, 1, 4, 2, 3, 4),
    ),  # Sep 30 – Oct 2, 2026
    (
        re.compile(rf"{_MONTH} {_DAY}, {_YEAR}{_TO}{_MONTH} {_DAY}, {_YEAR}"),
        (0, 1, 2, 3, 4, 5),
    ),  # … – Jan 2, 2027
]


def _month(word: str) -> int:
    """ "Sep" or "September" -> 9 (0 if it isn't a month)."""
    w = word.casefold()
    for n, name in enumerate(dates.MONTH_NAMES, start=1):
        if len(w) >= 3 and name.casefold().startswith(w):
            return n
    return 0


def work_days(text: str) -> tuple[date, date] | None:
    """The first and last day of work dates as dates.span writes them ("Sep 26–27, 2026", "Sep 30 – Oct 2,
    2026", "Dec 30, 2026 – Jan 2, 2027", "Sep 26, 2026"), or None for words typed in an older Saldo."""
    t = " ".join(text.split())
    for pattern, order in _SPANS:
        m = pattern.fullmatch(t)
        if m is None:
            continue
        g = m.groups()
        try:
            first = date(int(g[order[2]]), _month(g[order[0]]), int(g[order[1]]))
            last = date(int(g[order[5]]), _month(g[order[3]]), int(g[order[4]]))
        except ValueError:  # not a month, or a day it doesn't have
            return None
        return (first, last) if first <= last else None
    return None


def status_of(inv: Invoice, today=None) -> str:
    """draft / sent / overdue / paid."""
    if inv.status == "sent":
        due = billing.due(inv.issued, inv.terms_days)
        if due is not None and due < (today or dates.today()):
            return "overdue"
    return inv.status


def build(inv: Invoice, b: Business, today=None) -> InvoiceView:
    sym = b.currency or "$"
    t = billing.totals(inv)
    due = billing.due(inv.issued, inv.terms_days)
    issued = dates.fmt(dates.parse(inv.issued))
    due_s = dates.fmt(due)

    from_lines = [line for line in b.address.strip().splitlines() if line.strip()]
    contact = [x.strip() for x in (b.email, b.phone, b.website) if x.strip()]
    from_lines += contact

    c = inv.client
    bill_lines = []
    if c.contact.strip():
        bill_lines.append(f"Attn: {c.contact.strip()}")
    bill_lines += [line for line in c.address.strip().splitlines() if line.strip()]
    if c.email.strip():
        bill_lines.append(c.email.strip())

    project_lines = []
    if inv.work_dates.strip():
        project_lines.append(f"Dates: {inv.work_dates.strip()}")
    delivered = dates.parse(inv.delivered)
    if delivered:
        project_lines.append(f"Delivered: {dates.fmt(delivered)}")

    rows = []
    for it in inv.items:
        if it.is_blank():
            continue
        q, r = money.parse(it.qty), money.parse(it.rate)
        amount = billing.line_amount(it.qty, it.rate)
        rows.append(
            Row(
                it.description.strip(),
                it.details.strip(),
                money.fmt_qty(q),
                money.fmt(r, sym),
                "Included" if r == 0 else money.fmt(amount, sym),
            )
        )

    tot: list[tuple[str, str]] = [("Subtotal", money.fmt(t.subtotal, sym))]
    if t.discount:
        tot.append(("Discount", money.fmt(-t.discount, sym)))
    if t.tax:
        tot.append((f"Sales Tax ({money.fmt_rate(inv.tax_rate)})", money.fmt(t.tax, sym)))
    if t.deposit:
        tot.append(("Total", money.fmt(t.total, sym)))
        tot.append(("Deposit Received", money.fmt(-t.deposit, sym)))

    status = status_of(inv, today)
    if status == "paid":
        paid_on = dates.fmt(dates.parse(inv.paid_on))
        big_label, big_amount = "Paid", money.fmt(t.total, sym)
        big_note = f"Paid {paid_on}" if paid_on else "Paid in full"
        balance_label, balance = "Balance Due", money.fmt(money.ZERO, sym)
    else:
        big_label, big_amount = "Amount Due", money.fmt(t.balance, sym)
        big_note = "Due on receipt" if inv.terms_days <= 0 else f"Due by {due_s}"
        balance_label, balance = "Balance Due", money.fmt(t.balance, sym)

    if inv.terms_days <= 0:
        due_line = "Payment is due on receipt."
    else:
        due_line = f"Payment is due within {inv.terms_days} days of the invoice date ({due_s})."
    terms_text = due_line + ("\n" + inv.terms.strip() if inv.terms.strip() else "")

    footer = "  ·  ".join(x for x in (b.name.strip(), b.email.strip(), b.phone.strip()) if x)

    return InvoiceView(
        name=b.name.strip(),
        tagline=b.tagline.strip(),
        from_lines=from_lines,
        bill_to=c.name.strip(),
        bill_lines=bill_lines,
        number=inv.number,
        issued=issued,
        terms=billing.terms_label(inv.terms_days),
        due=due_s if inv.terms_days > 0 else "On Receipt",
        status=status,
        big_label=big_label,
        big_amount=big_amount,
        big_note=big_note,
        project=inv.project.strip(),
        project_lines=project_lines,
        rows=rows,
        totals=tot,
        balance_label=balance_label,
        balance=balance,
        payment=inv.payment.strip(),
        terms_text=terms_text,
        note=inv.note.strip(),
        footer=footer,
        logo=b.look.logo,
        meta=[
            ("Invoice", inv.number),
            ("Issued", issued),
            ("Terms", billing.terms_label(inv.terms_days)),
            ("Due", due_s if inv.terms_days > 0 else "On Receipt"),
        ],
    )


def file_stem(inv: Invoice) -> str:
    """ "JLF-2026-001 Northwind Media": what an exported file is called (safe on every system)."""
    raw = f"{inv.number} {inv.client.name}".strip() or "Invoice"
    bad = '<>:"/\\|?*'
    clean = "".join("-" if ch in bad or ord(ch) < 32 else ch for ch in raw)
    return " ".join(clean.split()).strip(" .") or "Invoice"


def summary_text(view: InvoiceView) -> str:
    """Plain text of the whole invoice (Copy Invoice Text), for pasting into an email."""
    lines = [f"Invoice {view.number}", f"From: {view.name}"]
    if view.bill_to:
        lines.append(f"Bill to: {view.bill_to}")
    lines.append(f"Issued: {view.issued} · {view.terms} · Due: {view.due}")
    if view.project:
        lines.append(f"Project: {view.project}")
    lines.append("")
    for r in view.rows:
        lines.append(f"- {r.description}: {r.qty} × {r.rate} = {r.amount}")
    lines.append("")
    for label, value in view.totals:
        lines.append(f"{label}: {value}")
    lines.append(f"{view.balance_label}: {view.balance}")
    if view.payment:
        lines += ["", view.payment]
    return "\n".join(lines)
