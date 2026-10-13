"""What the main window's parts share: the places in the sidebar and their titles (the invoice places, then
All Clients), and which invoices each place shows."""

from __future__ import annotations

from cobro.core import document
from cobro.core.model import Invoice

# the sidebar's places, in order: key -> (title, icon)
PLACES = {
    "all": ("All Invoices", "receipt"),
    "drafts": ("Drafts", "edit"),
    "unpaid": ("Unpaid", "clock"),
    "paid": ("Paid", "check"),
}
TITLES = {**{k: v[0] for k, v in PLACES.items()}, "clients": "All Clients"}  # every place in the sidebar
STATUS_WORDS = {"draft": "Draft", "sent": "Sent", "overdue": "Overdue", "paid": "Paid"}
STATUS_COLORS = {"draft": "MUTED", "sent": "WARN", "overdue": "BAD", "paid": "GOOD"}  # token names


def in_place(inv: Invoice, place: str, today=None) -> bool:
    """Does this invoice belong in a place? (Unpaid is sent and overdue.)"""
    st = document.status_of(inv, today)
    if place == "drafts":
        return st == "draft"
    if place == "unpaid":
        return st in ("sent", "overdue")
    if place == "paid":
        return st == "paid"
    return True
