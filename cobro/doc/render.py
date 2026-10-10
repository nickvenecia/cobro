"""Lay out an invoice into pages of drawing steps, then paint them on any device.

layout() works in points on the paper (Letter is 612 × 792) and returns a list of Pages. Each Page
is a list of simple steps (text in a box, a filled box, a line, the logo). paint() replays one page
on a QPainter that has been scaled so one point = one page unit; the on-screen preview, the PDF, the
PNG and the printer all use the same steps, so they always match.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QImageReader, QPainter, QPen
from PySide6.QtSvg import QSvgRenderer

from ..core.document import InvoiceView
from ..core.looks import INK, INK_SOFT, RULE, Resolved
from .fonts import FontSpec, make, metrics

LEFT = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
RIGHT = int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
CENTER = int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
WRAP = int(Qt.TextFlag.TextWordWrap)

MARGIN = 48.0
LABEL_SPACING = 0.14  # letter-spacing of the small capital labels


# ---------------------------------------------------------------------------- drawing steps
@dataclass
class Text:
    rect: QRectF
    text: str
    font: FontSpec
    color: str
    flags: int = LEFT


@dataclass
class Fill:
    rect: QRectF
    color: str
    radius: float = 0.0


@dataclass
class Line:
    a: QPointF
    b: QPointF
    width: float
    color: str


@dataclass
class Logo:
    rect: QRectF
    path: Path


@dataclass
class Page:
    size: tuple[float, float]
    steps: list = field(default_factory=list)


# ---------------------------------------------------------------------------- logo files
def logo_size(path: Path) -> tuple[float, float] | None:
    """Width and height of a logo file (SVG or a picture), or None if it can't be read."""
    if not path.is_file():
        return None
    if path.suffix.lower() == ".svg":
        r = QSvgRenderer(str(path))
        if not r.isValid():
            return None
        s = r.defaultSize()
        return (float(s.width()), float(s.height())) if s.width() > 0 and s.height() > 0 else (1.0, 1.0)
    reader = QImageReader(str(path))
    s = reader.size()
    if s.width() > 0 and s.height() > 0:
        return float(s.width()), float(s.height())
    return None


def _draw_logo(p: QPainter, step: Logo) -> None:
    if step.path.suffix.lower() == ".svg":
        r = QSvgRenderer(str(step.path))
        if r.isValid():
            r.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
            r.render(p, step.rect)
        return
    img = QImage(str(step.path))
    if not img.isNull():
        p.drawImage(step.rect, img)


# ---------------------------------------------------------------------------- measuring
def text_h(text: str, spec: FontSpec, width: float) -> float:
    if not text:
        return 0.0
    fm = metrics(spec)
    r = fm.boundingRect(QRectF(0, 0, width, 1e6), LEFT | WRAP, text)
    return max(r.height(), fm.lineSpacing())


def text_w(text: str, spec: FontSpec) -> float:
    return metrics(spec).horizontalAdvance(text)


class _Pages:
    """A cursor that adds steps to the current page and starts new pages."""

    def __init__(self, size: tuple[float, float]):
        self.size = size
        self.pages: list[Page] = [Page(size)]
        self.y = MARGIN

    @property
    def steps(self) -> list:
        return self.pages[-1].steps

    @property
    def bottom(self) -> float:
        return self.size[1] - MARGIN - 14  # leaves room for the footer

    def fits(self, h: float) -> bool:
        return self.y + h <= self.bottom

    def new_page(self) -> None:
        self.pages.append(Page(self.size))
        self.y = MARGIN

    def text(
        self,
        x: float,
        y: float,
        w: float,
        text: str,
        spec: FontSpec,
        color: str,
        flags: int = LEFT,
    ) -> float:
        """Add wrapped text; returns its height."""
        if not text:
            return 0.0
        h = text_h(text, spec, w)
        self.steps.append(Text(QRectF(x, y, w, h + 1), text, spec, color, flags | WRAP))
        return h


