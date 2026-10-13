"""Step 3, Preview: the invoice exactly as it will print, and the ways to send it out.

The pages are drawn by doc/render.py, the same steps the PDF uses, into pictures sized to the panel.
The moon in the header turns on the Dark Page: the same page in light-on-dark colors, easier on the eyes
while you work (PDFs and prints always stay white).
The bottom bar holds Save PDF… (the one primary action), Print… and a ⋯ menu (PNG, copy as text,
open the folder). After saving, it offers Show File and, for a draft, Mark as Sent.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QToolButton,
    QWidget,
)

from cobro.doc import export
from cobro.doc.render import Page
from cobro.ui.components.widgets import StepHeader, hbox, vbox
from cobro.ui.style import theme, tokens


class PageView(QWidget):
    """Draws the pages one under another, as wide as the panel allows."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.pages: list[Page] = []
        self._images: list[QImage] = []
        self._scale = 1.0
        self.message = ""

    def set_pages(self, pages: list[Page]) -> None:
        self.pages = pages
        self._render()

    def _fit(self) -> float:
        """Pixels per point so the page fills the panel's width (with a gap each side)."""
        if not self.pages:
            return 1.0
        avail = self.width() - 2 * tokens.PAGE_GAP
        return max(0.35, min(1.8, avail / self.pages[0].size[0]))

    def _render(self) -> None:
        self._scale = self._fit()
        dpr = self.devicePixelRatioF() or 1.0
        self._images = []
        for p in self.pages:
            img = export.image(p, self._scale * dpr)
            img.setDevicePixelRatio(dpr)
            self._images.append(img)
        h = tokens.PAGE_GAP + sum(p.size[1] * self._scale + tokens.PAGE_GAP for p in self.pages)
        self.setMinimumHeight(int(h))
        self.update()

    def refit(self) -> None:
        if self.pages and abs(self._fit() - self._scale) > 0.01:
            self._render()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.pages:
            if self.message:
                p.setPen(QColor(tokens.FAINT))
                p.drawText(self.rect(), int(Qt.AlignmentFlag.AlignCenter), self.message)
            return
        y = float(tokens.PAGE_GAP)
        for page, img in zip(self.pages, self._images, strict=False):
            w, h = page.size[0] * self._scale, page.size[1] * self._scale
            x = (self.width() - w) / 2
            # a soft shadow under the paper
            for i in range(tokens.PAGE_SHADOW // 3, 0, -1):
                c = QColor(0, 0, 0, max(4, 26 - i * 3))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(c)
                p.drawRoundedRect(QRectF(x - i, y - i + 4, w + 2 * i, h + 2 * i), i, i)
            p.drawImage(QRectF(x, y, w, h), img)
            y += h + tokens.PAGE_GAP


class PreviewPanel(QFrame):
    save_pdf = Signal()
    print_wanted = Signal()
    save_png = Signal()
    copy_text = Signal()
    open_folder = Signal()
    show_file = Signal()
    mark_sent = Signal()
    dark_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.dark = False
        outer = vbox(self, 0, 0)
        header = StepHeader(3, "Preview")
        self.btn_dark = QToolButton()
        self.btn_dark.setObjectName("IconBtn")
        self.btn_dark.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dark.clicked.connect(lambda: self._toggle_dark())
        header.actions.addWidget(self.btn_dark)
        outer.addWidget(header)
        self.area = QScrollArea()
        self.area.setObjectName("PreviewArea")
        self.area.setWidgetResizable(True)
        self.area.setFrameShape(QFrame.Shape.NoFrame)
        self.area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view = PageView()
        self.area.setWidget(self.view)
        self.area.viewport().setAutoFillBackground(True)
        self.area.viewport().setObjectName("PreviewArea")
        outer.addWidget(self.area, 1)

        bottom = QFrame()
        bottom.setObjectName("PanelBottom")
        row = hbox(bottom, tokens.SPACE_4, tokens.SPACE_2)
        self.status = QLabel()
        self.status.setObjectName("Muted")
        row.addWidget(self.status, 1)
        self.btn_show = QPushButton("Show File")
        self.btn_show.setObjectName("Ghost")
        self.btn_show.clicked.connect(self.show_file.emit)
        self.btn_sent = QPushButton("Mark as Sent")
        self.btn_sent.setObjectName("Ghost")
        self.btn_sent.setToolTip("Set this invoice to Sent, so it's counted as unpaid until it's paid")
        self.btn_sent.clicked.connect(self.mark_sent.emit)
        row.addWidget(self.btn_show)
        row.addWidget(self.btn_sent)
        self.btn_more = QToolButton()
        self.btn_more.setObjectName("IconBtn")
        self.btn_more.setIcon(theme.icon("more", theme.MUTED))
        self.btn_more.setToolTip("More ways to send it")
        self.btn_more.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        from PySide6.QtWidgets import QMenu

        m = QMenu(self.btn_more)
        m.addAction(theme.menu_icon("image"), "Save as PNG…", self.save_png.emit)
        m.addAction(theme.menu_icon("copy"), "Copy as Text", self.copy_text.emit)
        m.addSeparator()
        m.addAction(theme.menu_icon("folder"), "Open Invoices Folder", self.open_folder.emit)
        self.btn_more.setMenu(m)
        row.addWidget(self.btn_more)
        self.btn_print = QPushButton("Print…")
        self.btn_print.setIcon(theme.icon("printer", theme.TEXT))
        self.btn_print.clicked.connect(self.print_wanted.emit)
        row.addWidget(self.btn_print)
        self.btn_pdf = QPushButton("Save PDF…")
        self.btn_pdf.setObjectName("Primary")
        self.btn_pdf.clicked.connect(self.save_pdf.emit)
        row.addWidget(self.btn_pdf)
        outer.addWidget(bottom)
        self.saved_hint(None, False)
        self.set_dark(False)

        self._refit = QTimer(self)
        self._refit.setSingleShot(True)
        self._refit.setInterval(120)
        self._refit.timeout.connect(self.view.refit)

    def set_dark(self, on: bool) -> None:
        self.dark = on
        self.btn_dark.setIcon(theme.icon("sun" if on else "moon", theme.MUTED))
        self.btn_dark.setToolTip(
            "Show the page in white, exactly as it prints"
            if on
            else "Dark Page: easier on the eyes while you work. PDFs and prints stay white."
        )

    def _toggle_dark(self) -> None:
        self.set_dark(not self.dark)
        self.dark_changed.emit(self.dark)

    def set_pages(self, pages: list[Page]) -> None:
        self.view.message = ""
        self.view.set_pages(pages)
        for b in (self.btn_pdf, self.btn_print, self.btn_more):
            b.setEnabled(bool(pages))

    def clear(self, message: str) -> None:
        self.view.message = message
        self.view.set_pages([])
        for b in (self.btn_pdf, self.btn_print, self.btn_more):
            b.setEnabled(False)
        self.saved_hint(None, False)

    def saved_hint(self, name: str | None, offer_sent: bool) -> None:
        self.status.setText(f"Saved {name}" if name else "")
        self.btn_show.setVisible(bool(name))
        self.btn_sent.setVisible(bool(name) and offer_sent)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._refit.start()

    def showEvent(self, e):
        super().showEvent(e)
        self._refit.start()
