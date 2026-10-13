"""A saved client, on the right: their name, how to reach them, the code in their invoice numbers, and every
invoice you've made them (click one to open it).

Every part folds away (Contact, Invoice Numbers, Invoices), each fold remembered and, when folded, saying
what's inside. Invoice Numbers shows only while one of your profiles counts numbers per client. Edits go into
the panel's own copy and fire `changed` once the client can be kept (a name, and not another client's); the
window saves it, and drafts billed to them follow. Invoices you already sent keep what they said.

Across the bottom: Save Client while you're making a new client (it's kept as you type all the same, so
nothing's lost if you click away), then New Invoice once it's saved.
"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QLineEdit, QWidget

from saldo.core import billing, dates, document, money, numbering
from saldo.core.model import Client, Invoice
from saldo.core.store import Library
from saldo.ui.components.widgets import (
    ElidedLabel,
    Section,
    TextBox,
    TitleEdit,
    hbox,
    hint,
    set_tone,
    vbox,
)
from saldo.ui.panels.base import DetailsBase
from saldo.ui.style import tokens
from saldo.ui.window.common import STATUS_WORDS


class InvoiceLine(QFrame):
    """One of the client's invoices: its number and date, its status, its amount. Click to open it."""

    clicked = Signal(str)

    def __init__(self, inv: Invoice, currency: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.inv_id = inv.id
        self.setObjectName("InvoiceLine")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Open this invoice")
        lay = hbox(self, (tokens.SPACE_3, tokens.SPACE_2, tokens.SPACE_3, tokens.SPACE_2), tokens.SPACE_2)
        words = vbox(spacing=0)
        number = ElidedLabel(inv.number or "No number")
        number.setObjectName("ItemTitle")
        when = ElidedLabel(
            " · ".join(x for x in (dates.fmt(dates.parse(inv.issued)), inv.project.strip()) if x)
        )
        when.setObjectName("ItemAmount")
        words.addWidget(number)
        words.addWidget(when)
        lay.addLayout(words, 1)
        tone = document.status_of(inv)
        status = QLabel()
        status.setObjectName("LineStatus")
        set_tone(status, tone, STATUS_WORDS[tone])
        lay.addWidget(status)
        amount = QLabel(money.fmt(billing.totals(inv).total, currency))
        amount.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(amount)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.inv_id)
        super().mousePressEvent(e)


