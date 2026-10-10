"""Saving and loading: everything lives as small JSON files in Cobro's data folder.

    businesses.json   your business(es), with their look and defaults
    clients.json      everyone you've billed (filled in as you write invoices)
    invoices/<id>.json   one file per invoice
    settings.json     window and app preferences

Every write goes to a temp file next to the real one, then replaces it in one step, so a crash
or a full disk never leaves a half-written file. A file that can't be read is set aside as
<name>.unreadable-<time> (never deleted) and logged.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any

from . import dates, numbering
from .log import get_logger
from .model import Business, Client, Invoice, LineItem, new_id, now_iso
from .paths import data_dir

log = get_logger(__name__)

DEFAULT_TERMS = (
    "The work listed above is complete and has been delivered.\n"
    "Balances not paid by the due date accrue a late fee of 1.5% per month.\n"
    "Usage rights to the final deliverables transfer to the client upon payment in full."
)
DEFAULT_NOTE = "Thank you for the work."


def write_json(path: Path, data: Any) -> None:
    """Write atomically: a temp file in the same folder, then os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            log.warning("couldn't remove %s", tmp, exc_info=True)
        raise


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        aside = path.with_name(f"{path.name}.unreadable-{int(time.time())}")
        log.warning("couldn't read %s; keeping it as %s", path, aside.name, exc_info=True)
        try:
            path.replace(aside)
        except OSError:
            log.warning("couldn't set %s aside", path, exc_info=True)
        return default


def suggested_payment(b: Business) -> str:
    """A starting point for "How to Pay", from the business's own details."""
    who = b.name.strip() or "the business above"
    where = (b.mail_address or b.address).strip().replace("\n", ", ")
    lines = [f"Checks payable to {who}" + (f", mailed to:\n{where}" if where else ".")]
    lines.append("Zelle / ACH details available on request.")
    return "\n\n".join(lines)


class Library:
    """Everything Cobro knows, loaded from the data folder and saved back file by file."""

    def __init__(self, root: Path | None = None):
        self.root = root or data_dir()
        self.businesses: dict[str, Business] = {}
        self.clients: dict[str, Client] = {}
        self.invoices: dict[str, Invoice] = {}
        self.settings: dict[str, Any] = {}

    # ------------------------------------------------------------------ files
    @property
    def _inv_dir(self) -> Path:
        return self.root / "invoices"

    def load(self) -> Library:
        raw = read_json(self.root / "businesses.json", [])
        self.businesses = {}
        for d in raw if isinstance(raw, list) else []:
            b = Business.from_dict(d)
            self.businesses[b.id] = b
        raw = read_json(self.root / "clients.json", [])
        self.clients = {}
        for d in raw if isinstance(raw, list) else []:
            c = Client.from_dict(d)
            self.clients[c.id] = c
        self.invoices = {}
        if self._inv_dir.is_dir():
            for f in sorted(self._inv_dir.glob("*.json")):
                data = read_json(f, None)
                if isinstance(data, dict):
                    inv = Invoice.from_dict(data)
                    self.invoices[inv.id] = inv
        s = read_json(self.root / "settings.json", {})
        self.settings = s if isinstance(s, dict) else {}
        log.info(
            "loaded %d businesses, %d clients, %d invoices from %s",
            len(self.businesses), len(self.clients), len(self.invoices), self.root,
        )  # fmt: skip
        return self

    def save_businesses(self) -> None:
        write_json(
            self.root / "businesses.json",
            [b.to_dict() for b in self.businesses.values()],
        )

    def save_clients(self) -> None:
        clients = sorted(self.clients.values(), key=lambda c: c.name.casefold())
        write_json(self.root / "clients.json", [c.to_dict() for c in clients])

    def save_invoice(self, inv: Invoice) -> None:
        inv.updated = now_iso()
        self.invoices[inv.id] = inv
        write_json(self._inv_dir / f"{inv.id}.json", inv.to_dict())

    def save_settings(self) -> None:
        write_json(self.root / "settings.json", self.settings)

    # ------------------------------------------------------------------ businesses
    def add_business(self, b: Business) -> Business:
        if not b.prefix:
            b.prefix = numbering.initials(b.name)
        b.prefix = numbering.clean_prefix(b.prefix)
        if not b.payment.strip():
            b.payment = suggested_payment(b)
        if not b.terms.strip():
            b.terms = DEFAULT_TERMS
        if not b.note.strip():
            b.note = DEFAULT_NOTE
        self.businesses[b.id] = b
        self.save_businesses()
        return b

    def delete_business(self, business_id: str) -> None:
        """Only allowed while no invoice uses it (the window checks first)."""
        if any(i.business_id == business_id for i in self.invoices.values()):
            raise ValueError("Invoices still use this business.")
        self.businesses.pop(business_id, None)
        self.save_businesses()

    # ------------------------------------------------------------------ invoices
    def ordered(self) -> list[Invoice]:
        """Newest first: by issue date, then by number."""
        return sorted(
            self.invoices.values(),
            key=lambda i: (i.issued, i.number, i.created),
            reverse=True,
        )

    def next_number(self, business: Business, year: int | None = None) -> str:
        year = year or dates.today().year
        return numbering.next_number(business.prefix, (i.number for i in self.invoices.values()), year)

    def new_invoice(self, business: Business, today: date | None = None) -> Invoice:
        today = today or dates.today()
        tax = business.tax_rate
        inv = Invoice(
            business_id=business.id,
            number=self.next_number(business, today.year),
            issued=dates.iso(today),
            terms_days=business.terms_days,
            delivered=dates.iso(today),
            items=[LineItem()],
            tax_rate=tax,
            payment=business.payment,
            terms=business.terms,
            note=business.note,
        )
        self.save_invoice(inv)
        log.info("new invoice %s", inv.number)
        return inv

    def duplicate(self, inv: Invoice, today: date | None = None) -> Invoice:
        """A fresh draft with the same client and line items, a new number and today's date."""
        today = today or dates.today()
        business = self.businesses.get(inv.business_id)
        copy = Invoice.from_dict(inv.to_dict())
        copy.id = new_id()
        copy.number = (
            self.next_number(business, today.year)
            if business
            else numbering.next_number("INV", [], today.year)
        )
        copy.issued = dates.iso(today)
        copy.delivered = dates.iso(today) if inv.delivered else ""
        copy.status, copy.sent_on, copy.paid_on = "draft", "", ""
        copy.created = now_iso()
        self.save_invoice(copy)
        log.info("duplicated %s as %s", inv.number, copy.number)
        return copy

    def delete_invoice(self, invoice_id: str) -> None:
        self.invoices.pop(invoice_id, None)
        try:
            (self._inv_dir / f"{invoice_id}.json").unlink(missing_ok=True)
        except OSError:
            log.warning("couldn't delete invoice file %s", invoice_id, exc_info=True)

    # ------------------------------------------------------------------ clients
    def find_client(self, name: str) -> Client | None:
        key = name.strip().casefold()
        if not key:
            return None
        return next((c for c in self.clients.values() if c.name.strip().casefold() == key), None)

    def remember_client(self, c: Client) -> Client | None:
        """Keep a client's latest details for next time (matched by name). Returns the saved copy."""
        if not c.name.strip():
            return None
        saved = self.find_client(c.name)
        fresh = replace(c, id=saved.id if saved else (c.id or new_id()), name=c.name.strip())
        if saved is not None and saved == fresh:
            return saved
        self.clients[fresh.id] = fresh
        self.save_clients()
        return fresh
