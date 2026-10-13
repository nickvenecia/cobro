"""The big tables in the middle: your invoices (or your clients). Click a row to edit it on the right.

Every column sorts (newest first to start). The list is divided by month or by client (or not at all), each
band with its total; click a band to fold it. Status reads at a glance: Draft grey, Sent amber, Overdue red,
Paid green. Right-click a row for Duplicate, Invoice… and Delete….
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QMenu,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from saldo.core import billing, dates, document, money
from saldo.core.model import Invoice
from saldo.core.store import Library
from saldo.ui.style import theme, tokens
from saldo.ui.window.common import STATUS_COLORS, STATUS_WORDS

ID = Qt.ItemDataRole.UserRole
SORT = Qt.ItemDataRole.UserRole + 1
HAY = Qt.ItemDataRole.UserRole + 2  # every word a search can match
HEAD = Qt.ItemDataRole.UserRole + 3  # a band row: its place in the list
OPEN = Qt.ItemDataRole.UserRole + 4  # a band is open
FOLD = Qt.ItemDataRole.UserRole + 5  # a band's key, for remembering it folded

RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

# the columns: key, title, width (0 = takes the rest), alignment
COLUMNS = [
    ("number", "Invoice", tokens.COL_W["number"], None),
    ("client", "Client", 0, None),
    ("project", "Project", tokens.COL_W["project"], None),
    ("issued", "Issued", tokens.COL_W["issued"], None),
    ("due", "Due", tokens.COL_W["due"], None),
    ("status", "Status", tokens.COL_W["status"], None),
    ("total", "Amount", tokens.COL_W["total"], RIGHT),
]
COL = {key: n for n, (key, *_rest) in enumerate(COLUMNS)}
CLIENT_COLUMNS = [
    ("name", "Client", 0, None),
    ("contact", "Attention", tokens.COL_W["contact"], None),
    ("email", "Email", tokens.COL_W["email"], None),
    ("count", "Invoices", tokens.COL_W["count"], RIGHT),
    ("owed", "Unpaid", tokens.COL_W["balance"], RIGHT),
    ("billed", "Billed", tokens.COL_W["total"], RIGHT),
]
DIVIDES = [("month", "Month", ""), ("client", "Client", ""), ("none", "No Dividers", "")]


class Row(QTreeWidgetItem):
    """Sorts by the hidden sort key of the clicked column (numbers as numbers, words as words)."""

    def __lt__(self, other):
        tree = self.treeWidget()
        col = tree.sortColumn() if tree else 0
        ha, hb = self.data(0, HEAD), other.data(0, HEAD)
        if ha is not None and hb is not None:  # bands keep their order whichever way you sort
            descending = (
                tree is not None and tree.header().sortIndicatorOrder() == Qt.SortOrder.DescendingOrder
            )
            return ha > hb if descending else ha < hb
        a, b = self.data(col, SORT), other.data(col, SORT)
        if a is None or b is None:
            return (self.text(col) or "").casefold() < (other.text(col) or "").casefold()
        if isinstance(a, str) or isinstance(b, str):
            return str(a).casefold() < str(b).casefold()
        return a < b


class RowPainter(QStyledItemDelegate):
    """Every row's highlight, drawn once across the whole row as one rounded shape (hover, selected, and the
    bands' accent tint, a step brighter under the mouse), the way the Mac's lists do it.
    The stylesheet leaves cells clear so nothing paints over it."""

    def _ends(self, option) -> tuple[int, int]:
        """Where the whole row starts and ends (the first column showing to the far edge)."""
        view = self.parent()
        left, right = option.rect.left(), option.rect.right()
        if view is not None:
            head = view.header()
            for v in range(head.count()):  # the first column showing starts the row
                c = head.logicalIndex(v)
                if not head.isSectionHidden(c):
                    left = head.sectionViewportPosition(c)
                    break
            right = view.viewport().width()
        return left, right

    def row_shape(self, painter, option, fill: QColor) -> None:
        left, right = self._ends(option)
        i = tokens.ROW_INSET
        r = QRectF(left + 1, option.rect.top() + i, right - left - 2, option.rect.height() - 2 * i)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setClipRect(option.rect)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill)
        painter.drawRoundedRect(r, tokens.ROW_R, tokens.ROW_R)
        painter.restore()

    def _band(self, painter, option, row0) -> None:
        """A band's chevron and name, across every column up to its total. Each cell draws its own slice,
        so a cell repainted alone (under the mouse) still shows its part of the name."""
        left, right = self._ends(option)
        view = self.parent()
        if view is not None and not view.isColumnHidden(COL["total"]):
            right = view.header().sectionViewportPosition(COL["total"])
        painter.save()
        painter.setClipRect(option.rect)
        self._chevron(
            painter, QRectF(left, option.rect.top(), 0, option.rect.height()), bool(row0.data(OPEN))
        )
        x = left + tokens.SPACE_2 + tokens.CHEVRON + tokens.SPACE_2
        f = row0.data(Qt.ItemDataRole.FontRole)
        if f is not None:
            painter.setFont(f)
        painter.setPen(theme.qcolor(tokens.DIVIDER_TEXT))
        room = max(0, right - x - tokens.SPACE_2)
        text = painter.fontMetrics().elidedText(
            row0.data(Qt.ItemDataRole.DisplayRole) or "", Qt.TextElideMode.ElideRight, room
        )
        painter.drawText(
            QRectF(x, option.rect.top(), room, option.rect.height()),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            text,
        )
        painter.setPen(theme.qcolor(tokens.BORDER))  # the hairline every cell has (the stylesheet's)
        painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())
        painter.restore()

    @staticmethod
    def _chevron(painter, rect, open_: bool) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(theme.qcolor(tokens.DIVIDER_TEXT), tokens.LINE_STROKE)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        c = QPointF(rect.left() + tokens.SPACE_2 + tokens.CHEVRON / 2, rect.center().y())
        r = tokens.CHEVRON / 2
        if open_:
            pts = [
                QPointF(c.x() - r, c.y() - r / 2),
                QPointF(c.x(), c.y() + r / 2),
                QPointF(c.x() + r, c.y() - r / 2),
            ]
        else:
            pts = [
                QPointF(c.x() - r / 2, c.y() - r),
                QPointF(c.x() + r / 2, c.y()),
                QPointF(c.x() - r / 2, c.y() + r),
            ]
        painter.drawPolyline(pts)
        painter.restore()

    def paint(self, painter, option, index):
        row0 = index.siblingAtColumn(0)
        band = row0.data(HEAD) is not None
        hover = bool(option.state & QStyle.StateFlag.State_MouseOver)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        if band:
            self.row_shape(painter, option, theme.qcolor(tokens.DIVIDER_HOVER if hover else tokens.DIVIDER))
        elif selected:
            self.row_shape(painter, option, theme.qcolor(tokens.CARD_SELECTED))
        elif hover:
            self.row_shape(painter, option, theme.qcolor(tokens.ROW_HOVER))
        opt = QStyleOptionViewItem(option)
        opt.state &= ~(
            QStyle.StateFlag.State_MouseOver
            | QStyle.StateFlag.State_Selected
            | QStyle.StateFlag.State_HasFocus
        )
        if band and index.column() != COL["total"]:
            self._band(painter, option, row0)
            return
        super().paint(painter, opt, index)


def _month(iso: str) -> str:
    d = dates.parse(iso)
    return f"{d:%Y-%m}" if d else ""


def _month_name(key: str) -> str:
    try:
        y, m = (int(x) for x in key.split("-"))
        return f"{date(y, m, 1):%B %Y}"
    except ValueError:
        return "No Date"


class Table(QTreeWidget):
    """What every table in the middle shares: its columns (COLUMNS: key, title, width, alignment), rows that
    sort by their hidden keys, one rounded highlight per row, picking (one row, or many with `many`), a click on
    empty space to pick nothing, Delete, search, and columns that step aside on a narrow window (GIVE_WAY)."""

    picked = Signal(str)
    menu_wanted = Signal(str, QPoint)
    delete_wanted = Signal(list)  # Delete / Backspace on the picked rows
    cleared = Signal()  # a click on empty space: nothing picked

    COLUMNS: list[tuple[str, str, int, object]] = []
    GIVE_WAY: tuple[str, ...] = ()
    NAME = ""  # the column that never gets narrower than NAME_MIN

    def __init__(self, many: bool = True, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Table")
        self.col = {key: n for n, (key, *_rest) in enumerate(self.COLUMNS)}
        self.many = many
        self.setColumnCount(len(self.COLUMNS))
        self.setHeaderLabels([c[1] for c in self.COLUMNS])
        self.setRootIsDecorated(False)
        self.setIndentation(0)
        self.setUniformRowHeights(True)
        self.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
            if many
            else QAbstractItemView.SelectionMode.SingleSelection
        )
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSortingEnabled(True)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setFrameShape(QTreeWidget.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        h = self.header()
        h.setStretchLastSection(False)
        h.setSectionsMovable(False)
        h.setHighlightSections(False)
        h.setMinimumSectionSize(tokens.SMALL_H)
        for i, (_k, _t, w, align) in enumerate(self.COLUMNS):
            if w:
                h.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                self.setColumnWidth(i, w)
            else:
                h.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            if align is not None:
                self.headerItem().setTextAlignment(i, align)
        self.setItemDelegate(RowPainter(self))
        self.setMouseTracking(True)
        self.currentItemChanged.connect(self._current)
        self._quiet = False

    # ------------------------------------------------------------------ picking
    def _current(self, cur, _prev) -> None:
        if cur is not None and not self._quiet and cur.data(0, ID):
            self.picked.emit(cur.data(0, ID))

    def _menu(self, pos) -> None:
        it = self.itemAt(pos)
        if it is not None and it.data(0, ID):
            self.menu_wanted.emit(it.data(0, ID), self.viewport().mapToGlobal(pos))

    def mousePressEvent(self, e):
        if self.itemAt(e.position().toPoint()) is None:
            self.cleared.emit()
            return
        super().mousePressEvent(e)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            ids = self.chosen_ids()
            if ids:
                self.delete_wanted.emit(ids)
            return
        if e.matches(QKeySequence.StandardKey.SelectAll):
            if self.many:
                self.select_showing()
            return
        super().keyPressEvent(e)

    def rows(self):
        """Every row with something in it (not the bands)."""
        stack = [self.invisibleRootItem()]
        while stack:
            r = stack.pop()
            for i in range(r.childCount()):
                c = r.child(i)
                if c.data(0, ID):
                    yield c
                stack.append(c)

    def showing_rows(self):
        """Rows you can see: not hidden, not inside a folded band."""

        def walk(row):
            for i in range(row.childCount()):
                r = row.child(i)
                if r.isHidden():
                    continue
                if r.data(0, ID):
                    yield r
                if r.isExpanded():
                    yield from walk(r)

        yield from walk(self.invisibleRootItem())

    def select_showing(self) -> None:
        """⌘A: everything you can see (never the bands, never hidden rows)."""
        self.clearSelection()
        for r in self.showing_rows():
            r.setSelected(True)

    def chosen_ids(self) -> list[str]:
        """The picked rows you can see, top to bottom (or the current row)."""
        ids = [r.data(0, ID) for r in self.showing_rows() if r.isSelected()]
        if not ids and self.current_id():
            ids = [self.current_id()]
        return ids

    def current_id(self) -> str:
        it = self.currentItem()
        return it.data(0, ID) if it is not None else ""

    def select_id(self, obj_id: str) -> None:
        self._quiet = True
        found = next((r for r in self.rows() if r.data(0, ID) == obj_id), None)
        if found is not None:
            p = found.parent()
            while p is not None:
                p.setExpanded(True)
                p.setData(0, OPEN, True)
                p = p.parent()
            self.setCurrentItem(found)
            self.scrollToItem(found, QAbstractItemView.ScrollHint.EnsureVisible)
        else:
            self.clearSelection()
        self._quiet = False

    # ------------------------------------------------------------------ filling
    def _fill_start(self) -> tuple[str, int, Qt.SortOrder]:
        """Before filling: what was picked and how it sorted, to put back after."""
        keep = self.current_id()
        col, order = self.sortColumn(), self.header().sortIndicatorOrder()
        self._quiet = True
        self.setSortingEnabled(False)
        self.clear()
        return keep, col, order

    def _fill_end(self, keep: str, col: int, order: Qt.SortOrder) -> None:
        self.setSortingEnabled(True)
        self.sortItems(max(0, col), order)
        self._quiet = False
        if keep:
            self.select_id(keep)

    def _cells(self, row: Row, cells: list[tuple[str, object]]) -> None:
        """A row's words and sort keys, column by column, aligned as the columns are."""
        for i, (text, sort) in enumerate(cells):
            row.setText(i, text)
            row.setData(i, SORT, sort)
            align = self.COLUMNS[i][3]
            if align is not None:
                row.setTextAlignment(i, align)
        row.setSizeHint(0, QSize(0, tokens.TABLE_ROW_H))

    def show_only(self, text: str) -> list[str]:
        """Hide rows that don't match every word of `text`. Returns the ids of the rows left showing."""
        words = text.casefold().split()
        shown: list[str] = []
        for row in self.rows():
            ok = all(w in (row.data(0, HAY) or "") for w in words)
            row.setHidden(not ok)
            if ok:
                shown.append(row.data(0, ID))
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            d = root.child(i)
            if d.data(0, HEAD) is not None:
                any_shown = any(not d.child(k).isHidden() for k in range(d.childCount()))
                d.setHidden(not any_shown)
                if words and any_shown and not d.isExpanded():
                    d.setExpanded(True)
                    d.setData(0, OPEN, True)
        return shown

    def fit(self, width: int) -> None:
        """On a narrow window, columns step aside (in GIVE_WAY's order) so the names keep NAME_MIN."""
        fixed = sum(w for _k, _t, w, _a in self.COLUMNS if w)
        for key in self.GIVE_WAY:
            self.setColumnHidden(self.col[key], False)
        room = width - tokens.SCROLL_W
        for key in self.GIVE_WAY:
            if room - fixed >= tokens.NAME_MIN:
                break
            self.setColumnHidden(self.col[key], True)
            fixed -= tokens.COL_W[key]

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.fit(self.viewport().width())


