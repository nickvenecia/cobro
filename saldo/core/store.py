"""Saving and loading: everything lives as small JSON files in Saldo's data folder.

    businesses.json   your business(es), with their look and defaults
    clients.json      your saved clients (added and edited from Bill To)
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

from saldo.core import dates, numbering
from saldo.core.log import get_logger
from saldo.core.model import Business, Client, Invoice, LineItem, new_id, now_iso
from saldo.core.paths import data_dir

log = get_logger(__name__)

DEFAULT_TERMS = (
    "The work listed above is complete.\n"
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


def write_bytes(path: Path, data: bytes) -> None:
    """Write a file atomically (a copy kept in backups/, say): a temp file in the same folder, then os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
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
    """Everything Saldo knows, loaded from the data folder and saved back file by file."""

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

    @staticmethod
    def client_code(c: Client) -> str:
        """The code a client goes by in invoice numbers (typed, or made from the name)."""
        return numbering.clean_code(c.code) or numbering.client_code(c.name)

    def next_number(
        self, business: Business, year: int | None = None, client: Client | None = None, skip: str = ""
    ) -> str:
        """The next free number for this profile (and client, if it counts per client).
        `skip`: an invoice whose own number doesn't count (it's the one being renumbered)."""
        year = year or dates.today().year
        code = self.client_code(client) if client is not None else ""
        head = numbering.head(business.prefix, code, business.number_style)
        taken = (i.number for i in self.invoices.values() if i.id != skip)
        return numbering.next_number(head, taken, year)

    def renumber(self, inv: Invoice) -> bool:
        """Keep a draft's number in step with its profile, client and year (JLF-NRTH-2026-001), when Saldo
        picked it. Numbers you typed, and invoices already sent or paid, never change. True if it changed."""
        b = self.businesses.get(inv.business_id)
        if b is None or not inv.auto_number or inv.status != "draft":
            return False
        year = (dates.parse(inv.issued) or dates.today()).year
        code = self.client_code(inv.client) if inv.client.name.strip() else ""
        start = f"{numbering.head(b.prefix, code, b.number_style)}-{year}-"
        if inv.number.upper().startswith(start.upper()):
            return False
        inv.number = self.next_number(b, year, inv.client if code else None, skip=inv.id)
        return True

    def new_invoice(self, business: Business, today: date | None = None) -> Invoice:
        today = today or dates.today()
        tax = business.tax_rate
        inv = Invoice(
            business_id=business.id,
            number=self.next_number(business, today.year),
            auto_number=True,
            issued=dates.iso(today),
            terms_days=business.terms_days,
            items=[LineItem()],  # no delivery date: not every job is a delivery (Show Delivery Date adds one)
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
            self.next_number(business, today.year, copy.client if copy.client.name.strip() else None)
            if business
            else numbering.next_number("INV", [], today.year)
        )
        copy.auto_number = True
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

    SNAPSHOTS_KEPT = 30

    def snapshot(self, why: str, invoice_ids: list[str]) -> Path | None:
        """A dated copy of these invoices' files in backups/ before a big change (an AI's edits, say); the
        newest SNAPSHOTS_KEPT copies are kept. None if there was nothing to copy or it couldn't be written."""
        folder = self.root / "backups"
        stamp = time.strftime("%Y-%m-%d-%H%M%S")
        tag = "".join(ch for ch in why.lower() if ch.isalnum() or ch == "-")
        dest = None
        try:
            for inv_id in invoice_ids:
                src = self._inv_dir / f"{inv_id}.json"
                if not src.is_file():
                    continue
                folder.mkdir(parents=True, exist_ok=True)
                dest = folder / f"invoice-{stamp}-{tag}-{inv_id}.json"
                write_bytes(dest, src.read_bytes())
            for old in sorted(folder.glob("invoice-*.json"))[: -self.SNAPSHOTS_KEPT]:
                old.unlink(missing_ok=True)
        except OSError:
            log.warning("couldn't keep a copy of the invoice before %s", why, exc_info=True)
            return None
        return dest

    # ------------------------------------------------------------------ clients
    def find_client(self, name: str) -> Client | None:
        key = name.strip().casefold()
        if not key:
            return None
        return next((c for c in self.clients.values() if c.name.strip().casefold() == key), None)

    def match_client(self, c: Client) -> Client | None:
        """The saved client an invoice's copy belongs to: same id, or else the same name."""
        return self.clients.get(c.id) or self.find_client(c.name)

    def invoices_by_client(self) -> dict[str, list[Invoice]]:
        """Each saved client's invoices, newest first (an invoice's own copy names its client by id, or else
        by name)."""
        found: dict[str, list[Invoice]] = {c_id: [] for c_id in self.clients}
        for inv in self.ordered():
            c = self.match_client(inv.client)
            if c is not None:
                found[c.id].append(inv)
        return found

    def save_client(self, c: Client) -> Client:
        """Add or update a saved client. Drafts billed to them pick up the change; sent and paid
        invoices keep the details they went out with."""
        saved = replace(c, id=c.id or new_id(), name=c.name.strip())
        self.clients[saved.id] = saved
        self.save_clients()
        for inv in self.invoices.values():
            if inv.client.id == saved.id and inv.status == "draft" and inv.client != saved:
                inv.client = replace(saved)
                self.renumber(inv)  # a new code changes the number of a draft that counts per client
                self.save_invoice(inv)
        log.info("saved client %s", saved.name)
        return saved

    def delete_client(self, client_id: str) -> None:
        """Take a client off the list. Invoices keep their own copy, so none of them change."""
        if self.clients.pop(client_id, None) is not None:
            self.save_clients()
