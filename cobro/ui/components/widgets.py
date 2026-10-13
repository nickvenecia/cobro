"""Small reusable widgets."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

from cobro.ui.style import theme, tokens


def section_label(text: str) -> QLabel:
    """The small Title Case label above a group of controls."""
    lbl = QLabel(text)
    lbl.setObjectName("SectionLabel")
    return lbl


def hint(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Hint")
    lbl.setWordWrap(True)
    return lbl


def vbox(
    widget: QWidget | None = None,
    margins: int | tuple[int, int, int, int] = 0,
    spacing: int = tokens.SPACE_2,
) -> QVBoxLayout:
    """A vertical layout using the spacing tokens (never type raw numbers in layouts)."""
    lay = QVBoxLayout(widget) if widget is not None else QVBoxLayout()
    m = (margins,) * 4 if isinstance(margins, int) else margins
    lay.setContentsMargins(*m)
    lay.setSpacing(spacing)
    return lay


def hbox(
    widget: QWidget | None = None,
    margins: int | tuple[int, int, int, int] = 0,
    spacing: int = tokens.SPACE_2,
) -> QHBoxLayout:
    """A horizontal layout using the spacing tokens."""
    lay = QHBoxLayout(widget) if widget is not None else QHBoxLayout()
    m = (margins,) * 4 if isinstance(margins, int) else margins
    lay.setContentsMargins(*m)
    lay.setSpacing(spacing)
    return lay


class Section(QWidget):
    """A labelled group: a small Title Case label, then its controls SPACE_1 below it.

    Put Sections in a layout with spacing SPACE_3 and every panel lines up the same way.
    Hiding a Section hides its label and controls together (and the gap collapses).
    """

    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.lay = vbox(self, 0, tokens.SPACE_1)
        self.label = section_label(title)
        self.label.setVisible(bool(title))
        self.lay.addWidget(self.label)

    def add(self, item: QWidget | QHBoxLayout | QVBoxLayout) -> None:
        if isinstance(item, QWidget):
            self.lay.addWidget(item)
        else:
            self.lay.addLayout(item)

    def set_title(self, title: str) -> None:
        self.label.setText(title)
        self.label.setVisible(bool(title))


class ElidedLabel(QLabel):
    """A one-line label that cuts long text short with "…" instead of widening its panel."""

    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self._full = ""
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.set_full_text(text)

    def set_full_text(self, text: str) -> None:
        self._full = text
        self.setToolTip("")
        self._elide()

    def full_text(self) -> str:
        return self._full

    def _elide(self) -> None:
        shown = self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideRight, max(1, self.width()))
        self.setText(shown)
        self.setToolTip(self._full if shown != self._full else "")

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._elide()


class Wordmark(QLabel):
    """The "cobro." wordmark with its turquoise dot. Rich text doesn't follow the stylesheet, so the dot
    is colored again whenever the stylesheet is (a switch between light and dark)."""

    def __init__(self, object_name: str = "Wordmark", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setTextFormat(Qt.TextFormat.RichText)
        self._color_dot()

    def _color_dot(self) -> None:
        self.setText(theme.wordmark())

    def changeEvent(self, e):
        if e.type() == QEvent.Type.StyleChange:
            self._color_dot()
        super().changeEvent(e)


class IconLabel(QWidget):
    """An icon on its own, not a button (a line item's fold arrow). Clicks go through to what's under it."""

    def __init__(self, size: int = tokens.ICON_SM, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._icon = QIcon()

    def set_icon(self, icon: QIcon) -> None:
        self._icon = icon
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        self._icon.paint(p, self.rect())
        p.end()


class _FoldHeader(QPushButton):
    """The Disclosure's header: its text is cut short with "…" rather than widening the panel."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._full = ""
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

    def set_full_text(self, text: str) -> None:
        self._full = text
        self._elide()

    def _elide(self) -> None:
        room = self.width() - self.iconSize().width() - tokens.SPACE_3
        self.setText(self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideRight, max(1, room)))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._elide()