class InvoiceTable(Table):
    COLUMNS = COLUMNS
    GIVE_WAY = tokens.GIVE_WAY

    def __init__(self, parent: QWidget | None = None):
        super().__init__(True, parent)
        self.sortByColumn(COL["issued"], Qt.SortOrder.DescendingOrder)  # newest first
        self.itemClicked.connect(self._band_clicked)
        self.folded: set[str] = set()
        self.divide = "month"

    def _band_clicked(self, row, _col) -> None:
        key = row.data(0, FOLD)
        if key is None:
            return
        row.setExpanded(not row.isExpanded())
        row.setData(0, OPEN, row.isExpanded())
        (self.folded.discard if row.isExpanded() else self.folded.add)(key)

    def fill(self, lib: Library, invoices: list[Invoice], divide: str = "month") -> None:
        """Show these invoices, divided by month, client or nothing."""
        keep, col, order = self._fill_start()
        self.divide = divide if divide in {k for k, _l, _t in DIVIDES} else "month"
        today = dates.today()

        def key_of(inv: Invoice) -> str:
            if self.divide == "month":
                return _month(inv.issued)
            if self.divide == "client":
                return inv.client.name.strip()
            return ""

        bands: dict[str, Row] = {}
        sums: dict[str, Decimal] = {}
        if self.divide != "none":
            # bands keep this order however the rows sort: the newest month first, clients A to Z,
            # and invoices with no date or no client last
            found = {key_of(i) for i in invoices}
            named = sorted((k for k in found if k), key=str.casefold, reverse=self.divide == "month")
            keys = named + ([""] if "" in found else [])
            for n, key in enumerate(keys):
                d = Row(self)
                if self.divide == "month":
                    name = _month_name(key) if key else "No Date"
                else:
                    name = key or "No Client"
                d.setData(0, HEAD, n)
                d.setData(0, FOLD, f"{self.divide}/{key}")
                d.setText(0, name)
                d.setFirstColumnSpanned(False)
                d.setFlags(Qt.ItemFlag.ItemIsEnabled)
                d.setSizeHint(0, QSize(0, tokens.TABLE_ROW_H))
                f = theme.font(tokens.TEXT_MD, tokens.WEIGHT_SEMIBOLD)
                for c, (_k, _t, _w, align) in enumerate(COLUMNS):
                    d.setFont(c, f)
                    d.setForeground(c, theme.qcolor(tokens.DIVIDER_TEXT))
                    if align is not None:
                        d.setTextAlignment(c, align)
                bands[key] = d
                sums[key] = money.ZERO
        for inv in invoices:
            b = lib.businesses.get(inv.business_id)
            cur = (b.currency if b else "$") or "$"
            t = billing.totals(inv)
            tone = document.status_of(inv, today)
            due = billing.due(inv.issued, inv.terms_days)
            who = inv.client.name.strip()
            parent = bands.get(key_of(inv), self)
            row = Row(parent)
            row.setData(0, ID, inv.id)
            cells = [
                (inv.number, inv.number),
                (who or "No client yet", who.casefold() or "~"),
                (inv.project, inv.project.casefold() or "~"),
                (dates.fmt(dates.parse(inv.issued)), inv.issued),
                (dates.fmt(due) if due else "", dates.iso(due) if due else ""),
                (STATUS_WORDS[tone], ["draft", "sent", "overdue", "paid"].index(tone)),
                (money.fmt(t.total, cur), float(t.total)),
            ]
            for i, (text, sort) in enumerate(cells):
                row.setText(i, text)
                row.setData(i, SORT, sort)
                align = COLUMNS[i][3]
                if align is not None:
                    row.setTextAlignment(i, align)
            row.setSizeHint(0, QSize(0, tokens.TABLE_ROW_H))
            row.setForeground(COL["status"], theme.qcolor(getattr(tokens, STATUS_COLORS[tone])))
            for k in ("number", "project", "issued", "due"):
                row.setForeground(COL[k], theme.qcolor(tokens.MUTED))
            if not who:
                row.setForeground(COL["client"], theme.qcolor(tokens.FAINT))
            words = [
                inv.number,
                inv.client.name,
                inv.client.contact,
                inv.project,
                STATUS_WORDS[tone],
                cells[3][0],
            ]
            words += [cells[4][0]]  # the dates as they show ("Oct 13, 2026")
            words += [it.description for it in inv.items] + [money.fmt(t.total, cur)]
            row.setData(0, HAY, " ".join(words).casefold())
            if key_of(inv) in sums:
                sums[key_of(inv)] += t.total
        cur = next((b.currency for b in lib.businesses.values() if b.currency), "$")
        for key, d in bands.items():
            d.setText(COL["total"], money.fmt(sums[key], cur))
            d.setExpanded(d.data(0, FOLD) not in self.folded)
            d.setData(0, OPEN, d.isExpanded())
        self._fill_end(keep, col, order)


