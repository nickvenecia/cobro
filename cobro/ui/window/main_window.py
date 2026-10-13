"""The window: the sidebar (where you are) | a big table of your invoices | the one you picked, editable.

Pick a place in the sidebar (All Invoices, Drafts, Unpaid, Paid), click an invoice, change it on the right.
The invoice itself opens in its own window when you ask for it (Invoice…). Edits save themselves a moment
after you stop typing.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, QSize, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QWidget,
)

from cobro.core import dates, document, money, update
from cobro.core.history import History
from cobro.core.log import get_logger
from cobro.core.model import Business, Invoice
from cobro.core.store import Library
from cobro.ui.components import titlebar
from cobro.ui.components.glass import Dock, GlassRoot, glass
from cobro.ui.components.widgets import ElidedLabel, SearchField, Toast, hbox, vbox
from cobro.ui.dialogs.preview import PageDialog
from cobro.ui.panels.invoice import InvoicePanel
from cobro.ui.style import theme, tokens
from cobro.ui.window.ai import AIMixin
from cobro.ui.window.common import TITLES, in_place
from cobro.ui.window.editing import EditingMixin
from cobro.ui.window.filters import FilterButton
from cobro.ui.window.menus import MenusMixin
from cobro.ui.window.pages import PagesMixin
from cobro.ui.window.services import ServicesMixin
from cobro.ui.window.sidebar import Sidebar
from cobro.ui.window.tables import InvoiceTable, menu
from cobro.ui.window.transfer import TransferMixin

log = get_logger(__name__)


class MainWindow(AIMixin, MenusMixin, EditingMixin, TransferMixin, PagesMixin, ServicesMixin, QMainWindow):
    def __init__(self, lib: Library | None = None):
        super().__init__()
        self.lib = lib or Library().load()
        self.setWindowTitle("Cobro")
        self.resize(*tokens.WINDOW_SIZE)
        self.setMinimumSize(*tokens.WINDOW_MIN)
        self._dirty: set[str] = set()
        self._dirty_businesses = False
        self.history: History | None = None
        self._fresh: tuple[str, dict] | None = None  # a new invoice not filled in yet
        self.last_export: Path | None = None
        self._release: update.Release | None = None
        self.view_key = "all"
        self.page: PageDialog | None = None
        self.page_inv: str = ""  # the invoice the page window shows

        root = GlassRoot()
        self.root = root
        outer = vbox(root, 0, 0)
        self.titlebar = titlebar.install(self)
        if self.titlebar is not None:
            outer.addWidget(self.titlebar)
        gap = tokens.GLASS_GAP
        body = hbox(spacing=gap)
        body.setContentsMargins(gap, 0 if self.titlebar is not None else gap, gap, gap)
        self.sidebar = glass(Sidebar(self.lib))
        root.float(self.sidebar)
        body.addWidget(self.sidebar)
        body.addWidget(self._build_center(), 1)
        self.panel = InvoicePanel(self.lib)
        self.inspector = glass(QStackedWidget())  # the glass panel on the right…
        self.inspector.addWidget(self.panel)
        self.assistant = self._build_assistant()
        self.inspector.addWidget(self.assistant)
        self.dock = Dock(self.inspector, root, self.sidebar, body)  # …which slides in when something's picked
        self.dock.follower = lambda: self.pages.currentWidget()
        outer.addLayout(body, 1)
        esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc.activated.connect(self.deselect)
        self.setCentralWidget(root)
        self.toaster = Toast(self)

        self._save_timer = QTimer(self, singleShot=True, interval=tokens.SAVE_DELAY_MS, timeout=self.flush)
        self._table_timer = QTimer(
            self, singleShot=True, interval=tokens.TABLE_DELAY_MS, timeout=self.refresh
        )
        self._draw_timer = QTimer(self, singleShot=True, interval=tokens.DRAW_DELAY_MS, timeout=self.redraw)

        self._wire()
        self._menus()
        groups = self.lib.settings.get("groups", {})
        groups = groups if isinstance(groups, dict) else {}
        state = groups.get(self.panel.KEY)
        if isinstance(state, dict):
            self.panel.set_open_groups(state)
        folded = self.lib.settings.get("folded", [])
        self.table.folded = {x for x in folded if isinstance(x, str)} if isinstance(folded, list) else set()
        self.view_menu.set_divide(str(self.lib.settings.get("divide", "month")))
        self._restored = False  # True: open at the size already set (screenshots), not the saved one
        view = self.lib.settings.get("view", "all")
        self.go(view if isinstance(view, str) else "all")
        self.look_changed()
        self.history = History(self.lib)  # undo/redo starts from how things are when the window opens
        QTimer.singleShot(tokens.UPDATE_CHECK_DELAY_MS, self._auto_check_updates)

    # ------------------------------------------------------------------ building
    def _build_center(self) -> QWidget:
        center = QFrame()
        center.setObjectName("Center")
        lay = vbox(center, 0, 0)
        bar = QFrame()
        bar.setObjectName("Toolbar")
        bar.setFixedHeight(tokens.TOOLBAR_H)
        # three parts: the title on the left, the search and filter centred, the buttons on the right
        grid = QGridLayout(bar)
        grid.setContentsMargins(tokens.SPACE_4, 0, tokens.SPACE_2, 0)
        grid.setHorizontalSpacing(tokens.SPACE_4)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(2, 1)
        left = hbox(spacing=tokens.SPACE_2)
        self.title = QLabel(TITLES["all"])
        self.title.setObjectName("PageTitle")
        self.count = ElidedLabel()  # "12", or "3 selected": gives way before the search does
        self.count.setObjectName("PageCount")
        self.count.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        left.addWidget(self.title)
        left.addWidget(self.count)
        left.addStretch(1)
        grid.addLayout(left, 0, 0)
        mid = hbox(spacing=tokens.SPACE_2)
        self.search = SearchField()
        self.search.setPlaceholderText("Search")
        self.search.setProperty("capsule", True)
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(tokens.SEARCH_MIN)  # shrinks before anything squeezes together
        self.search.setMaximumWidth(tokens.SEARCH_W)
        self.search.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.search.addAction(theme.icon("search", theme.FAINT), QLineEdit.ActionPosition.LeadingPosition)
        self.search.textChanged.connect(lambda _t: self._apply_search())
        mid.addWidget(self.search)
        # how the list is divided and what it shows, behind one icon (the accent while a filter hides some)
        self.view_menu = FilterButton(self._profile_names, self._years)
        self.view_menu.changed.connect(self._view_picked)
        mid.addWidget(self.view_menu)
        grid.addLayout(mid, 0, 1, Qt.AlignmentFlag.AlignCenter)
        right = hbox(spacing=tokens.SPACE_2)
        right.addStretch(1)
        self.btn_export = QToolButton()
        self.btn_export.setObjectName("Circle")
        self.btn_export.setIcon(theme.icon("share", theme.MUTED))
        self.btn_export.setToolTip("Export and back up")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        right.addWidget(self.btn_export)
        self.btn_ai = QToolButton()
        self.btn_ai.setObjectName("Circle")
        self.btn_ai.setIcon(theme.icon("assistant", theme.ACCENT, tokens.ICON_LG))
        self.btn_ai.setIconSize(QSize(tokens.ICON_LG, tokens.ICON_LG))
        self.btn_ai.setToolTip("AI Assistant (⌘J)")
        self.btn_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ai.clicked.connect(self.toggle_assistant)
        right.addWidget(self.btn_ai)
        self.btn_new = QToolButton()
        self.btn_new.setObjectName("CirclePrimary")
        self.btn_new.setIcon(theme.icon("plus", theme.ON_ACCENT))
        self.btn_new.setToolTip("New Invoice (⌘N)")
        self.btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new.clicked.connect(self.new_invoice)
        right.addWidget(self.btn_new)
        grid.addLayout(right, 0, 2)
        lay.addWidget(bar)
        self.toolbar = bar

        self.pages = QStackedWidget()
        self.table = InvoiceTable()
        self.empty = QWidget()
        el = vbox(self.empty, tokens.SPACE_5, tokens.SPACE_3)
        el.addStretch(1)
        self.empty_text = QLabel()
        self.empty_text.setObjectName("EmptyTitle")
        self.empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_btn = QPushButton()
        self.empty_btn.setObjectName("Primary")
        self._empty_slot = None
        self.empty_btn.clicked.connect(lambda: self._empty_slot and self._empty_slot())
        row = hbox(spacing=tokens.SPACE_2)
        row.addStretch(1)
        row.addWidget(self.empty_btn)
        row.addStretch(1)
        el.addWidget(self.empty_text)
        el.addLayout(row)
        el.addStretch(2)
        for w in (self.table, self.empty):
            self.pages.addWidget(w)
        lay.addWidget(self.pages, 1)
        self.totals = QFrame()
        self.totals.setObjectName("Totals")
        tl = hbox(
            self.totals, (tokens.SPACE_5, tokens.SPACE_3, tokens.SPACE_5, tokens.SPACE_3), tokens.SPACE_5
        )
        self.total_values: dict[str, QLabel] = {}
        self.total_labels: dict[str, QLabel] = {}
        tl.addStretch(1)
        for key, label in (("unpaid", "Unpaid"), ("overdue", "Overdue"), ("paid", "Paid"), ("all", "Total")):
            box = vbox(spacing=0)
            k = QLabel(label)
            k.setObjectName("TotalLabel")
            v = QLabel()
            v.setObjectName("TotalValue")
            k.setAlignment(Qt.AlignmentFlag.AlignRight)
            v.setAlignment(Qt.AlignmentFlag.AlignRight)
            box.addWidget(k)
            box.addWidget(v)
            tl.addLayout(box)
            self.total_values[key] = v
            self.total_labels[key] = k
        self.total_values["overdue"].setProperty("tone", "overdue")
        lay.addWidget(self.totals)
        return center

    def _wire(self) -> None:
        sb = self.sidebar
        sb.picked.connect(self.go)
        sb.new_invoice.connect(self.new_invoice)
        sb.profile_card.clicked.connect(self._app_menu)
        sb.btn_update.clicked.connect(self.show_update)
        t = self.table
        t.picked.connect(self.open)
        t.menu_wanted.connect(self._row_menu)
        t.delete_wanted.connect(self.delete_invoices)
        t.cleared.connect(self.deselect)
        t.itemClicked.connect(lambda _r, _c: self.lib.settings.__setitem__("folded", sorted(t.folded)))
        t.itemSelectionChanged.connect(self._selection_count)
        p = self.panel
        p.changed.connect(self._invoice_edited)
        p.status_changed.connect(lambda _i: (self.flush(), self.refresh()))
        p.business_wanted.connect(lambda kind: self.edit_business(kind == "add"))
        p.client_wanted.connect(lambda kind: self.edit_client(kind == "new"))
        p.defaults_saved.connect(self._defaults_saved)
        p.delete_wanted.connect(lambda i: self.delete_invoices([i]))
        p.duplicate_wanted.connect(self.duplicate)
        p.sheet_wanted.connect(self.show_page)
        p.close_wanted.connect(self.deselect)  # the round ✕
        p.groups_changed.connect(self._groups_changed)

    # ------------------------------------------------------------------ where you are
    def business(self) -> Business | None:
        """The profile you're working as (new invoices start from it)."""
        cur = self.lib.settings.get("business", "")
        return self.lib.businesses.get(cur) or next(iter(self.lib.businesses.values()), None)

    def _profile_names(self) -> list[tuple[str, str]]:
        return [(b.id, b.name or "Unnamed Profile") for b in self.lib.businesses.values()]

    def _years(self) -> list[str]:
        return sorted(
            {i.issued[:4] for i in self.lib.invoices.values() if i.issued[:4].isdigit()}, reverse=True
        )

    def _view_picked(self) -> None:
        self.lib.settings["divide"] = self.view_menu.divide
        self.refresh()

    def go(self, view: str) -> None:
        """Show a place from the sidebar."""
        self.flush()
        self._drop_fresh()
        view = view if view in TITLES else "all"
        self.view_key = view
        self.lib.settings["view"] = view
        self.sidebar.select(view)
        self.title.setText(TITLES[view])
        self.refresh()
        if self.assistant_showing():  # the assistant stays while you move around
            self._ai_state()
            return
        cur = self.panel.inv
        if cur is not None and self.dock.opened and cur.id in self._shown_ids():
            self.table.select_id(cur.id)
        else:
            self._inspector_empty()

    def _showing(self) -> list[Invoice]:
        """The invoices this place and the filter keep (before searching)."""
        today = dates.today()
        f = self.view_menu.filter
        return [
            inv for inv in self.lib.ordered() if in_place(inv, self.view_key, today) and f.keep(inv, today)
        ]

    def _shown_ids(self) -> set[str]:
        return {r.data(0, Qt.ItemDataRole.UserRole) for r in self.table.showing_rows()}

    def refresh(self) -> None:
        """Fill the table for where you are (and the sidebar's counts)."""
        self.sidebar.refresh()
        invoices = self._showing()
        self.table.fill(self.lib, invoices, self.view_menu.divide)
        if invoices:
            self.pages.setCurrentWidget(self.table)
        else:
            self.pages.setCurrentWidget(self._empty_page())
            if (not self.lib.businesses or not self.lib.invoices) and not self.assistant_showing():
                self.dock.set_open(False)
        self._apply_search()
        if self.history is not None:
            self.history.mark()

    def _empty_page(self) -> QWidget:
        if not self.lib.businesses:
            text, action, slot = (
                "Add your profile to start.",
                "Add Your Profile…",
                lambda: self.edit_business(True),
            )
        elif not self.lib.invoices:
            text, action, slot = "No invoices yet.", "New Invoice", self.new_invoice
        elif self.view_menu.filter.active():
            text, action, slot = "Nothing matches the filter.", "Clear Filters", self._clear_filters
        else:
            text = {
                "drafts": "No drafts.",
                "unpaid": "Nothing waiting to be paid.",
                "paid": "Nothing paid yet.",
            }
            text, action, slot = text.get(self.view_key, "No invoices yet."), "", None
        self.empty_text.setText(text)
        self.empty_btn.setText(action)
        self.empty_btn.setVisible(bool(action))
        self._empty_slot = slot
        return self.empty

    def _clear_filters(self) -> None:
        self.view_menu.clear()
        self._view_picked()

    def _apply_search(self) -> None:
        shown = self.table.show_only(self.search.text())
        self._totals([self.lib.invoices[i] for i in shown if i in self.lib.invoices])
        self.totals.setVisible(bool(self.lib.invoices) and self.pages.currentWidget() is self.table)
        self.count.set_full_text(f"{len(shown):,}" if shown else "")

    def _totals(self, invoices: list[Invoice]) -> None:
        """The bar under the table: what the invoices showing add up to."""
        today = dates.today()
        sums = {k: money.ZERO for k in ("unpaid", "overdue", "paid", "all")}
        for inv in invoices:
            t = money.totals(inv)
            st = document.status_of(inv, today)
            sums["all"] += t.total
            if st in ("sent", "overdue"):
                sums["unpaid"] += t.balance
            if st == "overdue":
                sums["overdue"] += t.balance
            if st == "paid":
                sums["paid"] += t.total
        b = self.business()
        cur = (b.currency if b else "$") or "$"
        for k, v in sums.items():
            self.total_values[k].setText(money.fmt(v, cur))
        late = bool(sums["overdue"])  # only what applies: Overdue only when something is
        self.total_labels["overdue"].setVisible(late)
        self.total_values["overdue"].setVisible(late)

    def _selection_count(self) -> None:
        picked = len(self.table.chosen_ids()) if len(self.table.selectedItems()) > 1 else 0
        shown = sum(1 for _r in self.table.showing_rows())
        self.count.set_full_text(f"{picked} selected" if picked > 1 else (f"{shown:,}" if shown else ""))

    def _inspector_empty(self) -> None:
        """Nothing picked: the panel slides away (still showing what was picked while it goes)."""

        def blank() -> None:
            if not self.lib.businesses:
                self.panel.show_empty(
                    "Add your profile", "", "Add Your Profile…", lambda: self.edit_business(True)
                )
            else:
                self.panel.show_empty("Nothing selected", "", "", None)
                self.panel.empty_btn.hide()

        self.dock.after_close(blank)
        self.panel.inv = None
        self.dock.set_open(False)

    def deselect(self) -> None:
        """Esc, or a click on empty space: nothing picked, the panel slides away (and a new invoice you
        didn't fill in goes away)."""
        self.flush()
        self._drop_fresh()
        t = self.table
        t._quiet = True
        t.clearSelection()
        t.setCurrentItem(None)
        t._quiet = False
        self._inspector_empty()

    # ------------------------------------------------------------------ opening
    def open(self, inv_id: str) -> None:
        """Open an invoice on the right (moving to All Invoices if this place doesn't show it)."""
        inv = self.lib.invoices.get(inv_id)
        if inv is None:
            self.toast("That's been deleted.")
            return
        if self.panel.inv is inv and self.dock.opened and self.inspector.currentWidget() is self.panel:
            return
        self.flush()
        self._drop_fresh(keep=inv_id)
        if inv_id not in self._shown_ids():
            self.search.blockSignals(True)
            self.search.clear()
            self.search.blockSignals(False)
            if not in_place(inv, self.view_key) or not self.view_menu.filter.keep(inv):
                self.view_menu.clear()
                self.view_key = "all"
                self.lib.settings["view"] = "all"
                self.sidebar.select("all")
                self.title.setText(TITLES["all"])
            self.refresh()
        self.table.select_id(inv_id)
        if inv.business_id not in self.lib.businesses and self.lib.businesses:
            inv.business_id = next(iter(self.lib.businesses))  # its profile was deleted
        self.panel.load(inv)
        self.lib.settings["current"] = inv.id
        self.inspector.setCurrentWidget(self.panel)
        self.dock.set_open(True)

    def _row_menu(self, inv_id: str, pos) -> None:
        ids = self.table.chosen_ids()
        if inv_id not in ids:
            ids = [inv_id]
        if len(ids) > 1:
            items = [("trash", f"Delete {len(ids)} Invoices…", lambda: self.delete_invoices(ids))]
        else:
            items = [
                ("copy", "Duplicate", lambda: self.duplicate(inv_id)),
                ("receipt", "Invoice…", lambda: self.show_page(inv_id)),
                ("", "-", None),
                ("trash", "Delete…", lambda: self.delete_invoices([inv_id])),
            ]
        menu(self, items).exec(pos)

    # ------------------------------------------------------------------ misc
    def toast(self, text: str) -> None:
        self.toaster.show_message(text)

    def show(self) -> None:
        """The first time: filling the screen (all of it but the menu bar and Dock). After that: the size
        and place you left it, if it still fits a screen you have (else filling the screen again)."""
        if self._restored:
            super().show()
            return
        geo = self.lib.settings.get("geometry")
        if isinstance(geo, str) and geo and self._fits_after(geo):
            super().show()
        elif self.titlebar is not None:  # the Mac: fill the free area ourselves (zooming is unreliable here)
            titlebar.fill_screen(self)
            super().show()
        else:
            self.showMaximized()

    def _fits_after(self, geo: str) -> bool:
        """Put the window back where it was; True if that lands wholly on a screen."""
        try:
            if not self.restoreGeometry(QByteArray.fromHex(geo.encode())):
                return False
        except (TypeError, ValueError):
            return False
        frame = self.frameGeometry()
        return any(
            s.availableGeometry().adjusted(-2, -2, 2, 2).contains(frame) for s in QGuiApplication.screens()
        )

    def resizeEvent(self, e):
        """The right panel gives up some width on a smaller window, so the toolbar never crowds."""
        super().resizeEvent(e)
        w = max(tokens.INSPECTOR_MIN, min(tokens.INSPECTOR_W, int(self.width() * tokens.INSPECTOR_SHARE)))
        self.dock.set_target(w)
        for i in range(self.inspector.count()):  # every right-hand panel, whatever it is
            self.inspector.widget(i).setFixedWidth(w)

    def _let_work_finish(self) -> None:
        """An update check may still be waiting on GitHub. Give it a moment; if it's still busy, quit
        without waiting for it (everything's saved by now), instead of crashing on the way out."""
        from PySide6.QtCore import QThread
        from PySide6.QtWidgets import QApplication

        busy = [t for t in self.findChildren(QThread) if t.isRunning()]
        for t in busy:
            t.wait(tokens.QUIT_WAIT_MS)
        if any(t.isRunning() for t in busy):
            log.info("quitting while a download is still running")
            QApplication.instance().setProperty("exit_now", True)

    def showEvent(self, e):
        super().showEvent(e)
        if self.titlebar is not None:
            QTimer.singleShot(0, self.titlebar.fit)

    def closeEvent(self, e):
        self.shutdown()
        super().closeEvent(e)

    def shutdown(self) -> None:
        """Save everything before quitting (and the window's size and place for next time)."""
        self.flush()
        self.assistant.shutdown()
        if not self._restored:
            self.lib.settings["geometry"] = bytes(self.saveGeometry().toHex()).decode()
        self._let_work_finish()
        try:
            self.lib.save_settings()
        except OSError:
            log.warning("couldn't save settings", exc_info=True)