class Disclosure(QWidget):
    """A fold-away group: a header row that opens and closes the controls under it.

    Folded, the header says what's inside ("Line Items · 3 items · $2,700.00"), so nothing that changes
    the invoice is ever hidden silently. `first` drops the hairline above the top group of a panel."""

    toggled = Signal(bool)

    def __init__(self, title: str, is_open: bool = False, first: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self._title = title
        self._summary = ""
        outer = vbox(self, 0, tokens.SPACE_3)
        self.header = _FoldHeader()
        self.header.setObjectName("Disclosure")
        self.header.setProperty("first", first)
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.clicked.connect(lambda: self.set_open(not self.body.isVisibleTo(self), emit=True))
        outer.addWidget(self.header)
        self.body = QWidget()
        self.lay = vbox(self.body, 0, tokens.SPACE_3)
        outer.addWidget(self.body)
        self.set_open(is_open)

    def add(self, item: QWidget | QHBoxLayout | QVBoxLayout) -> None:
        if isinstance(item, QWidget):
            self.lay.addWidget(item)
        else:
            self.lay.addLayout(item)

    def is_open(self) -> bool:
        return self.body.isVisibleTo(self)

    def set_open(self, on: bool, emit: bool = False) -> None:
        self.body.setVisible(on)
        self.header.setIcon(theme.icon("chevron" if on else "chevron-right", theme.MUTED))
        self.header.setToolTip("Hide" if on else "Show")
        self._show_title()
        if emit:
            self.toggled.emit(on)

    def set_summary(self, text: str) -> None:
        self._summary = text.replace("&", "&&")  # a lone & would underline the next letter instead
        self._show_title()

    def _show_title(self) -> None:
        folded = not self.body.isVisibleTo(self)
        self.header.set_full_text(
            f" {self._title}" + (f"  ·  {self._summary}" if folded and self._summary else "")
        )


def repolish(w: QWidget) -> None:
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()


class Segmented(QFrame):
    """A row of mutually exclusive buttons."""

    changed = Signal(str)

    def __init__(self, items: list[tuple[str, str]], parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Seg")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(*(tokens.SEG_INSET,) * 4)
        lay.setSpacing(tokens.SEG_INSET)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: dict[str, QPushButton] = {}
        for key, label in items:
            b = QPushButton(label)
            b.setObjectName("SegBtn")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            b.clicked.connect(lambda _=False, k=key: self.changed.emit(k))
            self.group.addButton(b)
            lay.addWidget(b)
            self.buttons[key] = b

    def set_value(self, key: str) -> None:
        if key in self.buttons:
            self.buttons[key].setChecked(True)

    def value(self) -> str:
        for k, b in self.buttons.items():
            if b.isChecked():
                return k
        return ""


class Toast(QLabel):
    """A short message that floats at the bottom of its parent and fades away."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setWordWrap(True)
        self.hide()
        self._t = QTimer(self)
        self._t.setSingleShot(True)
        self._t.timeout.connect(self.hide)

    def show_message(self, text: str, ms: int = 3500) -> None:
        self.setText(text)
        self.setMaximumWidth(min(520, self.parentWidget().width() - 40))
        self.adjustSize()
        p = self.parentWidget()
        self.move((p.width() - self.width()) // 2, p.height() - self.height() - 20)
        self.raise_()
        self.show()
        self._t.start(ms)


# ------------------------------------------------------------------ dropdowns
def combo(items: list[tuple[str, str, str]], current: str) -> QComboBox:
    """The standard dropdown. items: (key, label, tooltip); the key is the item's data."""
    c = QComboBox()
    for key, label, tip in items:
        c.addItem(label, key)
        if tip:
            c.setItemData(c.count() - 1, tip, Qt.ItemDataRole.ToolTipRole)
    c.setCurrentIndex(max(0, c.findData(current)))
    c.setCursor(Qt.CursorShape.PointingHandCursor)
    return c


def set_combo(c: QComboBox, key: str) -> None:
    """Select the item with this key without firing change signals."""
    c.blockSignals(True)
    c.setCurrentIndex(max(0, c.findData(key)))
    c.blockSignals(False)


def disable_item(c: QComboBox, key: str, why: str) -> None:
    """Grey out one item and say why in its tooltip."""
    i = c.findData(key)
    item = c.model().item(i) if i >= 0 and hasattr(c.model(), "item") else None
    if item is not None:
        item.setEnabled(False)
        item.setToolTip(why)


class ComboItemDelegate(QStyledItemDelegate):
    """Draws dropdown rows: rounded highlight from the stylesheet, standard row height,
    and a thin line for separators (Qt's default painter ignores the stylesheet on macOS)."""

    ROW_H = tokens.CONTROL_H - tokens.SPACE_2
    SEP_H = tokens.SPACE_2 + 1

    @staticmethod
    def _is_separator(index) -> bool:
        return index.data(Qt.ItemDataRole.AccessibleDescriptionRole) == "separator"

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(self.SEP_H if self._is_separator(index) else max(size.height(), self.ROW_H))
        return size

    def paint(self, painter, option, index):
        if self._is_separator(index):
            y = option.rect.center().y()
            painter.save()
            painter.setPen(QColor(tokens.BORDER_STRONG))
            painter.drawLine(
                option.rect.left() + tokens.SPACE_2,
                y,
                option.rect.right() - tokens.SPACE_2,
                y,
            )
            painter.restore()
            return
        super().paint(painter, option, index)


class FitScroll(QScrollArea):
    """Scroll area whose content always matches the visible width (no clipped edges).

    The scroll bar's space is always reserved (it's invisible while there's nothing to scroll), so
    content never shifts or squeezes when a group opens. Put SCROLL_GUTTER less margin on the
    right of the content so both sides look the same."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        bar = self.verticalScrollBar()
        bar.setEnabled(False)
        bar.rangeChanged.connect(lambda lo, hi: bar.setEnabled(hi > lo))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.widget():
            self.widget().setFixedWidth(self.viewport().width())


class StepHeader(QFrame):
    """The top of each panel: a numbered step and its name ("1 Invoices", "2 Details", "3 Preview").
    All three are the same height so the panels line up; `.actions` takes buttons on the right."""

    def __init__(self, number: int, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("StepHeader")
        self.setFixedHeight(tokens.HEADER_H)
        lay = hbox(self, (tokens.SPACE_4, 0, tokens.SPACE_4, 0), tokens.SPACE_2)
        badge = QLabel(str(number))
        badge.setObjectName("StepBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(tokens.STEP_BADGE, tokens.STEP_BADGE)
        name = QLabel(title)
        name.setObjectName("StepTitle")
        lay.addWidget(badge)
        lay.addWidget(name)
        lay.addStretch(1)
        self.actions = hbox(spacing=tokens.SPACE_2)
        lay.addLayout(self.actions)


class ToggleRow(QAbstractButton):
    """An on/off setting: the label on the left, a switch on the right, the whole row clickable.
    Works like a QCheckBox (setChecked, isChecked, toggled, text)."""

    def __init__(self, text: str, checked: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(tokens.TOGGLE_ROW_H)
        self._hover = False

    def sizeHint(self) -> QSize:
        w = self.fontMetrics().horizontalAdvance(self.text()) + tokens.SPACE_3 + tokens.TOGGLE_W
        return QSize(w, tokens.TOGGLE_ROW_H)

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        on, enabled = self.isChecked(), self.isEnabled()
        r = self.rect()
        # label
        p.setPen(QColor(tokens.TEXT if enabled else tokens.FAINT))
        text_rect = r.adjusted(0, 0, -(tokens.TOGGLE_W + tokens.SPACE_3), 0)
        label = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, text_rect.width())
        p.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            label,
        )
        # switch
        tw, th = tokens.TOGGLE_W, tokens.TOGGLE_H
        track = QRectF(r.right() - tw + 1, r.center().y() - th / 2 + 1, tw - 1, th - 1)
        if on:
            fill = tokens.ACCENT_HOVER if self._hover and enabled else tokens.ACCENT
        else:
            fill = tokens.BORDER_HOVER if self._hover and enabled else tokens.BORDER_STRONG
        if not enabled:
            fill = tokens.ACCENT_OFF if on else tokens.BORDER
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(fill))
        p.drawRoundedRect(track, th / 2, th / 2)
        knob = th - 2 * tokens.TOGGLE_INSET
        x = track.right() - tokens.TOGGLE_INSET - knob if on else track.left() + tokens.TOGGLE_INSET
        p.setBrush(QColor(tokens.ON_ACCENT if on else tokens.TEXT) if enabled else QColor(tokens.FAINT))
        p.drawEllipse(QRectF(x, track.top() + tokens.TOGGLE_INSET, knob, knob))
        p.end()


class TextBox(QPlainTextEdit):
    """A multi-line text field (addresses, details, payment text) that looks like the one-line fields.
    `edited` fires on typing only, never when the window fills it in with set_text()."""

    edited = Signal()

    def __init__(
        self,
        placeholder: str = "",
        height: int = tokens.TEXT_BOX_H,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("Field")
        self.setPlaceholderText(placeholder)
        self.setFixedHeight(height)
        self.setTabChangesFocus(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._quiet = False
        self.textChanged.connect(self._changed)

    def _changed(self) -> None:
        if not self._quiet:
            self.edited.emit()

    def text(self) -> str:
        return self.toPlainText()

    def set_text(self, text: str) -> None:
        if text == self.toPlainText():
            return
        self._quiet = True
        self.setPlainText(text)
        self._quiet = False
