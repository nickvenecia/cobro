"""Step 2, Details: everything on the invoice, top to bottom in the order it reads.

Every part folds away (From && Bill To, Invoice, Project, Line Items, Adjustments, Payment && Terms,
Look), each fold remembered and, when folded, saying what's inside. From picks one of your profiles and
Bill To one of your saved clients, each with Edit… beside it. Line items fold to one row each, and only
one is open at a time, so a long list stays tidy.
Edits go straight into the Invoice (or, for Look, the profile) and fire a signal; the window
saves and redraws the preview.
"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QDate, QLocale, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDateEdit,
    QFontDialog,
    QFrame,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QToolButton,
    QWidget,
)

from ..core import dates, document, money
from ..core.log import get_logger
from ..core.looks import (
    BUNDLED_FONTS,
    COLORS,
    CUSTOM,
    DISPLAY_ONLY,
    HEADERS,
    LOGO_SIZES,
    PAPERS,
    TYPE_STYLES,
    accent_of,
)
from ..core.model import STATUSES, TERMS_DAYS, Business, Client, Invoice, LineItem, Look
from ..core.paths import logos_dir
from ..core.store import Library
from . import theme, tokens
from .widgets import (
    Disclosure,
    ElidedLabel,
    FitScroll,
    Section,
    StepHeader,
    TextBox,
    ToggleRow,
    combo,
    hbox,
    hint,
    repolish,
    set_combo,
    vbox,
)

log = get_logger(__name__)

OTHER_FONT = "__other__"
PICK_COLOR = "__pick__"
ADD_BUSINESS = "__add__"
NEW_CLIENT = "__new__"
THIS_CLIENT = "__this__"  # a client on this invoice that isn't saved (deleted, or from an older Cobro)
STATUS_LABELS = {"draft": "Draft", "sent": "Sent", "paid": "Paid", "overdue": "Overdue"}
# the fold-away groups, top to bottom: key -> (title, open the first time)
GROUPS = {
    "who": ("From && Bill To", True),
    "invoice": ("Invoice", True),
    "project": ("Project", True),
    "items": ("Line Items", True),
    "adjustments": ("Adjustments", False),
    "payment": ("Payment && Terms", False),
    "look": ("Look", False),
}


def date_field() -> QDateEdit:
    d = QDateEdit()
    d.setCalendarPopup(True)
    d.setDisplayFormat("MMM d, yyyy")
    d.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
    d.setCursor(Qt.CursorShape.PointingHandCursor)
    return d


def to_qdate(iso: str) -> QDate:
    d = dates.parse(iso) or dates.today()
    return QDate(d.year, d.month, d.day)


def from_qdate(q: QDate) -> str:
    return f"{q.year():04d}-{q.month():02d}-{q.day():02d}"


def swatch(color: str) -> QIcon:
    size = tokens.SWATCH * 2
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    p.drawEllipse(1, 1, size - 2, size - 2)
    p.end()
    pm.setDevicePixelRatio(2)
    return QIcon(pm)


def icon_button(name: str, tip: str) -> QToolButton:
    b = QToolButton()
    b.setObjectName("IconBtn")
    b.setIcon(theme.icon(name, theme.MUTED, tokens.ICON_SM))
    b.setToolTip(tip)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def picker(placeholder: str = "") -> QComboBox:
    """A dropdown of your own things (profiles, clients) that never widens the panel for a long name."""
    c = QComboBox()
    c.setCursor(Qt.CursorShape.PointingHandCursor)
    c.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    c.setMinimumContentsLength(1)
    c.setPlaceholderText(placeholder)
    return c


# ---------------------------------------------------------------------------- one line item
class _ItemHead(QFrame):
    clicked = Signal()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)


class ItemEditor(QFrame):
    """One line item: a header row (what it is, its amount, ⋯) that folds the fields under it away.
    Duplicate, Move and Remove live in the ⋯ menu, so nothing is removed by a single stray click."""

    changed = Signal()
    open_wanted = Signal(object)  # self
    remove_wanted = Signal(object)
    duplicate_wanted = Signal(object)
    move_wanted = Signal(object, int)  # self, -1 (up) or +1 (down)

    def __init__(self, item: LineItem, currency: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ItemBox")
        self.item = item
        self.currency = currency
        lay = vbox(self, 0, 0)

        self.head = _ItemHead()
        self.head.setCursor(Qt.CursorShape.PointingHandCursor)
        hl = hbox(self.head, (tokens.SPACE_3, tokens.SPACE_2, tokens.SPACE_2, tokens.SPACE_2), tokens.SPACE_2)
        self.chevron = QLabel()
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
        hl.addWidget(self.chevron)
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
        self.details = TextBox("Details (optional)")
        self.details.set_text(item.details)
        bl.addWidget(self.details)
        row = hbox(spacing=tokens.SPACE_2)
        self.qty = QLineEdit(item.qty)
        self.qty.setPlaceholderText("Qty")
        self.qty.setToolTip("Quantity: days, hours or units")
        self.qty.setFixedWidth(tokens.NUM_FIELD_W - tokens.SPACE_5)
        times = QLabel("×")
        times.setObjectName("Muted")
        self.rate = QLineEdit(item.rate)
        self.rate.setPlaceholderText("Rate")
        self.rate.setToolTip("Price for one. Leave at 0 for something included.")
        self.rate.setFixedWidth(tokens.NUM_FIELD_W)
        row.addWidget(self.qty)
        row.addWidget(times)
        row.addWidget(self.rate)
        row.addStretch(1)
        bl.addLayout(row)
        lay.addWidget(self.body)

        self.set_open(True)
        self._show_head()
        self.desc.textEdited.connect(lambda t: self._set("description", t))
        self.details.edited.connect(lambda: self._set("details", self.details.text()))
        self.qty.textEdited.connect(lambda t: self._set("qty", t))
        self.rate.textEdited.connect(lambda t: self._set("rate", t))

    def _later(self, signal, *args) -> None:
        QTimer.singleShot(0, self, lambda: signal.emit(*args))  # dropped if this item is gone by then

    def is_open(self) -> bool:
        return self.body.isVisibleTo(self)

    def set_open(self, on: bool) -> None:
        self.body.setVisible(on)
        self.chevron.setPixmap(
            theme.pixmap("chevron" if on else "chevron-right", tokens.ICON_SM, theme.MUTED)
        )
        self.head.setToolTip("Fold away" if on else "Show the details")
        self.setProperty("open", on)
        repolish(self)

    def set_position(self, index: int, count: int) -> None:
        self.act_up.setEnabled(index > 0)
        self.act_down.setEnabled(index < count - 1)

    def _set(self, key: str, value: str) -> None:
        setattr(self.item, key, value)
        self._show_head()
        self.changed.emit()

    def _show_head(self) -> None:
        name = self.item.description.strip()
        self.title.set_full_text(name or "New line item")
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
class DetailsPanel(QFrame):
    invoice_changed = Signal(object)  # Invoice
    status_changed = Signal(object)  # Invoice
    look_changed = Signal(object)  # Business
    business_wanted = Signal(str)  # "edit" or "add" (a profile)
    client_wanted = Signal(str)  # "edit" or "new"
    defaults_saved = Signal(object)  # Business
    groups_changed = Signal(dict)  # {"adjustments": True, ...}

    def __init__(self, lib: Library, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Details")
        self.setFixedWidth(tokens.DETAILS_W)
        self.lib = lib
        self.inv: Invoice | None = None
        self._loading = False
        self.items: list[ItemEditor] = []

        outer = vbox(self, 0, 0)
        outer.addWidget(StepHeader(2, "Details"))
        self.scroll = FitScroll()
        body = QWidget()
        pad = tokens.SPACE_4
        self.lay = vbox(body, (pad, pad, pad - tokens.SCROLL_GUTTER, pad), tokens.SPACE_3)
        self.scroll.setWidget(body)
        outer.addWidget(self.scroll, 1)

        self._build_empty()
        self._build_form()
        self.lay.addStretch(1)
        self.show_empty("business")

    # ------------------------------------------------------------------ empty states
    def _build_empty(self) -> None:
        self.empty = QWidget()
        lay = vbox(self.empty, (0, tokens.SPACE_5, 0, 0), tokens.SPACE_3)
        self.empty_title = QLabel()
        self.empty_title.setObjectName("EmptyTitle")
        self.empty_title.setWordWrap(True)
        self.empty_text = QLabel()
        self.empty_text.setObjectName("EmptyText")
        self.empty_text.setWordWrap(True)
        self.empty_btn = QPushButton()
        self.empty_btn.setObjectName("Primary")
        row = hbox()
        row.addWidget(self.empty_btn)
        row.addStretch(1)
        lay.addWidget(self.empty_title)
        lay.addWidget(self.empty_text)
        lay.addLayout(row)
        self.lay.addWidget(self.empty)
        self._empty_action = None
        self.empty_btn.clicked.connect(lambda: self._empty_action and self._empty_action())

    def show_empty(self, kind: str, action=None) -> None:
        """kind: "business" (no profile set up yet) or "invoice" (no invoice picked)."""
        self.inv = None
        self.form.hide()
        self.empty.show()
        self._empty_action = action
        if kind == "business":
            self.empty_title.setText("Start with your profile")
            self.empty_text.setText(
                "Add your name, logo, address and how you like to be paid once. Every invoice starts with it."
            )
            self.empty_btn.setText("Add Your Profile…")
        else:
            self.empty_title.setText("No invoice open")
            self.empty_text.setText("Make a new one, or pick one from the list.")
            self.empty_btn.setText("New Invoice")

    # ------------------------------------------------------------------ the form
    def _build_form(self) -> None:
        self.form = QWidget()
        lay = vbox(self.form, 0, tokens.SPACE_3)
        self.lay.addWidget(self.form)
        self.groups: dict[str, Disclosure] = {}
        for key, (title, is_open) in GROUPS.items():
            self.groups[key] = Disclosure(title, is_open, first=not self.groups)
            lay.addWidget(self.groups[key])
        g = self.groups

        # From && Bill To: one of your profiles, one of your clients
        sec = Section("From")
        row = hbox(spacing=tokens.SPACE_2)
        self.business = picker()
        self.edit_business = QPushButton("Edit…")
        self.edit_business.setToolTip("Your name, logo, contact details and how you get paid")
        row.addWidget(self.business, 1)
        row.addWidget(self.edit_business)
        sec.add(row)
        g["who"].add(sec)
        sec = Section("Bill To")
        row = hbox(spacing=tokens.SPACE_2)
        self.client = picker("Choose a Client")
        self.client.setToolTip("Your saved clients. New Client… adds one.")
        self.edit_client = QPushButton("Edit…")
        self.edit_client.setToolTip("This client's name, contact, address and email")
        row.addWidget(self.client, 1)
        row.addWidget(self.edit_client)
        sec.add(row)
        g["who"].add(sec)

        # Invoice
        row = hbox(spacing=tokens.SPACE_2)
        sec = Section("Status")
        self.status = combo([(k, STATUS_LABELS[k], "") for k in STATUSES], "draft")
        self.status.setToolTip("Draft until you send it; Paid when the money arrives")
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
        self.work_dates.setPlaceholderText("Shoot / work dates, like Sep 26–27, 2026")
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
        self.add_item = QPushButton("Add Line Item")
        self.add_item.setIcon(theme.icon("plus", theme.TEXT, tokens.ICON_SM))
        add_row.addWidget(self.add_item)
        add_row.addStretch(1)
        g["items"].add(add_row)

        # Adjustments
        self.adj = g["adjustments"]
        row = hbox(spacing=tokens.SPACE_2)
        self.discount = self._num_field(row, "Discount", "0.00")
        self.deposit = self._num_field(row, "Deposit Paid", "0.00")
        self.adj.add(row)
        sec = Section("Sales Tax %")
        self.tax = QLineEdit()
        self.tax.setPlaceholderText("None")
        sec.add(self.tax)
        self.adj.add(sec)

        # Payment && Terms
        self.pay = g["payment"]
        sec = Section("How to Pay")
        self.payment = TextBox("", tokens.TEXT_BOX_TALL)
        sec.add(self.payment)
        self.pay.add(sec)
        sec = Section("Terms")
        self.terms = TextBox("", tokens.TEXT_BOX_TALL)
        self.terms.setToolTip("The due-date line is added on top automatically")
        sec.add(self.terms)
        self.pay.add(sec)
        sec = Section("Closing Note")
        self.note = QLineEdit()
        sec.add(self.note)
        self.pay.add(sec)
        row = hbox()
        self.reset_pay = QPushButton("Use Profile Defaults")
        self.reset_pay.setObjectName("Ghost")
        self.reset_pay.setToolTip("Put back the payment text, terms and note from your profile")
        self.save_pay = QPushButton("Make These the Defaults")
        self.save_pay.setObjectName("Ghost")
        self.save_pay.setToolTip("New invoices will start with this payment text, terms and note")
        row.addWidget(self.reset_pay)
        row.addWidget(self.save_pay)
        row.addStretch(1)
        self.pay.add(row)

        # Look
        self.look = g["look"]
        self._build_look()

        self._connect()

    def _num_field(self, row, label: str, placeholder: str) -> QLineEdit:
        sec = Section(label)
        f = QLineEdit()
        f.setPlaceholderText(placeholder)
        sec.add(f)
        row.addWidget(sec, 1)
        return f

    def _build_look(self) -> None:
        L = self.look
        self.logo_size_sec = Section("Logo Size")
        self.logo_size = combo([(k, v[0], "") for k, v in LOGO_SIZES.items()], "medium")
        self.logo_size_sec.add(self.logo_size)
        self.name_with_logo = ToggleRow("Show Name Next to Logo", True)
        self.name_with_logo.setToolTip("Turn off if your logo already spells out the name")
        self.logo_size_sec.add(self.name_with_logo)
        L.add(self.logo_size_sec)

        sec = Section("Type")
        items = [(k, s.label, s.tip) for k, s in TYPE_STYLES.items()]
        self.type_style = combo(items, "modern")
        self.type_style.insertSeparator(self.type_style.count())
        self.type_style.addItem("Custom Fonts", CUSTOM)
        self.type_style.setItemData(
            self.type_style.count() - 1,
            "Pick the heading and body fonts yourself",
            Qt.ItemDataRole.ToolTipRole,
        )
        sec.add(self.type_style)
        L.add(sec)
        self.custom_fonts = QWidget()
        cl = vbox(self.custom_fonts, 0, tokens.SPACE_3)
        s1 = Section("Heading Font")
        self.heading_font = self._font_combo(display=True)
        s1.add(self.heading_font)
        self.caps = ToggleRow("Name in Capitals", True)
        s1.add(self.caps)
        s2 = Section("Body Font")
        self.body_font = self._font_combo(display=False)
        s2.add(self.body_font)
        cl.addWidget(s1)
        cl.addWidget(s2)
        L.add(self.custom_fonts)

        sec = Section("Color")
        self.color = QComboBox()
        self.color.setCursor(Qt.CursorShape.PointingHandCursor)
        sec.add(self.color)
        L.add(sec)
        row = hbox(spacing=tokens.SPACE_2)
        sec = Section("Header")
        self.header = combo([(k, v, "") for k, v in HEADERS.items()], "clean")
        sec.add(self.header)
        row.addWidget(sec, 1)
        sec = Section("Paper")
        self.paper = combo([(k, v[0], "") for k, v in PAPERS.items()], "letter")
        sec.add(self.paper)
        row.addWidget(sec, 1)
        L.add(row)
        self.look_hint = hint("")
        L.add(self.look_hint)

    def _font_combo(self, display: bool) -> QComboBox:
        c = QComboBox()
        c.setCursor(Qt.CursorShape.PointingHandCursor)
        for fam, tip in BUNDLED_FONTS:
            if not display and fam in DISPLAY_ONLY:
                continue
            c.addItem(fam, fam)
            c.setItemData(c.count() - 1, tip, Qt.ItemDataRole.ToolTipRole)
        c.insertSeparator(c.count())
        c.addItem("Fonts on This Computer…", OTHER_FONT)
        return c

    def _set_font_combo(self, c: QComboBox, family: str) -> None:
        c.blockSignals(True)
        i = c.findData(family)
        if i < 0 and family:  # a font from this computer: list it at the top
            c.insertItem(0, family, family)
            i = 0
        c.setCurrentIndex(max(0, i))
        c.blockSignals(False)

    def _fill_colors(self, look: Look) -> None:
        c = self.color
        c.blockSignals(True)
        c.clear()
        for k, s in COLORS.items():
            c.addItem(swatch(s.accent), s.label, k)
        if look.color == CUSTOM:
            c.addItem(swatch(accent_of(look)), f"Custom {accent_of(look)}", CUSTOM)
        c.insertSeparator(c.count())
        c.addItem("Pick a Color…", PICK_COLOR)
        c.setCurrentIndex(max(0, c.findData(look.color)))
        c.blockSignals(False)

    # ------------------------------------------------------------------ wiring
    def _connect(self) -> None:
        def inv_text(field: str):
            return lambda t: self._edit(field, t)

        self.client.activated.connect(self._client_picked)
        self.edit_client.clicked.connect(lambda: self.client_wanted.emit("edit"))
        self.edit_business.clicked.connect(lambda: self.business_wanted.emit("edit"))
        self.number.textEdited.connect(self._number_typed)
        self.issued.dateChanged.connect(self._issued_changed)
        self.terms_days.currentIndexChanged.connect(
            lambda _i: self._edit("terms_days", int(self.terms_days.currentData()))
        )
        self.project.textEdited.connect(inv_text("project"))
        self.work_dates.textEdited.connect(inv_text("work_dates"))
        self.show_delivered.toggled.connect(self._toggle_delivered)
        self.delivered.dateChanged.connect(lambda q: self._edit("delivered", from_qdate(q)))
        self.add_item.clicked.connect(self._add_item)
        self.discount.textEdited.connect(inv_text("discount"))
        self.deposit.textEdited.connect(inv_text("deposit"))
        self.tax.textEdited.connect(inv_text("tax_rate"))
        self.payment.edited.connect(lambda: self._edit("payment", self.payment.text()))
        self.terms.edited.connect(lambda: self._edit("terms", self.terms.text()))
        self.note.textEdited.connect(inv_text("note"))
        self.reset_pay.clicked.connect(self._reset_pay)
        self.save_pay.clicked.connect(self._save_pay)
        self.status.currentIndexChanged.connect(self._status_picked)
        self.paid_on.dateChanged.connect(lambda q: self._edit("paid_on", from_qdate(q)))
        self.business.activated.connect(self._business_picked)

        self.logo_size.currentIndexChanged.connect(
            lambda _i: self._edit_look("logo_size", self.logo_size.currentData())
        )
        self.name_with_logo.toggled.connect(lambda on: self._edit_look("name_with_logo", on))
        self.type_style.currentIndexChanged.connect(self._style_picked)
        self.heading_font.currentIndexChanged.connect(
            lambda _i: self._font_picked(self.heading_font, "heading_font")
        )
        self.body_font.currentIndexChanged.connect(lambda _i: self._font_picked(self.body_font, "body_font"))
        self.caps.toggled.connect(lambda on: self._edit_look("heading_caps", on))
        self.color.currentIndexChanged.connect(self._color_picked)
        self.header.currentIndexChanged.connect(
            lambda _i: self._edit_look("header", self.header.currentData())
        )
        self.paper.currentIndexChanged.connect(lambda _i: self._edit_look("paper", self.paper.currentData()))
        for d in self.groups.values():
            d.toggled.connect(lambda _on: self.groups_changed.emit(self.open_groups()))

    def open_groups(self) -> dict:
        return {key: d.is_open() for key, d in self.groups.items()}

    def set_open_groups(self, groups: dict) -> None:
        for key, d in self.groups.items():
            d.set_open(bool(groups.get(key, GROUPS[key][1])))

    # ------------------------------------------------------------------ loading
    def current_business(self) -> Business | None:
        return self.lib.businesses.get(self.inv.business_id) if self.inv else None

    def load(self, inv: Invoice) -> None:
        self._loading = True
        self.inv = inv
        self.empty.hide()
        self.form.show()
        b = self.current_business()
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
        self.discount.setText(inv.discount)
        self.deposit.setText(inv.deposit)
        self.tax.setText(inv.tax_rate)
        self.payment.set_text(inv.payment)
        self.terms.set_text(inv.terms)
        self.note.setText(inv.note)
        self._rebuild_items()
        self.load_look(b)
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

    def load_look(self, b: Business | None) -> None:
        if b is None:
            return
        was = self._loading
        self._loading = True
        look = b.look
        has_logo = bool(look.logo) and (logos_dir() / look.logo).is_file()
        self.logo_size_sec.setVisible(has_logo)
        set_combo(self.logo_size, look.logo_size)
        self.name_with_logo.setChecked(look.name_with_logo)
        set_combo(
            self.type_style,
            look.type_style if look.type_style in TYPE_STYLES else CUSTOM,
        )
        custom = look.type_style not in TYPE_STYLES
        self.custom_fonts.setVisible(custom)
        base = TYPE_STYLES["modern"]
        self._set_font_combo(self.heading_font, look.heading_font or base.heading)
        self._set_font_combo(self.body_font, look.body_font or base.body)
        self.caps.setChecked(look.heading_caps)
        self._fill_colors(look)
        set_combo(self.header, look.header)
        set_combo(self.paper, look.paper)
        who = b.name or "this profile"
        self.look_hint.setText(
            f"Applies to every invoice from {who}."
            + ("" if has_logo else " To add a logo, click Edit… next to From.")
        )
        self._summaries()
        self._loading = was

    def _currency(self) -> str:
        b = self.current_business()
        return (b.currency if b else "$") or "$"

    def _rebuild_items(self) -> None:
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

    def _add_editor(self, it: LineItem, currency: str, at: int | None = None) -> ItemEditor:
        ed = ItemEditor(it, currency)
        ed.changed.connect(self._changed)
        ed.open_wanted.connect(self._toggle_item)
        ed.remove_wanted.connect(self._remove_item)
        ed.duplicate_wanted.connect(self._duplicate_item)
        ed.move_wanted.connect(self._move_item)
        pos = len(self.items) if at is None else at
        self.items_lay.insertWidget(pos, ed)
        self.items.insert(pos, ed)
        return ed

    def _positions(self) -> None:
        for i, ed in enumerate(self.items):
            ed.set_position(i, len(self.items))

    def _open_only(self, ed: ItemEditor | None, focus: bool = False) -> None:
        """One line item open at a time keeps a long list tidy."""
        for other in self.items:
            other.set_open(other is ed)
        if ed is not None:
            if focus:
                ed.desc.setFocus()
            QTimer.singleShot(0, ed, lambda: self.scroll.ensureWidgetVisible(ed))

    def _toggle_item(self, ed: ItemEditor) -> None:
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

    def _duplicate_item(self, ed: ItemEditor) -> None:
        if self.inv is None or ed not in self.items:
            return
        i = self.items.index(ed) + 1
        it = replace(ed.item)
        self.inv.items.insert(i, it)
        copy = self._add_editor(it, self._currency(), i)
        self._positions()
        self._open_only(copy)
        self._changed()

    def _move_item(self, ed: ItemEditor, step: int) -> None:
        if self.inv is None or ed not in self.items:
            return
        i = self.items.index(ed)
        j = i + step
        if not 0 <= j < len(self.items):
            return
        # self.items and self.inv.items are always in the same order
        self.items[i], self.items[j] = self.items[j], self.items[i]
        self.inv.items[i], self.inv.items[j] = self.inv.items[j], self.inv.items[i]
        self.items_lay.removeWidget(ed)
        self.items_lay.insertWidget(j, ed)
        self._positions()
        self._changed()

    def _remove_item(self, ed: ItemEditor) -> None:
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

    # ------------------------------------------------------------------ edits
    def _changed(self) -> None:
        if self.inv is not None and not self._loading:
            self._summaries()
            self.invoice_changed.emit(self.inv)

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
        """From outside (Mark as Sent after exporting)."""
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
        n = sum(1 for v in (self.inv.discount, self.inv.deposit, self.inv.tax_rate) if money.parse(v))
        self.adj.set_summary(f"{n} set" if n else "")
        same = b is not None and (self.inv.payment, self.inv.terms, self.inv.note) == (
            b.payment,
            b.terms,
            b.note,
        )
        self.pay.set_summary("" if same else "Edited")
        self.reset_pay.setVisible(not same)
        self.save_pay.setVisible(not same)
        if b is not None:
            style = TYPE_STYLES.get(b.look.type_style)
            color = COLORS.get(b.look.color)
            parts = [
                style.label if style else "Custom Fonts",
                color.label if color else accent_of(b.look),
            ]
            if b.look.logo:
                parts.append("Logo")
            self.look.set_summary(" · ".join(parts))

    # ------------------------------------------------------------------ look edits
    def _edit_look(self, field: str, value) -> None:
        b = self.current_business()
        if b is None or self._loading:
            return
        setattr(b.look, field, value)
        self.load_look(b)
        self.look_changed.emit(b)

    def _style_picked(self, _i: int) -> None:
        key = self.type_style.currentData()
        b = self.current_business()
        if b is None or self._loading:
            return
        if key == CUSTOM:
            st = TYPE_STYLES.get(b.look.type_style, TYPE_STYLES["modern"])
            b.look.heading_font = b.look.heading_font or st.heading
            b.look.body_font = b.look.body_font or st.body
            if b.look.type_style in TYPE_STYLES:  # start from the style you were on
                b.look.heading_font, b.look.body_font, b.look.heading_caps = (
                    st.heading,
                    st.body,
                    st.caps,
                )
        self._edit_look("type_style", key)

    def _font_picked(self, c: QComboBox, field: str) -> None:
        if self._loading:
            return
        b = self.current_business()
        if b is None:
            return
        fam = c.currentData()
        if fam == OTHER_FONT:
            current = getattr(b.look, field) or TYPE_STYLES["modern"].body
            from PySide6.QtGui import QFont

            ok, font = QFontDialog.getFont(QFont(current), self, "Pick a Font")
            if not ok:
                self.load_look(b)
                return
            fam = font.family()
        self._edit_look(field, fam)

    def _color_picked(self, _i: int) -> None:
        if self._loading:
            return
        b = self.current_business()
        if b is None:
            return
        key = self.color.currentData()
        if key == PICK_COLOR:
            chosen = QColorDialog.getColor(QColor(accent_of(b.look)), self, "Pick a Color")
            if not chosen.isValid():
                self.load_look(b)
                return
            b.look.custom_color = chosen.name().upper()
            key = CUSTOM
        self._edit_look("color", key)
