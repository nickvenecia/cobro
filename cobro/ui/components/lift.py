"""Reordering a stack of cards by dragging a grip, drawn live: the card lifts and follows the pointer, and the
others ease apart to open a gap where it will land (like the Finder or Reminders).

While a card is lifted the stack shows a drawing of itself (every card drawn once into a picture, then just
moved), so the slide stays smooth; the real cards come back when it's let go. Letting go drops it in the gap;
Esc puts it back where it was. Near the top or bottom of the scroll area, the list scrolls.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QScrollArea, QWidget

from cobro.ui.style import theme, tokens

WIDGET_MAX = 16_777_215  # Qt's "no limit" for a widget's height


class Grip(QWidget):
    """Six dots you drag a card by. Says where the pointer is while it's held; Esc while dragging cancels."""

    pressed = Signal(QPoint)  # global position
    moved = Signal(QPoint)
    released = Signal(bool)  # True: Esc was pressed (put it back)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(tokens.GRIP_W, tokens.SMALL_H)
        self.active = True
        self._held = False
        self.set_active(True)

    def set_active(self, on: bool) -> None:
        """Only a stack of two or more can be reordered; otherwise the grip keeps its room but shows nothing."""
        self.active = on
        self.setCursor(Qt.CursorShape.OpenHandCursor if on else Qt.CursorShape.ArrowCursor)
        self.setToolTip("Drag to reorder" if on else "")
        self.update()

    def paintEvent(self, _e):
        if not self.active:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.qcolor(tokens.FAINT))
        c = QPointF(self.rect().center())
        gap = tokens.GRIP_GAP
        for dx in (-gap / 2, gap / 2):
            for dy in (-gap, 0, gap):
                p.drawEllipse(QPointF(c.x() + dx, c.y() + dy), tokens.GRIP_DOT, tokens.GRIP_DOT)
        p.end()

    def mousePressEvent(self, e):
        if not self.active or e.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(e)
            return
        e.accept()  # the moves and the release come back here
        self._held = True
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        self.grabKeyboard()  # for Esc
        self.pressed.emit(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        if self._held:
            self.moved.emit(e.globalPosition().toPoint())

    def mouseReleaseEvent(self, e):
        if self._held and e.button() == Qt.MouseButton.LeftButton:
            self._let_go(False)

    def keyPressEvent(self, e):
        if self._held and e.key() == Qt.Key.Key_Escape:
            self._let_go(True)
            return
        super().keyPressEvent(e)

    def _let_go(self, cancelled: bool) -> None:
        self._held = False
        self.releaseKeyboard()
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.released.emit(cancelled)


class StackLift(QWidget):
    """Drawn over `box` (the widget holding the cards, top to bottom) while one card is dragged.
    `finish()` gives the card's new place (or None if it stays) and puts the real cards back."""

    def __init__(
        self,
        box: QWidget,
        cards: list[QWidget],
        moving: QWidget,
        press: QPoint,
        spacing: int,
        scroll: QScrollArea | None = None,
    ):
        super().__init__(box)
        self.box, self.cards, self.moving, self.scroll = box, cards, moving, scroll
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.rest = [c for c in cards if c is not moving]
        geo = {id(c): c.geometry() for c in cards}
        self.h = {id(c): geo[id(c)].height() for c in cards}
        self.pix: dict[int, QPixmap] = {id(c): c.grab() for c in cards}  # each card drawn once
        self.top = min((geo[id(c)].top() for c in cards), default=0)
        self.gap = self.h[id(moving)] + spacing
        self.base: list[float] = []  # where each other card sits with the moving one taken out
        y = float(self.top)
        for c in self.rest:
            self.base.append(y)
            y += self.h[id(c)] + spacing
        self.end_y = y
        self.cur = {id(c): float(geo[id(c)].top()) for c in self.rest}  # where each is drawn now
        local = box.mapFromGlobal(press)
        self.grab_dy = local.y() - geo[id(moving)].top()
        self.pointer_y = float(local.y())
        self.start_k = cards.index(moving)
        self.k = self.start_k
        self.slot_y = float(self._slot(self.k))
        # the stack keeps its height while the real cards hide behind the drawing
        self._height = box.height()
        box.setFixedHeight(self._height)
        for c in cards:
            c.hide()
        self.setGeometry(box.rect())
        self.show()
        self.raise_()
        self.timer = QTimer(self, interval=tokens.LIFT_STEP_MS, timeout=self._step)
        self.timer.start()

    # ------------------------------------------------------------------ where it lands
    def _slot(self, k: int) -> float:
        return self.base[k] if k < len(self.rest) else self.end_y

    def _target_k(self) -> int:
        center = self.pointer_y - self.grab_dy + self.h[id(self.moving)] / 2
        return sum(1 for i, c in enumerate(self.rest) if self.base[i] + self.h[id(c)] / 2 < center)

    def move_to(self, global_pos: QPoint) -> None:
        self.pointer_y = float(self.box.mapFromGlobal(global_pos).y())

    def finish(self, cancelled: bool = False) -> int | None:
        """Put the real cards back. The new place, or None (it didn't move, or Esc)."""
        self.timer.stop()
        self.box.setMinimumHeight(0)
        self.box.setMaximumHeight(WIDGET_MAX)
        for c in self.cards:
            c.show()
        self.hide()
        self.deleteLater()
        k = self._target_k()
        return None if cancelled or k == self.start_k else k

    # ------------------------------------------------------------------ each step
    def _step(self) -> None:
        if self.scroll is not None:  # near the top or bottom of the panel: scroll
            vp = self.scroll.viewport()
            y = vp.mapFromGlobal(self.box.mapToGlobal(QPoint(0, round(self.pointer_y)))).y()
            edge = tokens.TABLE_ROW_H
            bar = self.scroll.verticalScrollBar()
            if y < edge:
                bar.setValue(bar.value() - int((edge - y) / 2) - 1)
            elif y > vp.height() - edge:
                bar.setValue(bar.value() + int((y - vp.height() + edge) / 2) + 1)
        self.k = self._target_k()
        for i, c in enumerate(self.rest):  # each card eases towards where it should be
            target = self.base[i] + (self.gap if i >= self.k else 0)
            y = self.cur[id(c)]
            self.cur[id(c)] = y + (target - y) * tokens.LIFT_EASE if abs(target - y) > 0.5 else float(target)
        slot = self._slot(self.k)
        self.slot_y = (
            self.slot_y + (slot - self.slot_y) * tokens.LIFT_EASE if abs(slot - self.slot_y) > 0.5 else slot
        )
        self.update()  # the card follows the pointer every step

    # ------------------------------------------------------------------ drawing
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        # the gap: a soft slot where it will land
        slot = QRectF(0, self.slot_y, w, self.h[id(self.moving)])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.qcolor(tokens.CHIP))
        p.drawRoundedRect(slot, tokens.RADIUS_LG, tokens.RADIUS_LG)
        for c in self.rest:
            p.drawPixmap(QPointF(0, self.cur[id(c)]), self.pix[id(c)])
        self._paint_card(p, self.pointer_y - self.grab_dy, w)
        p.end()

    def _paint_card(self, p: QPainter, y: float, w: float) -> None:
        """The lifted card: raised, with a soft shadow and an accent edge, following the pointer."""
        card = QRectF(0, y, w, self.h[id(self.moving)])
        shadow = theme.qcolor(tokens.GLASS_SHADOW)
        for i in range(tokens.LIFT_SHADOW_STEPS, 0, -1):  # a soft shadow: rings fading outwards
            c = QColor(shadow)
            c.setAlphaF(shadow.alphaF() * 0.5 / i)
            grow = i * 1.5
            ring = QPainterPath()
            ring.addRoundedRect(
                card.adjusted(-grow, -grow + 2, grow, grow + 3),
                tokens.RADIUS_LG + grow,
                tokens.RADIUS_LG + grow,
            )
            p.fillPath(ring, c)
        path = QPainterPath()
        path.addRoundedRect(card, tokens.RADIUS_LG, tokens.RADIUS_LG)
        p.fillPath(path, theme.qcolor(tokens.RAISED))
        p.save()
        p.setClipPath(path)
        p.drawPixmap(QPointF(0, y), self.pix[id(self.moving)])
        p.restore()
        p.setPen(theme.qcolor(tokens.ACCENT_EDGE))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