# ---------------------------------------------------------------------------- the layout
def layout(v: InvoiceView, look: Resolved, logo: Path | None = None) -> list[Page]:
    W, H = look.page
    cw = W - 2 * MARGIN
    x0 = MARGIN
    out = _Pages((W, H))

    body = FontSpec(look.body, 9.5)
    body_soft = FontSpec(look.body, 9)
    body_strong = FontSpec(look.body, 9.5, 600)
    label = FontSpec(look.body, 6.8, 600, LABEL_SPACING)
    nums = FontSpec(look.numbers, 9.2)
    band = look.header == "band"
    on = look.on_accent if band else INK
    on_soft = look.on_accent if band else INK_SOFT

    # ------------------------------------------------ header: logo + name on the left, amount on the right
    top = MARGIN * (0.85 if band else 1.0)
    right_w = 200.0
    left_w = cw - right_w - 24
    logo_w = logo_h = 0.0
    dims = logo_size(logo) if logo else None
    if dims:
        logo_h = look.logo_h
        logo_w = min(logo_h * dims[0] / dims[1], left_w * (0.55 if look.name_with_logo else 1.0))
        logo_h = logo_w * dims[1] / dims[0]
    show_name = bool(v.name) and (look.name_with_logo or not dims)
    name_text = v.name.upper() if look.caps else v.name
    nx = x0 + (logo_w + 14 if dims and show_name else 0)
    nw = x0 + left_w - nx
    size = 26.0
    while size > 15 and text_w(name_text, FontSpec(look.heading, size, 800)) > nw:
        size -= 1
    name_spec = FontSpec(look.heading, size, 800, 0.01 if look.caps else 0)
    tag_spec = FontSpec(look.body, 7.6, 600, 0.13)
    name_h = text_h(name_text, name_spec, nw) if show_name else 0.0
    tag_text = v.tagline.upper()
    tag_h = text_h(tag_text, tag_spec, nw if show_name else left_w)
    block_h = name_h + (6 + tag_h if tag_h and show_name else 0)

    steps_before_band = len(out.steps)
    if dims:
        out.steps.append(Logo(QRectF(x0, top, logo_w, logo_h), logo))
    if show_name:
        by = top + max(0.0, (logo_h - block_h) / 2) if dims else top
        out.text(nx, by, nw, name_text, name_spec, on)
        if tag_h:
            out.text(nx, by + name_h + 6, nw, tag_text, tag_spec, on_soft)
        left_h = max(logo_h, block_h)
    else:
        left_h = logo_h
        if tag_h:
            out.text(x0, top + logo_h + 8, left_w, tag_text, tag_spec, on_soft)
            left_h += 8 + tag_h

    rx = x0 + cw - right_w
    ry = top
    ry += out.text(rx, ry, right_w, v.big_label.upper(), label, on_soft, RIGHT) + 4
    amount_spec = FontSpec(look.heading, 25, 700)
    if text_w(v.big_amount, amount_spec) > right_w:
        amount_spec = FontSpec(look.heading, 19, 700)
    ry += (
        out.text(
            rx,
            ry,
            right_w,
            v.big_amount,
            amount_spec,
            on if band else look.accent,
            RIGHT,
        )
        + 3
    )
    ry += out.text(rx, ry, right_w, v.big_note, body_soft, on, RIGHT)
    header_h = max(left_h, ry - top)

    if band:
        band_h = top + header_h + MARGIN * 0.7
        out.steps.insert(steps_before_band, Fill(QRectF(0, 0, W, band_h), look.band))
        out.y = band_h + 22
    else:
        out.y = top + header_h + 26

    # ------------------------------------------------ the strip: Invoice / Issued / Terms / Due
    y = out.y
    out.steps.append(Line(QPointF(x0, y), QPointF(x0 + cw, y), 1.6, INK))
    col = cw / 4
    label_h = text_h("X", label, col)
    val_h = text_h("X", nums, col)
    strip_h = 8 + label_h + 3 + val_h + 8
    for i, (k, val) in enumerate(v.meta):
        cx = x0 + i * col + (12 if i else 0)
        if i:
            out.steps.append(
                Line(
                    QPointF(x0 + i * col, y + 6),
                    QPointF(x0 + i * col, y + strip_h - 6),
                    0.6,
                    RULE,
                )
            )
        out.text(cx, y + 8, col - 16, k.upper(), label, INK_SOFT)
        out.text(cx, y + 8 + label_h + 3, col - 16, val, nums, INK)
    out.steps.append(Line(QPointF(x0, y + strip_h), QPointF(x0 + cw, y + strip_h), 0.6, RULE))
    out.y = y + strip_h + 22

    # ------------------------------------------------ who: Bill To / From / Project
    columns: list[tuple[str, str, list[str]]] = [
        ("Bill To", v.bill_to or "Client name", v.bill_lines),
        ("From", v.name, v.from_lines),
    ]
    if v.project or v.project_lines:
        columns.append(("Project", v.project, v.project_lines))
    gap = 20.0
    pw = (cw - gap * (len(columns) - 1)) / len(columns)
    tallest = 0.0
    for i, (k, name, lines) in enumerate(columns):
        cx = x0 + i * (pw + gap)
        cy = out.y
        cy += out.text(cx, cy, pw, k.upper(), label, INK_SOFT) + 4
        if name:
            cy += out.text(cx, cy, pw, name, body_strong, INK if v.bill_to or i else INK_SOFT) + 2
        for line in lines:
            cy += out.text(cx, cy, pw, line, body_soft, INK_SOFT)
        tallest = max(tallest, cy - out.y)
    out.y += tallest + 24

    # ------------------------------------------------ line items
    qty_w, rate_w, amt_w = 34.0, 78.0, 84.0
    desc_w = cw - qty_w - rate_w - amt_w - 3 * 14
    cols_x = (x0, x0 + desc_w + 14, x0 + desc_w + 14 + qty_w + 14, x0 + cw - amt_w)
    detail_spec = FontSpec(look.body, 8.6)

    def table_header() -> None:
        hy = out.y
        h = text_h("X", label, 80)
        out.text(cols_x[0], hy, desc_w, "DESCRIPTION", label, INK_SOFT)
        out.text(cols_x[1], hy, qty_w, "QTY", label, INK_SOFT, RIGHT)
        out.text(cols_x[2], hy, rate_w, "RATE", label, INK_SOFT, RIGHT)
        out.text(cols_x[3], hy, amt_w, "AMOUNT", label, INK_SOFT, RIGHT)
        out.y = hy + h + 7
        out.steps.append(Line(QPointF(x0, out.y), QPointF(x0 + cw, out.y), 1.0, INK))

    def continued() -> None:
        out.new_page()
        out.text(x0, out.y, cw, f"Invoice {v.number} (continued)", body_soft, INK_SOFT)
        out.y += 22

    table_header()
    rows = v.rows or []
    if not rows:
        out.y += 10
        out.y += (
            out.text(
                x0,
                out.y,
                desc_w,
                "Add line items to see them here.",
                body_soft,
                INK_SOFT,
            )
            + 10
        )
        out.steps.append(Line(QPointF(x0, out.y), QPointF(x0 + cw, out.y), 0.6, RULE))
    for r in rows:
        dh = text_h(r.description, body_strong, desc_w) if r.description else 0.0
        th = text_h(r.details, detail_spec, desc_w) if r.details else 0.0
        row_h = 10 + max(dh + (2 + th if th else 0), text_h("X", nums, 80)) + 10
        if not out.fits(row_h):
            continued()
            table_header()
        ty = out.y + 10
        if r.description:
            out.text(cols_x[0], ty, desc_w, r.description, body_strong, INK)
        if r.details:
            out.text(
                cols_x[0],
                ty + (dh + 2 if dh else 0),
                desc_w,
                r.details,
                detail_spec,
                INK_SOFT,
            )
        out.text(cols_x[1], ty, qty_w, r.qty, nums, INK, RIGHT)
        out.text(cols_x[2], ty, rate_w, r.rate, nums, INK, RIGHT)
        out.text(cols_x[3], ty, amt_w, r.amount, nums, INK, RIGHT)
        out.y += row_h
        out.steps.append(Line(QPointF(x0, out.y), QPointF(x0 + cw, out.y), 0.6, RULE))

    # ------------------------------------------------ totals (kept together)
    tw = 236.0
    tx = x0 + cw - tw
    row_h = text_h("X", body, tw) + 7
    bal_spec = FontSpec(look.numbers, 15, 700)
    bal_h = max(text_h("X", bal_spec, tw), row_h)
    need = 12 + len(v.totals) * row_h + 8 + bal_h
    if not out.fits(need):
        continued()
    ty = out.y + 12
    for k, val in v.totals:
        out.text(tx, ty, tw * 0.6, k, body, INK_SOFT)
        out.text(tx + tw * 0.4, ty, tw * 0.6, val, nums, INK, RIGHT)
        ty += row_h
    ty += 2
    out.steps.append(Line(QPointF(tx, ty), QPointF(tx + tw, ty), 1.6, INK))
    ty += 8
    out.text(tx, ty + (bal_h - row_h) / 2 + 2, tw * 0.5, v.balance_label, body_strong, INK)
    out.text(tx + tw * 0.3, ty, tw * 0.7, v.balance, bal_spec, look.accent, RIGHT)
    out.y = ty + bal_h

    # ------------------------------------------------ payment + terms boxes (kept together)
    boxes = [(k, t) for k, t in (("How to Pay", v.payment), ("Terms", v.terms_text)) if t]
    if boxes:
        bw = (cw - 18) / 2
        pad = 12.0
        box_text = FontSpec(look.body, 8.6)
        heights = [
            pad + text_h("X", label, bw) + 6 + text_h(t, box_text, bw - 2 * pad) + pad for _, t in boxes
        ]
        bh = max(heights)
        if not out.fits(28 + bh):
            out.new_page()
        by = out.y + 28
        for i, (k, t) in enumerate(boxes):
            bx = x0 + i * (bw + 18)
            out.steps.append(Fill(QRectF(bx, by, bw, bh), look.tint, 3))
            ly = by + pad
            ly += out.text(bx + pad, ly, bw - 2 * pad, k.upper(), label, INK_SOFT) + 6
            out.text(bx + pad, ly, bw - 2 * pad, t, box_text, INK)
        out.y = by + bh

    # ------------------------------------------------ footer on every page
    total = len(out.pages)
    foot = FontSpec(look.body, 8)
    note_w = min(text_w(v.note, foot) + 2, cw * 0.45) if v.note else 0.0
    page_w = text_w(f"Page {total} of {total}", foot) + 2 if total > 1 else 0.0
    # the last page is the fullest row: note, then the page number, then the contact line on the right
    used = note_w + (16 if note_w else 0) + page_w + (16 if page_w else 0)
    room = cw - used
    fspec = foot
    while v.footer and fspec.size > 6.2 and text_w(v.footer, fspec) > room:
        fspec = FontSpec(look.body, fspec.size - 0.3)
    footer = metrics(fspec).elidedText(v.footer, Qt.TextElideMode.ElideLeft, room) if v.footer else ""
    for n, page in enumerate(out.pages, start=1):
        fy = H - MARGIN + 4
        page.steps.append(Line(QPointF(x0, fy), QPointF(x0 + cw, fy), 0.6, RULE))
        px = x0
        if n == total and v.note:
            note = metrics(foot).elidedText(v.note, Qt.TextElideMode.ElideRight, note_w)
            page.steps.append(Text(QRectF(x0, fy + 8, note_w, 14), note, foot, INK_SOFT, LEFT))
            px = x0 + note_w + 16
        if total > 1:
            page.steps.append(
                Text(
                    QRectF(px, fy + 8, page_w, 14),
                    f"Page {n} of {total}",
                    foot,
                    INK_SOFT,
                    LEFT,
                )
            )
        if footer:
            page.steps.append(
                Text(
                    QRectF(x0 + cw - room, fy + 8, room, 14),
                    footer,
                    fspec,
                    INK_SOFT,
                    RIGHT,
                )
            )
    return out.pages


# ---------------------------------------------------------------------------- painting
def paint(p: QPainter, page: Page) -> None:
    """Draw one page. The painter must already be scaled so 1 unit = 1 point on the paper."""
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    p.fillRect(QRectF(0, 0, *page.size), QColor("#FFFFFF"))
    device = p.device()
    for s in page.steps:
        if isinstance(s, Fill):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(s.color))
            if s.radius:
                p.drawRoundedRect(s.rect, s.radius, s.radius)
            else:
                p.drawRect(s.rect)
        elif isinstance(s, Line):
            pen = QPen(QColor(s.color))
            pen.setWidthF(s.width)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.drawLine(s.a, s.b)
        elif isinstance(s, Text):
            p.setFont(make(s.font, device))
            p.setPen(QColor(s.color))
            # a hair wider than measured, so rounding on another device never re-wraps a line
            r = QRectF(s.rect)
            if s.flags & int(Qt.AlignmentFlag.AlignRight):
                r.setLeft(r.left() - 2)
            else:
                r.setWidth(r.width() + 2)
            p.drawText(r, s.flags, s.text)
        elif isinstance(s, Logo):
            _draw_logo(p, s)
    p.restore()