class ClientPanel(DetailsBase):
    TITLE = "Client"
    KEY = "client"
    # the fold-away groups, top to bottom: key -> (title, open the first time)
    GROUPS = {
        "contact": ("Contact", True),
        "numbers": ("Invoice Numbers", True),
        "invoices": ("Invoices", True),
    }

    changed = Signal(object)  # Client, ready to keep
    save_wanted = Signal()  # Save Client, under a new client
    open_invoice = Signal(str)  # invoice id
    new_invoice_wanted = Signal(str)  # client id
    delete_wanted = Signal(str)

    def __init__(self, lib: Library, parent: QWidget | None = None):
        super().__init__(parent)
        self.lib = lib
        self.c: Client | None = None  # the panel's own copy; the library's is replaced when it's saved
        self.fresh = False  # a new client, not kept until it has a name
        self.making = False  # a new client, until Save Client (or another client opens)
        g = self.groups
        self.more.setToolTip("New invoice, delete")
        self.save_btn = self.footer_button("Save Client", "check")
        self.save_btn.setToolTip("Keep this client, to bill them now or pick them under Bill To")
        self.save_btn.clicked.connect(self.save_wanted.emit)
        self.new_inv = self.footer_button("New Invoice", "plus")
        self.new_inv.setToolTip("An invoice billed to this client")
        self.new_inv.clicked.connect(lambda: self.c and self.new_invoice_wanted.emit(self.c.id))
        self.menu_action("plus", "New Invoice", lambda: self.c and self.new_invoice_wanted.emit(self.c.id))
        self.menu_action("", "-", None)
        self.menu_action("trash", "Delete Client…", lambda: self.c and self.delete_wanted.emit(self.c.id))

        self.name = TitleEdit()  # the client's name as the panel's title
        self.name.setPlaceholderText("Company or person")
        self.form_lay.insertWidget(0, self.name)
        self.name_hint = hint("")
        self.form_lay.insertWidget(1, self.name_hint)

        sec = Section("Attention")
        self.contact = QLineEdit()
        self.contact.setPlaceholderText("Contact person (optional)")
        sec.add(self.contact)
        g["contact"].add(sec)
        sec = Section("Email")
        self.email = QLineEdit()
        self.email.setPlaceholderText("Where invoices go (optional)")
        sec.add(self.email)
        g["contact"].add(sec)
        sec = Section("Address")
        self.address = TextBox("Street\nCity, State ZIP")
        sec.add(self.address)
        g["contact"].add(sec)

        sec = Section("Code")
        self.code = QLineEdit()
        self.code.setMaxLength(8)
        self.code.setFixedWidth(tokens.NUM_FIELD_W)
        sec.add(self.code)
        g["numbers"].add(sec)
        g["numbers"].add(hint("Goes in invoice numbers that count per client, like JLF-NRTH-2026-001."))

        # what they owe and what you've billed them, then each invoice
        self.sums = QWidget()
        sl = hbox(self.sums, 0, tokens.SPACE_5)
        self.sum_values: dict[str, QLabel] = {}
        self.sum_boxes: dict[str, QWidget] = {}
        for key, label in (("unpaid", "Unpaid"), ("overdue", "Overdue"), ("billed", "Billed")):
            box = QWidget()
            bl = vbox(box, 0, 0)
            k = QLabel(label)
            k.setObjectName("TotalLabel")
            v = QLabel()
            v.setObjectName("TotalValue")
            bl.addWidget(k)
            bl.addWidget(v)
            sl.addWidget(box)
            self.sum_values[key] = v
            self.sum_boxes[key] = box
        sl.addStretch(1)
        self.sum_values["overdue"].setProperty("tone", "overdue")
        g["invoices"].add(self.sums)
        self.lines = QWidget()
        self.lines_lay = vbox(self.lines, 0, tokens.SPACE_1)
        g["invoices"].add(self.lines)
        self.no_invoices = hint("No invoices yet. New Invoice starts one billed to them.")
        g["invoices"].add(self.no_invoices)

        self.name.textEdited.connect(lambda t: self._set("name", t))
        self.contact.textEdited.connect(lambda t: self._set("contact", t))
        self.email.textEdited.connect(lambda t: self._set("email", t))
        self.address.edited.connect(lambda: self._set("address", self.address.text()))
        self.code.textEdited.connect(lambda t: self._set("code", numbering.clean_code(t)))
        self.form.hide()

    # ------------------------------------------------------------------ loading
    def load(self, c: Client, fresh: bool = False) -> None:
        self._loading = True
        self.c = replace(c)
        self.fresh = fresh
        self.making = fresh
        self.show_form()
        self.name.setText(c.name)
        self.contact.setText(c.contact)
        self.email.setText(c.email)
        self.address.set_text(c.address)
        self.code.setText(c.code)
        self.groups["numbers"].setVisible(any(b.number_style != "year" for b in self.lib.businesses.values()))
        self._loading = False
        self._check()
        self.refresh_invoices()

    def kept(self) -> None:
        """A new client was just saved (it had its name): now it can have invoices."""
        self.fresh = False
        self._check()
        self.refresh_invoices()

    def saved(self) -> None:
        """Save Client: done making this one. New Invoice takes its place across the bottom."""
        self.making = False
        self._check()

    def refresh_invoices(self) -> None:
        """The client's invoices and what they add up to (after any invoice changes)."""
        while self.lines_lay.count():
            w = self.lines_lay.takeAt(0).widget()
            if w is not None:
                w.setParent(None)
        invoices = [] if self.c is None or self.fresh else self.lib.invoices_by_client().get(self.c.id, [])
        today = dates.today()
        cur = next((b.currency for b in self.lib.businesses.values() if b.currency), "$")
        sums = {k: money.ZERO for k in self.sum_values}
        for inv in invoices:
            b = self.lib.businesses.get(inv.business_id)
            line = InvoiceLine(inv, (b.currency if b else "") or cur)
            line.clicked.connect(lambda i: self.later(lambda: self.open_invoice.emit(i)))
            self.lines_lay.addWidget(line)
            t = billing.totals(inv)
            st = document.status_of(inv, today)
            sums["billed"] += t.total
            if st in ("sent", "overdue"):
                sums["unpaid"] += t.balance
            if st == "overdue":
                sums["overdue"] += t.balance
        for k, v in sums.items():
            self.sum_values[k].setText(money.fmt(v, cur))
        self.sums.setVisible(bool(invoices))
        self.sum_boxes["overdue"].setVisible(bool(sums["overdue"]))  # only when something is
        self.no_invoices.setVisible(not invoices)
        n = len(invoices)
        owed = f" · {money.fmt(sums['unpaid'], cur)} unpaid" if sums["unpaid"] else ""
        self.groups["invoices"].set_summary(f"{n} {'invoice' if n == 1 else 'invoices'}{owed}" if n else "")

    # ------------------------------------------------------------------ editing
    def can_save(self) -> bool:
        """A client is kept once it has a name that isn't another client's."""
        return self.c is not None and bool(self.c.name.strip()) and self._taken() is None

    def _taken(self) -> Client | None:
        other = self.lib.find_client(self.c.name) if self.c is not None else None
        return other if other is not None and other.id != self.c.id else None

    def _check(self) -> None:
        """Say what's keeping the client from being saved, if anything; and what each folded group holds."""
        c = self.c
        if c is None:
            return
        other = self._taken()
        if not c.name.strip():
            text = "Type a name to save this client." if self.fresh else "A client needs a name to be saved."
        elif other is not None:
            text = f"{other.name} is already one of your clients."
        else:
            text = ""
        self.name_hint.setText(text)
        self.name_hint.setVisible(bool(text))
        self.code.setPlaceholderText(numbering.client_code(c.name))
        self.save_btn.setVisible(self.making)
        self.save_btn.setEnabled(self.can_save())
        self.new_inv.setVisible(not self.making)
        self.new_inv.setEnabled(not self.fresh)
        g = self.groups
        g["contact"].set_summary(c.email.strip() or c.contact.strip())
        g["numbers"].set_summary(c.code or numbering.client_code(c.name))

    def _set(self, key: str, value) -> None:
        if self._loading or self.c is None:
            return
        setattr(self.c, key, value)
        self._check()
        if self.can_save():
            self.changed.emit(self.c)