class ClientTable(Table):
    """Your saved clients: who they are, how many invoices you've made them, what they owe (amber while it's
    waiting, red once something's overdue) and what you've billed them in all. Click one to edit it."""

    COLUMNS = CLIENT_COLUMNS
    GIVE_WAY = tokens.CLIENT_GIVE_WAY

    def __init__(self, parent: QWidget | None = None):
        super().__init__(False, parent)
        self.sortByColumn(0, Qt.SortOrder.AscendingOrder)  # A to Z

    def fill(self, lib: Library) -> None:
        keep, col, order = self._fill_start()
        today = dates.today()
        cur = next((b.currency for b in lib.businesses.values() if b.currency), "$")
        mine = lib.invoices_by_client()
        for c in lib.clients.values():
            invoices = mine.get(c.id, [])
            owed = billed = money.ZERO
            late = False
            for inv in invoices:
                t = billing.totals(inv)
                st = document.status_of(inv, today)
                billed += t.total
                if st in ("sent", "overdue"):
                    owed += t.balance
                late = late or st == "overdue"
            row = Row(self)
            row.setData(0, ID, c.id)
            n = len(invoices)
            self._cells(
                row,
                [
                    (c.name, c.name.casefold()),
                    (c.contact, c.contact.casefold() or "~"),
                    (c.email, c.email.casefold() or "~"),
                    (str(n) if n else "", n),
                    (money.fmt(owed, cur) if owed else "", float(owed)),
                    (money.fmt(billed, cur) if billed else "", float(billed)),
                ],
            )
            for k in ("contact", "email", "count"):
                row.setForeground(self.col[k], theme.qcolor(tokens.MUTED))
            if owed:
                row.setForeground(self.col["owed"], theme.qcolor(tokens.BAD if late else tokens.WARN))
            words = [c.name, c.contact, c.email, c.address, c.code]
            row.setData(0, HAY, " ".join(words).casefold())
        self._fill_end(keep, col, order)


def menu(parent: QWidget, items: list[tuple[str, str, object]]) -> QMenu:
    m = QMenu(parent)
    for icon, text, slot in items:
        if text == "-":
            m.addSeparator()
        else:
            m.addAction(theme.menu_icon(icon), text, slot)
    return m
