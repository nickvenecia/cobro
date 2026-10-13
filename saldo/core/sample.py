"""A made-up business, clients and invoices, used by the smoke test, the tests and screenshots (never by real
data)."""

from __future__ import annotations

from dataclasses import replace

from saldo.core.model import Business, Client, Invoice, LineItem, Look
from saldo.core.store import DEFAULT_NOTE, DEFAULT_TERMS, Library


def business(look: Look | None = None) -> Business:
    return Business(
        id="sample-business",
        name="Juniper Lane Films",
        tagline="Director · Cinematographer · Editor",
        address="1200 Sample Ave\nAlbuquerque, NM 87102",
        email="hello@juniperlane.example",
        phone="(505) 555-0142",
        prefix="JLF",
        terms_days=15,
        payment="Checks payable to Juniper Lane Films, mailed to:\n1200 Sample Ave, Albuquerque, NM 87102\n\n"
        "Zelle / ACH details available on request.",
        terms=DEFAULT_TERMS,
        note=DEFAULT_NOTE,
        look=look or Look(),
    )


def invoice(items: int = 3) -> Invoice:
    base = [
        LineItem(
            "Production",
            "Shoot day: directing and cinematography, camera package",
            "1",
            "1500",
        ),
        LineItem("Post-production", "Edit, color grade, sound mix, final export", "1", "1200"),
        LineItem("Revisions", "Two rounds of client revisions", "1", "0"),
    ]
    rows = [base[i % 3] for i in range(items)]
    return Invoice(
        id="sample-invoice",
        business_id="sample-business",
        number="JLF-2026-001",
        client=Client(
            name="Northwind Media",
            contact="Alex Rivera",
            address="88 Example St\nPhoenix, AZ 85004",
        ),
        issued="2026-10-10",
        terms_days=15,
        project="Fall Brand Film",
        work_dates="Sep 26–27, 2026",
        delivered="2026-10-09",
        items=rows,
        payment=business().payment,
        terms=DEFAULT_TERMS,
        note=DEFAULT_NOTE,
    )


def fill(lib: Library) -> Library:
    """Add the sample profile, three clients and four invoices (a draft, one sent, one overdue, one paid) to
    an (empty) library."""
    from datetime import timedelta

    from saldo.core import dates

    b = lib.add_business(business())
    northwind = lib.save_client(invoice().client)
    desert = lib.save_client(Client(name="Desert Sun Records", address="12 Mesa Rd\nTucson, AZ 85701"))
    mesa = lib.save_client(Client(name="Mesa Coffee Co.", contact="Jordan Lee"))
    today = dates.today()
    plans = [
        (northwind, "draft", today, "Fall Brand Film", 3),
        (desert, "sent", today - timedelta(days=5), "Album Teaser", 2),
        (mesa, "sent", today - timedelta(days=40), "Menu Spots", 1),
        (desert, "paid", today - timedelta(days=60), "Live Session", 3),
    ]
    for client, status, issued, project, items in plans:
        inv = lib.new_invoice(b, today=issued)
        inv.client = replace(client)
        inv.project = project
        inv.items = invoice(items).items
        inv.status = status
        if status != "draft":
            inv.sent_on = dates.iso(issued)
            inv.auto_number = False
        if status == "paid":
            inv.paid_on = dates.iso(issued + timedelta(days=12))
        lib.save_invoice(inv)
    return lib
