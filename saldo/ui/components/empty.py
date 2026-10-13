"""What shows where the table would be when there's nothing in it: the ways to start, as tiles. Each tile has
the place's own icon (the sidebar's), a name and a few words; nothing else is on the page (the title above it
already says where you are)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QWidget

from saldo.ui.components.widgets import IconLabel, hbox, vbox
from saldo.ui.style import theme, tokens


class StartTile(QFrame):
    """One way to start: an icon, what it is, a few words. A click, Space or Return picks it."""

    clicked = Signal()

    def __init__(self, icon: str, title: str, detail: str, tip: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("StartTile")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(tokens.START_TILE_W)
        if tip:
            self.setToolTip(theme.plain_tip(tip))
        lay = vbox(self, (tokens.SPACE_4, tokens.SPACE_5, tokens.SPACE_4, tokens.SPACE_5), tokens.SPACE_1)
        badge = QFrame()  # the icon, in a circle of the accent's tint
        badge.setObjectName("StartBadge")
        badge.setFixedSize(tokens.START_BADGE, tokens.START_BADGE)
        bl = vbox(badge)
        bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bl.addWidget(IconLabel(icon, "ACCENT", tokens.ICON_LG))
        lay.addWidget(badge, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addSpacing(tokens.SPACE_2)
        self.title = QLabel(title)
        self.title.setObjectName("StartTitle")
        sub = QLabel(detail)
        sub.setObjectName("StartDetail")
        for w in (self.title, sub):
            w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(w)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            e.accept()  # the release comes back here
        else:
            super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(e)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.clicked.emit()
            return
        super().keyPressEvent(e)


class EmptyPage(QWidget):
    """The empty page. `show_for()` sets its tiles."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._key: tuple = ()
        self._slots: list[Callable] = []
        self.tiles: list[StartTile] = []
        lay = vbox(self, tokens.SPACE_5, 0)
        lay.addStretch(2)
        self.tile_row = hbox(spacing=tokens.SPACE_3)
        lay.addLayout(self.tile_row)
        lay.addStretch(3)

    def show_for(self, tiles: tuple[tuple[str, str, str, str, Callable], ...]) -> None:
        """The tiles: (icon, title, detail, tooltip, what it does)."""
        self._slots = [t[4] for t in tiles]
        key = tuple(t[:4] for t in tiles)
        if key == self._key:
            return
        self._key = key
        while self.tile_row.count():
            w = self.tile_row.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        self.tiles = []
        self.tile_row.addStretch(1)
        for n, (name, label, detail, tip, _slot) in enumerate(tiles):
            tile = StartTile(name, label, detail, tip)
            tile.clicked.connect(lambda n=n: self._slots[n]())
            self.tile_row.addWidget(tile)
            self.tiles.append(tile)
        self.tile_row.addStretch(1)

    def titles(self) -> list[str]:
        return [t.title.text() for t in self.tiles]
