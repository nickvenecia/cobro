"""An invoice turned into the words and numbers that get printed, ready to draw.

build() decides every string on the page (dates spelled out, amounts formatted, empty parts left
out); doc/render.py only places them. Keeping this here means it's tested without Qt.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import dates, money
from .model import Business, Invoice


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


def status_of(inv: Invoice, today=None) -> str:
    """draft / sent / overdue / paid."""
    if inv.status == "sent":
        due = dates.due(inv.issued, inv.terms_days)
        if due is not None and due < (today or dates.today()):
            return "overdue"
    return inv.status


def build(inv: Invoice, b: Business, today=None) -> InvoiceView:
    sym = b.currency or "$"
    t = money.totals(inv)
    due = dates.due(inv.issued, inv.terms_days)
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
        amount = money.line_amount(it.qty, it.rate)
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
        terms=dates.terms_label(inv.terms_days),
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
            ("Terms", dates.terms_label(inv.terms_days)),
            ("Due", due_s if inv.terms_days > 0 else "On Receipt"),
        ],
    )


def file_stem(inv: Invoice) -> str:
    """ "NV-2026-001 Digital Empire": what an exported file is called (safe on every system)."""
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
