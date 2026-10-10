"""Step 1, Invoices: every invoice as a card (newest first), a filter, and what's still owed.

Click a card to open it. Right-click (or the card's ⋯) for Duplicate and Delete. The bottom bar
says how much is unpaid and how much came in this year, and holds the tools menu (⋯).
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QMenu, QPushButton, QToolButton, QWidget

from ..core import dates, document, money
from ..core.model import Invoice
from ..core.store import Library
from . import theme, tokens
from .widgets import FitScroll, StepHeader, combo, hbox, hint, repolish, vbox

FILTERS = [
    ("all", "All Invoices", ""),
    ("unpaid", "Unpaid", "Sent and not paid yet"),
    ("overdue", "Overdue", "Past the due date"),
    ("draft", "Drafts", "Not sent yet"),
    ("paid", "Paid", ""),
]
CHIP = {"draft": "Draft", "sent": "Sent", "overdue": "Overdue", "paid": "Paid"}


def matches(inv: Invoice, key: str) -> bool:
    st = document.status_of(inv)
    if key == "all":
        return True
    if key == "unpaid":
        return st in ("sent", "overdue")
    return st == key


class Card(QFrame):
    clicked = Signal(str)
    menu_wanted = Signal(str, QPoint)

    def __init__(self, inv_id: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.inv_id = inv_id
        self.setObjectName("Card")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(tokens.CARD_H)
        lay = vbox(
            self,
            (tokens.SPACE_3, tokens.SPACE_2, tokens.SPACE_3, tokens.SPACE_2),
            tokens.SPACE_1,
        )
        top = hbox(spacing=tokens.SPACE_2)
        self.client = QLabel()
        self.client.setObjectName("CardClient")
        self.amount = QLabel()
        self.amount.setObjectName("CardAmount")
        top.addWidget(self.client, 1)
        top.addWidget(self.amount)
        bottom = hbox(spacing=tokens.SPACE_2)
        self.meta = QLabel()
        self.meta.setObjectName("CardNumber")
        self.chip = QLabel()
        self.chip.setObjectName("Chip")
        bottom.addWidget(self.meta, 1)
        bottom.addWidget(self.chip)
        lay.addLayout(top)
        lay.addLayout(bottom)
        self._client_text = ""
        self._meta_text = ""

    def show_invoice(self, inv: Invoice, currency: str) -> None:
        self._client_text = inv.client.name.strip() or "No client yet"
        self._elide()
        t = money.totals(inv)
        st = document.status_of(inv)
        self.amount.setText(money.fmt(t.total if st == "paid" else t.balance, currency))
        when = dates.fmt(dates.parse(inv.issued))
        self._meta_text = f"{inv.number}  ·  {when}" if when else inv.number
        self._elide()
        if self.chip.property("tone") != st:
            self.chip.setProperty("tone", st)
            repolish(self.chip)
        self.chip.setText(CHIP.get(st, st.title()))

    def set_selected(self, on: bool) -> None:
        if bool(self.property("selected")) != on:
            self.setProperty("selected", on)
            repolish(self)

    def _elide(self) -> None:
        for label, text in (
            (self.client, self._client_text),
            (self.meta, self._meta_text),
        ):
            w = max(40, label.width())
            label.setText(label.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, w))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._elide()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.inv_id)
        super().mousePressEvent(e)

    def contextMenuEvent(self, e):
        self.menu_wanted.emit(self.inv_id, e.globalPos())


class InvoiceList(QFrame):
    picked = Signal(str)
    new_wanted = Signal()
    duplicate_wanted = Signal(str)
    delete_wanted = Signal(str)

    def __init__(self, lib: Library, parent: QWidget | None = None):
        super().__init__(parent)
        self.lib = lib
        self.setFixedWidth(tokens.LIST_W)
        self.cards: dict[str, Card] = {}
        self.current = ""
        outer = vbox(self, 0, 0)
        header = StepHeader(1, "Invoices")
        self.btn_new = QToolButton()
        self.btn_new.setObjectName("IconBtn")
        self.btn_new.setIcon(theme.icon("plus", theme.TEXT))
        self.btn_new.setToolTip("New Invoice (Ctrl+N)")
        self.btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new.clicked.connect(self.new_wanted.emit)
        header.actions.addWidget(self.btn_new)
        outer.addWidget(header)

        top = QWidget()
        tl = vbox(top, (tokens.SPACE_4, tokens.SPACE_3, tokens.SPACE_4, 0), 0)
        self.filter = combo(FILTERS, "all")
        self.filter.currentIndexChanged.connect(lambda _i: self.refresh())
        tl.addWidget(self.filter)
        outer.addWidget(top)

        self.scroll = FitScroll()
        body = QWidget()
        self.lay = vbox(
            body,
            (
                tokens.SPACE_4,
                tokens.SPACE_3,
                tokens.SPACE_4 - tokens.SCROLL_GUTTER,
                tokens.SPACE_4,
            ),
            tokens.SPACE_2,
        )
        self.empty = hint("")
        self.lay.addWidget(self.empty)
        self.lay.addStretch(1)
        self.scroll.setWidget(body)
        outer.addWidget(self.scroll, 1)

        foot = QFrame()
        foot.setObjectName("PanelBottom")
        fl = vbox(foot, tokens.SPACE_4, tokens.SPACE_2)
        stats = hbox(spacing=tokens.SPACE_4)
        self.unpaid = self._stat(stats, "Unpaid")
        self.paid = self._stat(stats, f"Paid in {dates.today().year}")
        stats.addStretch(1)
        self.btn_more = QToolButton()
        self.btn_more.setObjectName("IconBtn")
        self.btn_more.setIcon(theme.icon("more", theme.MUTED))
        self.btn_more.setToolTip("Business, updates and more")
        self.btn_more.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        stats.addWidget(self.btn_more, 0, Qt.AlignmentFlag.AlignBottom)
        fl.addLayout(stats)
        self.btn_update = QPushButton()
        self.btn_update.setObjectName("Secondary")
        self.btn_update.hide()
        fl.addWidget(self.btn_update)
        outer.addWidget(foot)

    def _stat(self, row, label: str) -> QLabel:
        box = vbox(spacing=0)
        k = QLabel(label)
        k.setObjectName("FooterStat")
        v = QLabel()
        v.setObjectName("FooterValue")
        box.addWidget(k)
        box.addWidget(v)
        row.addLayout(box)
        return v

    def _currency(self, inv: Invoice) -> str:
        b = self.lib.businesses.get(inv.business_id)
        return (b.currency if b else "$") or "$"

    def refresh(self) -> None:
        """Rebuild the list from the library (cheap: a few dozen cards)."""
        key = self.filter.currentData() or "all"
        shown = [i for i in self.lib.ordered() if matches(i, key)]
        keep = {i.id for i in shown}
        for inv_id in list(self.cards):
            if inv_id not in keep:
                self.cards.pop(inv_id).deleteLater()
        for pos, inv in enumerate(shown):
            card = self.cards.get(inv.id)
            if card is None:
                card = Card(inv.id)
                card.clicked.connect(self.picked.emit)
                card.menu_wanted.connect(self._menu)
                self.cards[inv.id] = card
            self.lay.insertWidget(pos, card)
            card.show_invoice(inv, self._currency(inv))
            card.set_selected(inv.id == self.current)
        if not self.lib.invoices:
            self.empty.setText("Your invoices will show up here.")
        elif not shown:
            self.empty.setText("Nothing here with this filter.")
        self.empty.setVisible(not shown)
        self._totals()

    def update_card(self, inv: Invoice) -> None:
        card = self.cards.get(inv.id)
        if card is not None:
            card.show_invoice(inv, self._currency(inv))
        self._totals()

    def select(self, inv_id: str) -> None:
        self.current = inv_id
        for k, c in self.cards.items():
            c.set_selected(k == inv_id)
        card = self.cards.get(inv_id)
        if card is not None:
            self.scroll.ensureWidgetVisible(card)

    def _totals(self) -> None:
        year = dates.today().year
        symbols = {self._currency(i) for i in self.lib.invoices.values()} or {"$"}
        sym = next(iter(symbols)) if len(symbols) == 1 else ""
        unpaid = sum(
            (money.totals(i).balance for i in self.lib.invoices.values() if i.status == "sent"),
            money.ZERO,
        )
        paid = sum(
            (
                money.totals(i).total
                for i in self.lib.invoices.values()
                if i.status == "paid" and (dates.parse(i.paid_on) or dates.today()).year == year
            ),
            money.ZERO,
        )
        self.unpaid.setText(money.fmt(unpaid, sym))
        self.paid.setText(money.fmt(paid, sym))

    def _menu(self, inv_id: str, pos: QPoint) -> None:
        m = QMenu(self)
        m.addAction(
            theme.menu_icon("copy"),
            "Duplicate",
            lambda: self.duplicate_wanted.emit(inv_id),
        )
        m.addSeparator()
        m.addAction(theme.menu_icon("trash"), "Delete…", lambda: self.delete_wanted.emit(inv_id))
        m.exec(pos)
