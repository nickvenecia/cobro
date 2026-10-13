"""The invoice list's filter button: how the list is divided, and which invoices it shows.

    Divide By    Month / Client / No Dividers
    Show         Everything / Draft / Sent / Overdue / Paid
    From      ▸  any one of your profiles (when you have more than one)
    Year      ▸  the year it was issued
    Clear Filters

Just an icon; the accent while a filter hides invoices. Clear Filters puts everything back to how it starts.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QLabel, QMenu, QToolButton, QWidgetAction

from saldo.core import document
from saldo.core.model import Invoice
from saldo.ui.style import theme
from saldo.ui.window.tables import DIVIDES

SHOWS = [
    ("all", "Everything", ""),
    ("draft", "Draft", "Not sent yet"),
    ("sent", "Sent", "Waiting to be paid, not yet due"),
    ("overdue", "Overdue", "Sent, and past its due date"),
    ("paid", "Paid", ""),
]
SHOW_LABEL = {k: label for k, label, _t in SHOWS}


@dataclass
class InvoiceFilter:
    show: str = "all"
    business: str = ""  # a profile's id; "" = any
    year: str = ""  # "2026"; "" = any

    def active(self) -> bool:
        return self.show != "all" or bool(self.business) or bool(self.year)

    def summary(self, names: dict[str, str]) -> str:
        parts = []
        if self.show != "all":
            parts.append(SHOW_LABEL.get(self.show, ""))
        if self.business:
            parts.append(names.get(self.business, "One Profile"))
        if self.year:
            parts.append(self.year)
        return " · ".join(parts)

    def keep(self, inv: Invoice, today=None) -> bool:
        if self.show != "all" and document.status_of(inv, today) != self.show:
            return False
        if self.business and inv.business_id != self.business:
            return False
        return not (self.year and not inv.issued.startswith(self.year))


class FilterButton(QToolButton):
    """The icon that opens the filter menu (built fresh each time, so From and Year list what's there now)."""

    changed = Signal()  # anything picked

    def __init__(self, profiles, years, parent=None):
        """`profiles`: () -> [(id, name)]; `years`: () -> ["2026", "2025"…]."""
        super().__init__(parent)
        self.setObjectName("Circle")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.profiles, self.years = profiles, years
        self.filter = InvoiceFilter()
        self.divide = "month"
        self.default_divide = "month"
        self.m = QMenu(self)
        self.m.setToolTipsVisible(True)
        self.m.aboutToShow.connect(self._build)
        self.setMenu(self.m)
        self.show_state()

    # ------------------------------------------------------------------ state
    def set_divide(self, key: str) -> None:
        self.divide = key if key in {k for k, _l, _t in DIVIDES} else self.default_divide

    def is_default(self) -> bool:
        return not self.filter.active() and self.divide == self.default_divide

    def clear(self) -> None:
        self.filter = InvoiceFilter()
        self.divide = self.default_divide
        self.show_state()

    def show_state(self) -> None:
        on = self.filter.active()
        self.setIcon(theme.icon("filter", theme.ACCENT if on else theme.MUTED))
        if bool(self.property("active")) != on:
            self.setProperty("active", on)
            self.style().unpolish(self)
            self.style().polish(self)
        names = dict(self.profiles())
        self.setToolTip(f"Showing: {self.filter.summary(names)}" if on else "Filter and divide the list")

    def _pick(self, what: str, key: str) -> None:
        if what == "divide":
            self.divide = key
        else:
            setattr(self.filter, what, key)
        self.show_state()
        self.changed.emit()

    # ------------------------------------------------------------------ the menu
    def _heading(self, text: str) -> None:
        label = QLabel(text)
        label.setObjectName("MenuHeading")
        a = QWidgetAction(self.m)
        a.setDefaultWidget(label)
        a.setEnabled(False)
        self.m.addAction(a)

    def _choices(self, menu: QMenu, what: str, items, current: str) -> None:
        group = QActionGroup(menu)
        for key, label, *tip in items:
            a = QAction(label, group)
            a.setCheckable(True)
            a.setChecked(key == current)
            if tip and tip[0]:
                a.setToolTip(tip[0])
            a.triggered.connect(lambda _c=False, k=key: self._pick(what, k))
            menu.addAction(a)

    def _build(self) -> None:
        m = self.m
        m.clear()
        self._heading("Divide By")
        self._choices(m, "divide", DIVIDES, self.divide)
        m.addSeparator()
        self._heading("Show")
        self._choices(m, "show", SHOWS, self.filter.show)
        m.addSeparator()
        profiles = self.profiles()
        if len(profiles) > 1:
            names = dict(profiles)
            title = f"From: {names.get(self.filter.business, '')}" if self.filter.business else "From"
            sub = m.addMenu(title)
            self._choices(sub, "business", [("", "Any Profile"), *profiles], self.filter.business)
        years = self.years()
        sub = m.addMenu(f"Year: {self.filter.year}" if self.filter.year else "Year")
        self._choices(sub, "year", [("", "Any Year"), *[(y, y) for y in years]], self.filter.year)
        m.addSeparator()
        clear = m.addAction("Clear Filters")
        clear.setEnabled(not self.is_default())
        clear.triggered.connect(self._clear)

    def _clear(self) -> None:
        self.clear()
        self.changed.emit()
