"""What Saldo keeps: businesses (you), clients, and invoices. Saved as JSON.

Every field has a default, and from_dict() ignores keys it doesn't know and fills in ones that are
missing, so files from older or newer versions of Saldo always open. Amounts are kept as the text
you typed ("1500", "1,500.00") and turned into exact decimals by core/money.py.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from typing import Any, TypeVar

T = TypeVar("T")

STATUSES = ("draft", "sent", "paid")
TERMS_DAYS = (0, 7, 15, 30, 45, 60)
NUMBER_STYLES = ("year", "client", "client_only")  # JLF-2026-001 / JLF-NRTH-2026-001 / NRTH-2026-001


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _from(cls: type[T], data: Any) -> T:
    """Build a dataclass from a dict, keeping only known fields (wrong types fall back to the default)."""
    if not isinstance(data, dict):
        return cls()
    defaults = cls()
    kwargs = {}
    for f in fields(cls):
        if f.name not in data:
            continue
        value = data[f.name]
        default = getattr(defaults, f.name)
        if isinstance(default, bool):
            kwargs[f.name] = bool(value)
        elif isinstance(default, int):
            try:
                kwargs[f.name] = int(value)
            except (TypeError, ValueError):
                continue
        elif isinstance(default, str):
            kwargs[f.name] = "" if value is None else str(value)
        else:
            kwargs[f.name] = value
    return cls(**kwargs)


@dataclass
class Look:
    """How a business's invoices look. Keys refer to core/looks.py."""

    # kept from older versions, which offered type styles; read and saved as they were, but the paper is
    # always set in Inter now
    type_style: str = "modern"
    heading_font: str = ""
    body_font: str = ""
    heading_caps: bool = True
    color: str = "turquoise"  # a looks.COLORS key, or "custom" (an exact color from an older Saldo)
    custom_color: str = "#284B63"
    header: str = "clean"  # "clean" or "band"
    logo: str = ""  # a file name inside paths.logos_dir()
    logo_size: str = "medium"  # small / medium / large
    name_with_logo: bool = True  # print the business name next to the logo
    paper: str = "letter"  # letter / a4

    @classmethod
    def from_dict(cls, data: Any) -> Look:
        look = _from(cls, data)
        if not isinstance(data, dict) or "color" not in data:
            look.color = "ink"  # saved without a color: the one older versions used, so it looks as it did
        return look


@dataclass
class Business:
    """You: the name, addresses and defaults that go on every invoice you send."""

    id: str = field(default_factory=new_id)
    name: str = ""
    tagline: str = ""
    address: str = ""
    mail_address: str = ""  # where checks go, if not the address above
    email: str = ""
    phone: str = ""
    website: str = ""
    prefix: str = ""  # invoice numbers: PREFIX-2026-001
    number_style: str = "year"  # a NUMBER_STYLES key: one count for everyone, or one per client
    currency: str = "$"
    terms_days: int = 15
    payment: str = ""
    terms: str = ""
    note: str = ""
    tax_rate: str = ""
    look: Look = field(default_factory=Look)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Any) -> Business:
        b = _from(cls, data)
        b.look = Look.from_dict(data.get("look") if isinstance(data, dict) else None)
        if b.number_style not in NUMBER_STYLES:
            b.number_style = "year"
        if not b.id:
            b.id = new_id()
        return b


@dataclass
class Client:
    """Who you're billing. Invoices keep their own copy: drafts follow edits to the saved client,
    sent and paid invoices keep what they said."""

    id: str = field(default_factory=new_id)
    name: str = ""
    contact: str = ""
    address: str = ""
    email: str = ""
    code: str = ""  # in invoice numbers that count per client (JLF-NRTH-2026-001); blank = made from the name

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Any) -> Client:
        c = _from(cls, data)
        if not c.id:
            c.id = new_id()
        return c


@dataclass
class LineItem:
    description: str = ""
    details: str = ""
    qty: str = "1"
    rate: str = ""

    def is_blank(self) -> bool:
        return not (self.description.strip() or self.details.strip() or self.rate.strip())

    @classmethod
    def from_dict(cls, data: Any) -> LineItem:
        return _from(cls, data)


@dataclass
class Invoice:
    id: str = field(default_factory=new_id)
    business_id: str = ""
    number: str = ""
    auto_number: bool = False  # Saldo picked the number (a draft's then follows its profile and client)
    client: Client = field(default_factory=Client)
    issued: str = ""  # YYYY-MM-DD
    terms_days: int = 15
    project: str = ""
    work_dates: str = ""  # free text: "Sep 26–27, 2026"
    delivered: str = ""  # YYYY-MM-DD, or "" when not shown
    items: list[LineItem] = field(default_factory=lambda: [LineItem()])
    discount: str = ""
    deposit: str = ""
    tax_rate: str = ""
    payment: str = ""
    terms: str = ""
    note: str = ""
    status: str = "draft"
    sent_on: str = ""
    paid_on: str = ""
    created: str = field(default_factory=now_iso)
    updated: str = field(default_factory=now_iso)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Any) -> Invoice:
        inv = _from(cls, data)
        if not isinstance(data, dict):
            return inv
        inv.client = Client.from_dict(data.get("client"))
        raw = data.get("items")
        inv.items = [LineItem.from_dict(i) for i in raw] if isinstance(raw, list) else []
        if not inv.items:
            inv.items = [LineItem()]
        if inv.status not in STATUSES:
            inv.status = "draft"
        if not inv.id:
            inv.id = new_id()
        return inv
