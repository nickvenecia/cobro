"""Step 2, Details: everything on the invoice, top to bottom in the order it reads.

Basic first (Status, From, Bill To, Invoice, Project, Line Items); the rest folds away
(Adjustments, Payment & Terms, Look), each fold remembered and saying what's changed.
Edits go straight into the Invoice (or, for Look, the Business) and fire a signal; the window
saves and redraws the preview.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from PySide6.QtCore import QDate, QLocale, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QCompleter,
    QDateEdit,
    QFileDialog,
    QFontDialog,
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolButton,
    QWidget,
)

from ..core import dates, money
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
    FitScroll,
    Section,
    StepHeader,
    TextBox,
    ToggleRow,
    combo,
    hbox,
    hint,
    set_combo,
    vbox,
)

log = get_logger(__name__)

OTHER_FONT = "__other__"
PICK_COLOR = "__pick__"
EDIT_BUSINESS = "__edit__"
ADD_BUSINESS = "__add__"
STATUS_LABELS = {"draft": "Draft", "sent": "Sent", "paid": "Paid"}
LOGO_MAX_PX = 1600  # bigger pictures are scaled down when added (keeps PDFs small)


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


def import_logo(src: Path) -> str:
    """Copy a logo into Cobro's own folder (so moving or deleting the original never breaks an invoice).
    Returns the stored file name. Raises ValueError if it isn't a picture Cobro can read."""
    from ..doc.render import logo_size

    if logo_size(src) is None:
        raise ValueError(f"Cobro can't read {src.name}. Use a PNG, JPG or SVG file.")
    data = src.read_bytes()
    digest = hashlib.sha256(data).hexdigest()[:16]
    folder = logos_dir()
    folder.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".svg":
        name = f"{digest}.svg"
        (folder / name).write_bytes(data)
        return name
    img = QImage(str(src))
    if img.isNull():
        raise ValueError(f"Cobro can't read {src.name}. Use a PNG, JPG or SVG file.")
    if max(img.width(), img.height()) > LOGO_MAX_PX:
        img = img.scaled(
            LOGO_MAX_PX,
            LOGO_MAX_PX,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    name = f"{digest}.png"
    if not img.save(str(folder / name), "PNG"):
        raise ValueError("Couldn't save the logo. Check that there's free space on this computer.")
    return name


# ---------------------------------------------------------------------------- one line item
class ItemEditor(QFrame):
    changed = Signal()
    removed = Signal(object)  # self

    def __init__(self, item: LineItem, currency: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ItemBox")
        self.item = item
        self.currency = currency
        lay = vbox(self, tokens.SPACE_3, tokens.SPACE_2)
        top = hbox(spacing=tokens.SPACE_2)
        self.desc = QLineEdit(item.description)
        self.desc.setPlaceholderText("What you did (Production, Edit…)")
        top.addWidget(self.desc, 1)
        rm = icon_button("x", "Remove Line Item")
        rm.clicked.connect(lambda: self.removed.emit(self))
        top.addWidget(rm)
        lay.addLayout(top)
        self.details = TextBox("Details (optional)")
        self.details.set_text(item.details)
        lay.addWidget(self.details)
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
        self.amount = QLabel()
        self.amount.setObjectName("ItemAmount")
        self.amount.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.qty)
        row.addWidget(times)
        row.addWidget(self.rate)
        row.addStretch(1)
        row.addWidget(self.amount)
        lay.addLayout(row)
        self._show_amount()
        self.desc.textEdited.connect(lambda t: self._set("description", t))
        self.details.edited.connect(lambda: self._set("details", self.details.text()))
        self.qty.textEdited.connect(lambda t: self._set("qty", t))
        self.rate.textEdited.connect(lambda t: self._set("rate", t))

    def _set(self, key: str, value: str) -> None:
        setattr(self.item, key, value)
        self._show_amount()
        self.changed.emit()

    def _show_amount(self) -> None:
        amt = money.line_amount(self.item.qty, self.item.rate)
        self.amount.setText(money.fmt(amt, self.currency) if self.item.rate.strip() else "")


# ---------------------------------------------------------------------------- the panel
class DetailsPanel(QFrame):
    invoice_changed = Signal(object)  # Invoice
    status_changed = Signal(object)  # Invoice
    look_changed = Signal(object)  # Business
    business_wanted = Signal(str)  # "edit" or "add"
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
        """kind: "business" (nothing set up yet) or "invoice" (no invoice picked)."""
        self.inv = None
        self.form.hide()
        self.empty.show()
        self._empty_action = action
        if kind == "business":
            self.empty_title.setText("Start with your business")
            self.empty_text.setText(
                "Add your name, address and how you like to be paid once. Every invoice starts with it."
            )
            self.empty_btn.setText("Add Your Business…")
        else:
            self.empty_title.setText("No invoice open")
            self.empty_text.setText("Make a new one, or pick one from the list.")
            self.empty_btn.setText("New Invoice")

    # ------------------------------------------------------------------ the form
    def _build_form(self) -> None:
        self.form = QWidget()
        lay = vbox(self.form, 0, tokens.SPACE_3)
        self.lay.addWidget(self.form)

        # Status
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
        lay.addLayout(row)

        # From
        sec = Section("From")
        self.business = QComboBox()
        self.business.setCursor(Qt.CursorShape.PointingHandCursor)
        sec.add(self.business)
        lay.addWidget(sec)

        # Bill To
        sec = Section("Bill To")
        self.client = QLineEdit()
        self.client.setPlaceholderText("Client name")
        self.completer = QCompleter([])
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.client.setCompleter(self.completer)
        self.contact = QLineEdit()
        self.contact.setPlaceholderText("Attention (contact person)")
        self.client_addr = TextBox("Address")
        self.client_email = QLineEdit()
        self.client_email.setPlaceholderText("Email")
        for w in (self.client, self.contact, self.client_addr, self.client_email):
            sec.add(w)
        lay.addWidget(sec)

        # Invoice
        row = hbox(spacing=tokens.SPACE_2)
        sec = Section("Invoice No.")
        self.number = QLineEdit()
        sec.add(self.number)
        row.addWidget(sec, 1)
        sec = Section("Issued")
        self.issued = date_field()
        sec.add(self.issued)
        row.addWidget(sec, 1)
        lay.addLayout(row)
        sec = Section("Payment Terms")
        self.terms_days = combo([(str(d), dates.terms_label(d), "") for d in TERMS_DAYS], "15")
        sec.add(self.terms_days)
        lay.addWidget(sec)

        # Project
        sec = Section("Project")
        self.project = QLineEdit()
        self.project.setPlaceholderText("Project name (optional)")
        self.work_dates = QLineEdit()
        self.work_dates.setPlaceholderText("Shoot / work dates, like Sep 26–27, 2026")
        sec.add(self.project)
        sec.add(self.work_dates)
        self.show_delivered = ToggleRow("Show Delivery Date")
        self.show_delivered.setToolTip("Prints when the final files were delivered")
        sec.add(self.show_delivered)
        self.delivered = date_field()
        sec.add(self.delivered)
        lay.addWidget(sec)

        # Line items
        self.items_sec = Section("Line Items")
        self.items_box = QWidget()
        self.items_lay = vbox(self.items_box, 0, tokens.SPACE_2)
        self.items_sec.add(self.items_box)
        add_row = hbox()
        self.add_item = QPushButton("Add Line Item")
        self.add_item.setIcon(theme.icon("plus", theme.TEXT, tokens.ICON_SM))
        add_row.addWidget(self.add_item)
        add_row.addStretch(1)
        self.items_sec.add(add_row)
        lay.addWidget(self.items_sec)

        # Adjustments
        self.adj = Disclosure("Adjustments")
        row = hbox(spacing=tokens.SPACE_2)
        self.discount = self._num_field(row, "Discount", "0.00")
        self.deposit = self._num_field(row, "Deposit Paid", "0.00")
        self.adj.lay.addLayout(row)
        sec = Section("Sales Tax %")
        self.tax = QLineEdit()
        self.tax.setPlaceholderText("None")
        sec.add(self.tax)
        self.adj.add(sec)
        lay.addWidget(self.adj)

        # Payment & Terms
        self.pay = Disclosure("Payment && Terms")
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
        self.reset_pay = QPushButton("Use Business Defaults")
        self.reset_pay.setObjectName("Ghost")
        self.reset_pay.setToolTip("Put back the payment text, terms and note from your business")
        self.save_pay = QPushButton("Make These the Defaults")
        self.save_pay.setObjectName("Ghost")
        self.save_pay.setToolTip("New invoices will start with this payment text, terms and note")
        row.addWidget(self.reset_pay)
        row.addWidget(self.save_pay)
        row.addStretch(1)
        self.pay.lay.addLayout(row)
        lay.addWidget(self.pay)

        # Look
        self.look = Disclosure("Look")
        self._build_look()
        lay.addWidget(self.look)

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
        sec = Section("Logo")
        row = hbox(spacing=tokens.SPACE_2)
        self.logo_thumb = QLabel()
        self.logo_thumb.setObjectName("LogoThumb")
        self.logo_thumb.setFixedHeight(tokens.LOGO_THUMB)
        self.logo_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_btn = QPushButton("Choose Logo…")
        self.logo_remove = icon_button("x", "Remove Logo")
        row.addWidget(self.logo_thumb)
        row.addWidget(self.logo_btn)
        row.addWidget(self.logo_remove)
        row.addStretch(1)
        sec.add(row)
        L.add(sec)
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
        L.lay.addLayout(row)
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

        self.client.textEdited.connect(lambda t: self._edit_client("name", t))
        self.completer.activated.connect(self._pick_client)
        self.contact.textEdited.connect(lambda t: self._edit_client("contact", t))
        self.client_addr.edited.connect(lambda: self._edit_client("address", self.client_addr.text()))
        self.client_email.textEdited.connect(lambda t: self._edit_client("email", t))
        self.number.textEdited.connect(inv_text("number"))
        self.issued.dateChanged.connect(lambda q: self._edit("issued", from_qdate(q)))
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

        self.logo_btn.clicked.connect(self._choose_logo)
        self.logo_remove.clicked.connect(lambda: self._edit_look("logo", ""))
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
        for name, d in (
            ("adjustments", self.adj),
            ("payment", self.pay),
            ("look", self.look),
        ):
            d.toggled.connect(lambda _on, n=name: self.groups_changed.emit(self.open_groups()))

    def open_groups(self) -> dict:
        return {
            "adjustments": self.adj.is_open(),
            "payment": self.pay.is_open(),
            "look": self.look.is_open(),
        }

    def set_open_groups(self, groups: dict) -> None:
        self.adj.set_open(bool(groups.get("adjustments", False)))
        self.pay.set_open(bool(groups.get("payment", False)))
        self.look.set_open(bool(groups.get("look", True)))

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
        self.completer.model().setStringList(
            sorted((c.name for c in self.lib.clients.values()), key=str.casefold)
        )
        self.client.setText(inv.client.name)
        self.contact.setText(inv.client.contact)
        self.client_addr.set_text(inv.client.address)
        self.client_email.setText(inv.client.email)
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
            c.addItem(b.name or "Untitled Business", b.id)
        c.insertSeparator(c.count())
        c.addItem("Edit This Business…", EDIT_BUSINESS)
        c.addItem("Add a Business…", ADD_BUSINESS)
        if self.inv:
            c.setCurrentIndex(max(0, c.findData(self.inv.business_id)))
        c.blockSignals(False)

    def load_look(self, b: Business | None) -> None:
        if b is None:
            return
        was = self._loading
        self._loading = True
        look = b.look
        logo = logos_dir() / look.logo if look.logo else None
        has_logo = bool(logo and logo.is_file())
        if has_logo:
            pm = QPixmap()
            if logo.suffix.lower() == ".svg":
                from PySide6.QtSvg import QSvgRenderer

                r = QSvgRenderer(str(logo))
                size = r.defaultSize()
                h = tokens.LOGO_THUMB * 2
                w = max(1, round(h * size.width() / max(1, size.height())))
                pm = QPixmap(w, h)
                pm.fill(Qt.GlobalColor.transparent)
                p = QPainter(pm)
                r.render(p)
                p.end()
            else:
                pm.load(str(logo))
            pm = pm.scaledToHeight(
                (tokens.LOGO_THUMB - tokens.SPACE_2) * 2,
                Qt.TransformationMode.SmoothTransformation,
            )
            pm.setDevicePixelRatio(2)
            self.logo_thumb.setPixmap(pm)
            self.logo_thumb.setFixedWidth(min(pm.width() // 2 + tokens.SPACE_2, tokens.LOGO_THUMB * 4))
        self.logo_thumb.setVisible(has_logo)
        self.logo_remove.setVisible(has_logo)
        self.logo_btn.setText("Change…" if has_logo else "Choose Logo…")
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
        self.look_hint.setText(f"Applies to every invoice from {b.name or 'this business'}.")
        self._summaries()
        self._loading = was

    def _rebuild_items(self) -> None:
        for ed in self.items:
            ed.setParent(None)
            ed.deleteLater()
        self.items = []
        cur = (self.current_business().currency if self.current_business() else "$") or "$"
        for it in self.inv.items:
            self._add_editor(it, cur)

    def _add_editor(self, it: LineItem, currency: str) -> ItemEditor:
        ed = ItemEditor(it, currency)
        ed.changed.connect(self._items_changed)
        ed.removed.connect(self._remove_item)
        self.items_lay.addWidget(ed)
        self.items.append(ed)
        return ed

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

    def _edit_client(self, field: str, value: str) -> None:
        if self.inv is None or self._loading:
            return
        setattr(self.inv.client, field, value)
        self._changed()

    def _pick_client(self, name: str) -> None:
        """Picked a saved client from the suggestions: fill in their details."""
        saved = self.lib.find_client(name)
        if saved is None or self.inv is None:
            return
        self.inv.client = Client(
            id=saved.id,
            name=saved.name,
            contact=saved.contact,
            address=saved.address,
            email=saved.email,
        )
        self._loading = True
        self.client.setText(saved.name)
        self.contact.setText(saved.contact)
        self.client_addr.set_text(saved.address)
        self.client_email.setText(saved.email)
        self._loading = False
        self._changed()

    def _toggle_delivered(self, on: bool) -> None:
        self.delivered.setVisible(on)
        if self.inv is None or self._loading:
            return
        self.inv.delivered = from_qdate(self.delivered.date()) if on else ""
        self._changed()

    def _items_changed(self) -> None:
        self._changed()

    def _add_item(self) -> None:
        if self.inv is None:
            return
        it = LineItem()
        self.inv.items.append(it)
        b = self.current_business()
        ed = self._add_editor(it, (b.currency if b else "$") or "$")
        ed.desc.setFocus()
        self._changed()
        self.scroll.ensureWidgetVisible(ed)

    def _remove_item(self, ed: ItemEditor) -> None:
        if self.inv is None:
            return
        if ed.item in self.inv.items:
            self.inv.items.remove(ed.item)
        self.items.remove(ed)
        ed.setParent(None)
        ed.deleteLater()
        if not self.inv.items:
            self.inv.items.append(LineItem())
            self._add_editor(self.inv.items[0], "$")
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
        if key in (EDIT_BUSINESS, ADD_BUSINESS):
            self.refresh_businesses()  # put the selection back
            self.business_wanted.emit("edit" if key == EDIT_BUSINESS else "add")
            return
        if key and key != self.inv.business_id:
            self.inv.business_id = key
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
        if self.inv is None:
            return
        n = sum(1 for v in (self.inv.discount, self.inv.deposit, self.inv.tax_rate) if money.parse(v))
        self.adj.set_summary(f"{n} set" if n else "")
        b = self.current_business()
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

    def _choose_logo(self) -> None:
        b = self.current_business()
        if b is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose a Logo", str(Path.home()), "Logos (*.png *.jpg *.jpeg *.svg)"
        )
        if not path:
            return
        try:
            name = import_logo(Path(path))
        except (OSError, ValueError) as e:
            log.warning("logo not added: %s", e)
            self.window().toast(str(e) if isinstance(e, ValueError) else "Couldn't read that file.")
            return
        log.info("logo added for %s", b.name)
        self._edit_look("logo", name)
