"""The invoice you picked, on the right: everything on it, top to bottom in the order it reads.

Every part folds away (From && Bill To, Invoice, Project, Line Items, Adjustments, Payment && Terms), each
fold remembered and, when folded, saying what's inside. From picks one of your profiles and Bill To one of
your saved clients, each with Edit… beside it. Line items fold to one row each, and only one is open at a
time, so a long list stays tidy. Edits go straight into the Invoice and fire `changed`; the window saves.
The page itself opens in its own window (Invoice…, across the bottom).
"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QDate, QPoint, Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QLabel, QLineEdit, QMenu, QPushButton, QToolButton, QWidget

from cobro.core import dates, document, money
from cobro.core.log import get_logger
from cobro.core.model import STATUSES, TERMS_DAYS, Business, Client, Invoice, LineItem
from cobro.core.store import Library
from cobro.ui.components.lift import Grip, StackLift
from cobro.ui.components.widgets import (
    ElidedLabel,
    IconLabel,
    MoneyField,
    Section,
    TextBox,
    ToggleRow,
    add_chip,
    combo,
    date_field,
    from_qdate,
    hbox,
    icon_button,
    picker,
    qty_field,
    repolish,
    section_label,
    set_combo,
    to_qdate,
    vbox,
)
from cobro.ui.panels.base import DetailsBase
from cobro.ui.style import theme, tokens

log = get_logger(__name__)

ADD_BUSINESS = "__add__"
NEW_CLIENT = "__new__"
THIS_CLIENT = "__this__"  # a client on this invoice that isn't saved (deleted, or from an older Cobro)
STATUS_LABELS = {"draft": "Draft", "sent": "Sent", "paid": "Paid", "overdue": "Overdue"}
STATUS_TIPS = {
    "draft": "Not sent yet",
    "sent": "Sent and waiting to be paid; Overdue once it's past due",
    "paid": "The money's in",
}


# the adjustments you add to an invoice: key (an Invoice field) -> label
ADJUSTMENTS = {"discount": "Discount", "deposit": "Deposit Paid", "tax_rate": "Sales Tax %"}
ADD_LABELS = {"discount": "Discount", "deposit": "Deposit", "tax_rate": "Sales Tax"}


class _Part(Section):
    """An adjustment on the invoice (Discount, Deposit Paid, Sales Tax %). It shows when it holds something or
    you add it; an empty one has an × to take it off again."""

    removed = Signal(str)

    def __init__(self, key: str, title: str, field: QWidget, parent: QWidget | None = None):
        super().__init__("", parent)
        self.key = key
        head = hbox(spacing=tokens.SPACE_1)
        head.addWidget(section_label(title))
        head.addStretch(1)
        self.x = icon_button("x", f"Take {title.replace(' %', '')} off this invoice")
        self.x.clicked.connect(lambda: self.removed.emit(self.key))
        head.addWidget(self.x)
        self.lay.addLayout(head)
        self.lay.addWidget(field)
        self.field = field


class _ItemHead(QFrame):
    clicked = Signal()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)


class LineEditor(QFrame):
    """One line item: a header row (what it is, its amount, ⋯) that folds the fields under it away.
    Duplicate, Move and Remove live in the ⋯ menu, so nothing is removed by a single stray click."""

    changed = Signal()
    open_wanted = Signal(object)  # self
    remove_wanted = Signal(object)
    duplicate_wanted = Signal(object)
    move_wanted = Signal(object, int)  # self, -1 (up) or +1 (down)
    drag_started = Signal(object, QPoint)  # self, where the pointer is (global)
    drag_moved = Signal(QPoint)
    drag_ended = Signal(bool)  # True: Esc (put it back)

    def __init__(self, item: LineItem, currency: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ItemBox")
        self.item = item
        self.currency = currency
        lay = vbox(self, 0, 0)

        self.head = _ItemHead()
        self.head.setCursor(Qt.CursorShape.PointingHandCursor)
        hl = hbox(self.head, (tokens.SPACE_1, tokens.SPACE_2, tokens.SPACE_2, tokens.SPACE_2), tokens.SPACE_1)
        self.grip = Grip()  # drag it to reorder (with two or more line items)
        self.grip.pressed.connect(lambda pos: self.drag_started.emit(self, pos))
        self.grip.moved.connect(lambda pos: self.drag_moved.emit(pos))
        self.grip.released.connect(lambda cancelled: self.drag_ended.emit(cancelled))
        self.chevron = IconLabel("chevron-right")
        self.title = ElidedLabel()
        self.title.setObjectName("ItemTitle")
        self.amount = QLabel()
        self.amount.setObjectName("ItemAmount")
        self.more = icon_button("more", "Duplicate, move or remove")
        self.more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        m = QMenu(self.more)
        # wait for the menu to close before the list changes under it
        m.addAction(theme.menu_icon("copy"), "Duplicate", lambda: self._later(self.duplicate_wanted, self))
        self.act_up = m.addAction(
            theme.menu_icon("arrow-up"), "Move Up", lambda: self._later(self.move_wanted, self, -1)
        )
        self.act_down = m.addAction(
            theme.menu_icon("arrow-down"), "Move Down", lambda: self._later(self.move_wanted, self, 1)
        )
        m.addSeparator()
        m.addAction(theme.menu_icon("trash"), "Remove", lambda: self._later(self.remove_wanted, self))
        self.more.setMenu(m)
        hl.addWidget(self.grip)
        hl.addWidget(self.chevron)
        hl.addSpacing(tokens.SPACE_1)
        hl.addWidget(self.title, 1)
        hl.addWidget(self.amount)
        hl.addWidget(self.more)
        lay.addWidget(self.head)
        self.head.clicked.connect(lambda: self.open_wanted.emit(self))

        self.body = QWidget()
        bl = vbox(self.body, (tokens.SPACE_3, 0, tokens.SPACE_3, tokens.SPACE_3), tokens.SPACE_2)
        self.desc = QLineEdit(item.description)
        self.desc.setPlaceholderText("What you did (Production, Edit…)")
        bl.addWidget(self.desc)
        self.details = TextBox("What's included, dates, hours")
        self.details.set_text(item.details)
        bl.addWidget(self.details)
        self.add_details = add_chip("Details")
        self.add_details.clicked.connect(self._show_details)
        row = hbox()
        row.addWidget(self.add_details)
        row.addStretch(1)
        bl.addLayout(row)
        row = hbox(spacing=tokens.SPACE_2)
        sec = Section("Qty")
        self.qty = qty_field(item.qty)
        self.qty.setToolTip("How many: days, hours or units")
        sec.add(self.qty)
        row.addWidget(sec)
        sec = Section("Rate")
        self.rate = MoneyField(currency)
        self.rate.set_value(item.rate)
        self.rate.setPlaceholderText(money.fmt(money.ZERO, currency))
        self.rate.setToolTip("Price for one. Leave at 0 for something included.")
        sec.add(self.rate)
        row.addWidget(sec, 1)
        bl.addLayout(row)
        lay.addWidget(self.body)

        self.set_open(False)
        self._show_head()
        self.desc.textEdited.connect(lambda t: self._set("description", t))
        self.details.edited.connect(lambda: self._set("details", self.details.text()))
        self.qty.textEdited.connect(lambda t: self._set("qty", t))
        self.rate.textEdited.connect(
            lambda t: self._set("rate", t.replace(self.currency, "").replace(",", "").strip())
        )

    def _later(self, signal, *args) -> None:
        QTimer.singleShot(0, self, lambda: signal.emit(*args))  # dropped if this item is gone by then

    def is_open(self) -> bool:
        return self.body.isVisibleTo(self)

    def _show_details(self) -> None:
        self.details.show()
        self.add_details.hide()
        self.details.setFocus()

    def set_open(self, on: bool) -> None:
        has = bool(self.item.details.strip())  # details show once there are some (or + Details is clicked)
        self.details.setVisible(has)
        self.add_details.setVisible(not has)
        self.body.setVisible(on)
        self.chevron.set_icon("chevron" if on else "chevron-right")
        self.head.setToolTip("Fold away" if on else "Show the details")
        self.setProperty("open", on)
        repolish(self)

    def set_position(self, index: int, count: int) -> None:
        self.act_up.setEnabled(index > 0)
        self.act_down.setEnabled(index < count - 1)
        self.grip.set_active(count > 1)

    def _set(self, key: str, value: str) -> None:
        setattr(self.item, key, value)
        self._show_head()
        self.changed.emit()

    def _show_head(self) -> None:
        name = self.item.description.strip()
        self.title.set_full_text(name or "New Line Item")
        if self.title.property("blank") != (not name):
            self.title.setProperty("blank", not name)
            repolish(self.title)
        if not self.item.rate.strip():
            self.amount.setText("")
        elif money.parse(self.item.rate) == 0:
            self.amount.setText("Included")
        else:
            self.amount.setText(money.fmt(money.line_amount(self.item.qty, self.item.rate), self.currency))


# ---------------------------------------------------------------------------- the panel
class InvoicePanel(DetailsBase):
    TITLE = "Invoice"
    KEY = "invoice"
    # the fold-away groups, top to bottom: key -> (title, open the first time)
    GROUPS = {
        "who": ("From && Bill To", True),
        "invoice": ("Invoice", True),
        "project": ("Project", True),
        "items": ("Line Items", True),
        "adjustments": ("Adjustments", False),
        "payment": ("Payment && Terms", False),
    }

    changed = Signal(object)  # Invoice
    status_changed = Signal(object)  # Invoice
    business_wanted = Signal(str)  # "edit" or "add" (a profile)
    client_wanted = Signal(str)  # "edit" or "new"
    defaults_saved = Signal(object)  # Business
    delete_wanted = Signal(str)  # invoice id
    duplicate_wanted = Signal(str)
    sheet_wanted = Signal(str)  # open the invoice's page

    def __init__(self, lib: Library, parent: QWidget | None = None):
        super().__init__(parent)
        self.lib = lib
        self.inv: Invoice | None = None
        self.items: list[LineEditor] = []
        self._lift: StackLift | None = None  # a line item being dragged
        g = self.groups
        self.sheet = self.footer_button("Invoice…", "receipt")
        self.sheet.setToolTip("The invoice as it prints: Save PDF, Print, Mark as Sent")
        self.sheet.clicked.connect(lambda: self.inv and self.sheet_wanted.emit(self.inv.id))
        self.menu_action("copy", "Duplicate", lambda: self.inv and self.duplicate_wanted.emit(self.inv.id))
        self.menu_action("", "-", None)
        self.menu_action(
            "trash", "Delete Invoice…", lambda: self.inv and self.delete_wanted.emit(self.inv.id)
        )

        # From && Bill To: one of your profiles, one of your clients
        sec = Section("From")
        row = hbox(spacing=tokens.SPACE_2)
        self.business = picker()
        self.edit_business = self._edit_button("Your name, logo, contact details and how you get paid")
        row.addWidget(self.business, 1)
        row.addWidget(self.edit_business)
        sec.add(row)
        g["who"].add(sec)
        sec = Section("Bill To")
        row = hbox(spacing=tokens.SPACE_2)
        self.client = picker("Choose a Client")
        self.client.setToolTip("Your saved clients. New Client… adds one.")
        self.edit_client = self._edit_button("This client's name, contact, address and email")
        row.addWidget(self.client, 1)
        row.addWidget(self.edit_client)
        sec.add(row)
        g["who"].add(sec)

        # Invoice
        row = hbox(spacing=tokens.SPACE_2)
        sec = Section("Status")
        self.status = combo([(k, STATUS_LABELS[k], STATUS_TIPS[k]) for k in STATUSES], "draft")
        sec.add(self.status)
        row.addWidget(sec, 1)
        self.paid_sec = Section("Paid On")
        self.paid_on = date_field()
        self.paid_sec.add(self.paid_on)
        row.addWidget(self.paid_sec, 1)
        g["invoice"].add(row)
        row = hbox(spacing=tokens.SPACE_2)
        sec = Section("Invoice No.")
        self.number = QLineEdit()
        sec.add(self.number)
        row.addWidget(sec, 1)
        sec = Section("Issued")
        self.issued = date_field()
        sec.add(self.issued)
        row.addWidget(sec, 1)
        g["invoice"].add(row)
        sec = Section("Payment Terms")
        self.terms_days = combo([(str(d), dates.terms_label(d), "") for d in TERMS_DAYS], "15")
        sec.add(self.terms_days)
        g["invoice"].add(sec)

        # Project
        self.project = QLineEdit()
        self.project.setPlaceholderText("Project name (optional)")
        self.work_dates = QLineEdit()
        self.work_dates.setPlaceholderText("Shoot or work dates, like Sep 26–27, 2026")
        self.show_delivered = ToggleRow("Show Delivery Date")
        self.show_delivered.setToolTip("Prints when the final files were delivered")
        self.delivered = date_field()
        sec = Section()
        for w in (self.project, self.work_dates, self.show_delivered, self.delivered):
            sec.add(w)
        g["project"].add(sec)

        # Line items
        self.items_box = QWidget()
        self.items_lay = vbox(self.items_box, 0, tokens.SPACE_2)
        g["items"].add(self.items_box)
        add_row = hbox()
        self.add_item = add_chip("Add Line Item")
        add_row.addWidget(self.add_item)
        add_row.addStretch(1)
        g["items"].add(add_row)

        # Adjustments: only the ones this invoice has (or you add)
        self.discount = MoneyField()
        self.deposit = MoneyField()
        self.tax = QLineEdit()
        self.tax.setPlaceholderText("8.25")
        self.parts: dict[str, _Part] = {}
        self.add_parts: dict[str, QPushButton] = {}
        self._added: set[str] = set()  # added to this invoice but still empty
        for key, field in (("discount", self.discount), ("deposit", self.deposit), ("tax_rate", self.tax)):
            part = _Part(key, ADJUSTMENTS[key], field)
            part.removed.connect(self._remove_part)
            self.parts[key] = part
            g["adjustments"].add(part)
        add_row = hbox(spacing=tokens.SPACE_2)
        for key in ADJUSTMENTS:
            b = add_chip(ADD_LABELS[key])
            b.clicked.connect(lambda _c=False, k=key: self._add_part(k))
            self.add_parts[key] = b
            add_row.addWidget(b)
        add_row.addStretch(1)
        self.add_row = QWidget()
        self.add_row.setLayout(add_row)
        g["adjustments"].add(self.add_row)

        # Payment && Terms
        sec = Section("How to Pay")
        self.payment = TextBox("", tokens.TEXT_BOX_TALL)
        sec.add(self.payment)
        g["payment"].add(sec)
        sec = Section("Terms")
        self.terms = TextBox("", tokens.TEXT_BOX_TALL)
        self.terms.setToolTip("The due-date line is added on top automatically")
        sec.add(self.terms)
        g["payment"].add(sec)
        sec = Section("Closing Note")
        self.note = QLineEdit()
        sec.add(self.note)
        g["payment"].add(sec)
        row = hbox()
        self.reset_pay = self._ghost(
            "Use Profile Defaults", "Put back the payment text, terms and note from your profile"
        )
        self.save_pay = self._ghost(
            "Make These the Defaults", "New invoices will start with this payment text, terms and note"
        )
        row.addWidget(self.reset_pay)
        row.addWidget(self.save_pay)
        row.addStretch(1)
        g["payment"].add(row)

        self._connect()
        self.form.hide()

    @staticmethod
    def _edit_button(tip: str):
        from PySide6.QtWidgets import QPushButton

        b = QPushButton("Edit…")
        b.setToolTip(tip)
        return b

    @staticmethod
    def _ghost(text: str, tip: str):
        from PySide6.QtWidgets import QPushButton

        b = QPushButton(text)
        b.setObjectName("Ghost")
        b.setToolTip(tip)
        return b

    # ------------------------------------------------------------------ wiring
    def _connect(self) -> None:
        def text(field: str):
            return lambda t: self._edit(field, t)

        self.client.activated.connect(self._client_picked)
        self.edit_client.clicked.connect(lambda: self.client_wanted.emit("edit"))
        self.edit_business.clicked.connect(lambda: self.business_wanted.emit("edit"))
        self.business.activated.connect(self._business_picked)
        self.number.textEdited.connect(self._number_typed)
        self.issued.dateChanged.connect(self._issued_changed)
        self.terms_days.currentIndexChanged.connect(
            lambda _i: self._edit("terms_days", int(self.terms_days.currentData()))
        )
        self.project.textEdited.connect(text("project"))
        self.work_dates.textEdited.connect(text("work_dates"))
        self.show_delivered.toggled.connect(self._toggle_delivered)
        self.delivered.dateChanged.connect(lambda q: self._edit("delivered", from_qdate(q)))
        self.add_item.clicked.connect(self._add_item)
        self.discount.textEdited.connect(lambda t: (self._edit("discount", self._plain(t)), self._parts()))
        self.deposit.textEdited.connect(lambda t: (self._edit("deposit", self._plain(t)), self._parts()))
        self.tax.textEdited.connect(lambda t: (self._edit("tax_rate", t), self._parts()))
        self.payment.edited.connect(lambda: self._edit("payment", self.payment.text()))
        self.terms.edited.connect(lambda: self._edit("terms", self.terms.text()))
        self.note.textEdited.connect(text("note"))
        self.reset_pay.clicked.connect(self._reset_pay)
        self.save_pay.clicked.connect(self._save_pay)
        self.status.currentIndexChanged.connect(self._status_picked)
        self.paid_on.dateChanged.connect(lambda q: self._edit("paid_on", from_qdate(q)))

    def _plain(self, t: str) -> str:
        return t.replace(self._currency(), "").replace(",", "").strip()

    # ------------------------------------------------------------------ loading
    def current_business(self) -> Business | None:
        return self.lib.businesses.get(self.inv.business_id) if self.inv else None

    def load(self, inv: Invoice) -> None:
        self._loading = True
        self.inv = inv
        self.show_form()
        cur = self._currency()
        for f in (self.discount, self.deposit):
            f.currency = cur
        set_combo(self.status, inv.status)
        self.paid_on.setDate(to_qdate(inv.paid_on))
        self.paid_sec.setVisible(inv.status == "paid")
        self.refresh_businesses()
        self.refresh_clients()
        self.number.setText(inv.number)
        self.issued.setDate(to_qdate(inv.issued))
        set_combo(self.terms_days, str(inv.terms_days))
        if self.terms_days.currentData() != str(inv.terms_days):
            self.terms_days.addItem(dates.terms_label(inv.terms_days), str(inv.terms_days))
            set_combo(self.terms_days, str(inv.terms_days))
        self.project.setText(inv.project)
        self.work_dates.setText(inv.work_dates)
        self.show_delivered.setChecked(bool(inv.delivered))
        self.delivered.setDate(to_qdate(inv.delivered))
        self.delivered.setVisible(bool(inv.delivered))
        self.discount.set_value(inv.discount)
        self.deposit.set_value(inv.deposit)
        self.tax.setText(inv.tax_rate)
        self._added = set()
        self._parts()
        self.payment.set_text(inv.payment)
        self.terms.set_text(inv.terms)
        self.note.setText(inv.note)
        self._rebuild_items()
        self._summaries()
        self._loading = False

    def refresh_businesses(self) -> None:
        c = self.business
        c.blockSignals(True)
        c.clear()
        for b in sorted(self.lib.businesses.values(), key=lambda b: b.name.casefold()):
            c.addItem(b.name or "Untitled Profile", b.id)
        c.insertSeparator(c.count())
        c.addItem("Add a Profile…", ADD_BUSINESS)
        if self.inv:
            c.setCurrentIndex(max(0, c.findData(self.inv.business_id)))
        c.blockSignals(False)

    def _client_key(self) -> str | None:
        """Which Bill To entry this invoice's client is: a saved client, THIS_CLIENT, or None (nobody yet)."""
        c = self.inv.client
        saved = self.lib.match_client(c)
        if saved is not None:
            return saved.id
        return THIS_CLIENT if c.name.strip() else None

    def refresh_clients(self) -> None:
        if self.inv is None:
            return
        box = self.client
        box.blockSignals(True)
        box.clear()
        key = self._client_key()
        if key == THIS_CLIENT:
            box.addItem(self.inv.client.name.strip(), THIS_CLIENT)
            box.setItemData(
                0, "Only on this invoice. Edit… saves it for next time.", Qt.ItemDataRole.ToolTipRole
            )
        for c in sorted(self.lib.clients.values(), key=lambda c: c.name.casefold()):
            box.addItem(c.name or "Unnamed Client", c.id)
        if box.count():
            box.insertSeparator(box.count())
        box.addItem("New Client…", NEW_CLIENT)
        box.setCurrentIndex(box.findData(key) if key else -1)
        box.blockSignals(False)
        self.edit_client.setVisible(key is not None)
        self._summaries()

    def _currency(self) -> str:
        b = self.current_business()
        return (b.currency if b else "$") or "$"

    def _rebuild_items(self) -> None:
        if self._lift is not None:  # never refill the list under a line item being dragged
            self._lift.finish(cancelled=True)
            self._lift = None
        for ed in self.items:
            ed.setParent(None)
            ed.deleteLater()
        self.items = []
        cur = self._currency()
        for it in self.inv.items:
            self._add_editor(it, cur)
        # a single item, or one still being filled in, starts open; a finished list starts folded
        blank = next((ed for ed in self.items if ed.item.is_blank()), None)
        keep = self.items[0] if len(self.items) == 1 else blank
        for ed in self.items:
            ed.set_open(ed is keep)
        self._positions()

    def _add_editor(self, it: LineItem, currency: str, at: int | None = None) -> LineEditor:
        ed = LineEditor(it, currency)
        ed.changed.connect(self._changed)
        ed.open_wanted.connect(self._toggle_item)
        ed.remove_wanted.connect(self._remove_item)
        ed.duplicate_wanted.connect(self._duplicate_item)
        ed.move_wanted.connect(self._move_item)
        ed.drag_started.connect(self._drag_started)
        ed.drag_moved.connect(self._drag_moved)
        ed.drag_ended.connect(self._drag_ended)
        pos = len(self.items) if at is None else at
        self.items_lay.insertWidget(pos, ed)
        self.items.insert(pos, ed)
        return ed

    def _positions(self) -> None:
        for i, ed in enumerate(self.items):
            ed.set_position(i, len(self.items))

    def _open_only(self, ed: LineEditor | None, focus: bool = False) -> None:
        """One line item open at a time keeps a long list tidy."""
        for other in self.items:
            other.set_open(other is ed)
        if ed is not None:
            if focus:
                ed.desc.setFocus()
            if self.scroll is not None:
                QTimer.singleShot(0, ed, lambda: self.scroll.ensureWidgetVisible(ed))

    def _toggle_item(self, ed: LineEditor) -> None:
        self._open_only(None if ed.is_open() else ed)

    def _add_item(self) -> None:
        if self.inv is None:
            return
        it = LineItem()
        self.inv.items.append(it)
        ed = self._add_editor(it, self._currency())
        self._positions()
        self._open_only(ed, focus=True)
        self._changed()

    def _duplicate_item(self, ed: LineEditor) -> None:
        if self.inv is None or ed not in self.items:
            return
        i = self.items.index(ed) + 1
        it = replace(ed.item)
        self.inv.items.insert(i, it)
        copy = self._add_editor(it, self._currency(), i)
        self._positions()
        self._open_only(copy)
        self._changed()

    def _move_item(self, ed: LineEditor, step: int) -> None:
        if self.inv is not None and ed in self.items:
            self._move_to(ed, self.items.index(ed) + step)

    def _move_to(self, ed: LineEditor, j: int) -> None:
        """Put a line item in place `j` (Move Up / Move Down, or dropped after a drag)."""
        if self.inv is None or ed not in self.items or not 0 <= j < len(self.items):
            return
        i = self.items.index(ed)
        if i == j:
            return
        # self.items and self.inv.items are always in the same order
        self.items.insert(j, self.items.pop(i))
        self.inv.items.insert(j, self.inv.items.pop(i))
        self.items_lay.removeWidget(ed)
        self.items_lay.insertWidget(j, ed)
        self._positions()
        self._changed()

    # ------------------------------------------------------------------ dragging a line item by its grip
    def _drag_started(self, ed: LineEditor, pos: QPoint) -> None:
        if self.inv is None or len(self.items) < 2 or self._lift is not None:
            return
        if ed.is_open():  # it travels folded, like the rest
            ed.set_open(False)
            self.items_box.layout().activate()
        self._lift = StackLift(
            self.items_box, list(self.items), ed, pos, self.items_lay.spacing(), self.scroll
        )

    def _drag_moved(self, pos: QPoint) -> None:
        if self._lift is not None:
            self._lift.move_to(pos)

    def _drag_ended(self, cancelled: bool) -> None:
        lift, self._lift = self._lift, None
        if lift is None:
            return
        j = lift.finish(cancelled)
        if j is not None:
            self._move_to(lift.moving, j)

    def _remove_item(self, ed: LineEditor) -> None:
        if self.inv is None or ed not in self.items:
            return
        i = self.items.index(ed)
        del self.inv.items[i]
        self.items.pop(i)
        ed.setParent(None)
        ed.deleteLater()
        if not self.inv.items:
            self.inv.items.append(LineItem())
            self._open_only(self._add_editor(self.inv.items[0], self._currency()))
        self._positions()
        self._changed()

    # ------------------------------------------------------------------ adjustments you add
    def _has(self, key: str) -> bool:
        return self.inv is not None and bool(str(getattr(self.inv, key)).strip())

    def _parts(self) -> None:
        """Show the adjustments this invoice has (or you added); offer the rest as + Discount and so on."""
        missing = 0
        for key, part in self.parts.items():
            shown = self._has(key) or key in self._added
            part.setVisible(shown)
            part.x.setVisible(shown and not self._has(key))
            self.add_parts[key].setVisible(not shown)
            missing += not shown
        self.add_row.setVisible(missing > 0)

    def _add_part(self, key: str) -> None:
        self._added.add(key)
        self._parts()
        self.parts[key].field.setFocus()

    def _remove_part(self, key: str) -> None:
        if self._has(key):
            return
        self._added.discard(key)
        self._parts()

    # ------------------------------------------------------------------ edits
    def _changed(self) -> None:
        if self.inv is not None and not self._loading:
            self._summaries()
            self.changed.emit(self.inv)

    def _edit(self, field: str, value) -> None:
        if self.inv is None or self._loading:
            return
        setattr(self.inv, field, value)
        self._changed()

    def _client_picked(self, i: int) -> None:
        """Picked under Bill To: a saved client fills in the invoice; New Client… opens the dialog."""
        if self.inv is None:
            return
        key = self.client.itemData(i)
        if key == NEW_CLIENT:
            self.refresh_clients()  # put the selection back
            self.client_wanted.emit("new")
            return
        saved = self.lib.clients.get(key)
        if saved is not None and self.inv.client != saved:
            self.use_client(saved)

    def use_client(self, c: Client) -> None:
        """Bill this invoice to a saved client (picked here, or just saved in the client dialog)."""
        if self.inv is None:
            return
        self.inv.client = replace(c)
        self._renumber()
        self.refresh_clients()
        self._changed()

    def _renumber(self) -> None:
        """A draft whose number Cobro picked follows its profile, client and year (see Library.renumber)."""
        if self.lib.renumber(self.inv):
            self._loading, was = True, self._loading
            self.number.setText(self.inv.number)
            self._loading = was

    def _number_typed(self, text: str) -> None:
        if self.inv is None or self._loading:
            return
        self.inv.auto_number = False  # your own number: Cobro leaves it alone from now on
        self._edit("number", text)

    def _issued_changed(self, q: QDate) -> None:
        if self.inv is None or self._loading:
            return
        self.inv.issued = from_qdate(q)
        self._renumber()
        self._changed()

    def _toggle_delivered(self, on: bool) -> None:
        self.delivered.setVisible(on)
        if self.inv is None or self._loading:
            return
        self.inv.delivered = from_qdate(self.delivered.date()) if on else ""
        self._changed()

    def _status_picked(self, _i: int) -> None:
        if self.inv is None or self._loading:
            return
        st = self.status.currentData()
        self.inv.status = st
        today = dates.iso(dates.today())
        if st in ("sent", "paid") and not self.inv.sent_on:
            self.inv.sent_on = today
        if st == "paid":
            if not self.inv.paid_on:
                self.inv.paid_on = today
            self._loading = True
            self.paid_on.setDate(to_qdate(self.inv.paid_on))
            self._loading = False
        else:
            self.inv.paid_on = ""
        self.paid_sec.setVisible(st == "paid")
        self._changed()
        self.status_changed.emit(self.inv)

    def set_status(self, st: str) -> None:
        """From outside (Mark as Sent after saving the PDF)."""
        set_combo(self.status, st)
        self._status_picked(0)

    def _business_picked(self, _i: int) -> None:
        if self.inv is None:
            return
        key = self.business.currentData()
        if key == ADD_BUSINESS:
            self.refresh_businesses()  # put the selection back
            self.business_wanted.emit("add")
            return
        if key and key != self.inv.business_id:
            self.inv.business_id = key
            self.lib.renumber(self.inv)
            self.load(self.inv)
            self._changed()

    def _reset_pay(self) -> None:
        b = self.current_business()
        if self.inv is None or b is None:
            return
        self.inv.payment, self.inv.terms, self.inv.note = b.payment, b.terms, b.note
        self._loading = True
        self.payment.set_text(b.payment)
        self.terms.set_text(b.terms)
        self.note.setText(b.note)
        self._loading = False
        self._changed()

    def _save_pay(self) -> None:
        b = self.current_business()
        if self.inv is None or b is None:
            return
        b.payment, b.terms, b.note = self.inv.payment, self.inv.terms, self.inv.note
        self._summaries()
        self.defaults_saved.emit(b)

    def _summaries(self) -> None:
        """What each group holds, shown on its header while it's folded."""
        if self.inv is None:
            return
        inv, g = self.inv, self.groups
        b = self.current_business()
        who = inv.client.name.strip() or "No client yet"
        g["who"].set_summary(f"{who} · from {b.name}" if b is not None and b.name else who)
        g["invoice"].set_summary(f"{inv.number} · {STATUS_LABELS.get(document.status_of(inv), '')}")
        g["project"].set_summary(inv.project.strip())
        n = sum(1 for it in inv.items if not it.is_blank())
        total = money.fmt(money.totals(inv).subtotal, self._currency())
        g["items"].set_summary(f"{n} {'item' if n == 1 else 'items'} · {total}" if n else "")
        n = sum(1 for v in (inv.discount, inv.deposit, inv.tax_rate) if money.parse(v))
        g["adjustments"].set_summary(f"{n} set" if n else "")
        same = b is not None and (inv.payment, inv.terms, inv.note) == (b.payment, b.terms, b.note)
        g["payment"].set_summary("" if same else "Edited")
        self.reset_pay.setVisible(not same)
        self.save_pay.setVisible(not same)
