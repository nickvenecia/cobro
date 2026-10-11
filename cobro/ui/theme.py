"""Look and feel: colors, type, stylesheet and icons."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from .tokens import (
    ACCENT,
    ACCENT_EDGE,
    ACCENT_HOVER,
    ACCENT_OFF,
    ACCENT_OFF_TEXT,
    ACCENT_PRESS,
    ACCENT_TINT,
    BAD,
    BAD_EDGE,
    BAD_TINT,
    BAR_H,
    BG,
    BORDER,
    BORDER_CHECK,
    BORDER_HOVER,
    BORDER_STRONG,
    CARD,
    CARD_HOVER,
    CARD_SELECTED,
    CONTROL_H,
    FAINT,
    GOOD,
    HANDLE,
    ICON,
    INDICATOR,
    MUTED,
    ON_ACCENT,
    PANEL,
    PAPER,
    RADIUS,
    RADIUS_LG,
    RADIUS_SM,
    RADIUS_XS,
    RAISED,
    RAISED_HOVER,
    RAISED_PRESS,
    SCROLL_MIN,
    SCROLL_W,
    SEG_INSET,
    SMALL_H,
    SPACE_1,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    SPACE_5,
    STEP_BADGE,
    TEXT,
    TEXT_BRAND,
    TEXT_LG,
    TEXT_MD,
    TEXT_SM,
    TEXT_TITLEBAR,
    TEXT_XL,
    TEXT_XS,
    TRACK_H,
    WEIGHT_BOLD,
    WEIGHT_MEDIUM,
    WEIGHT_SEMIBOLD,
    WELL,
)

ASSETS = Path(__file__).resolve().parent.parent / "assets"
FONT_FAMILY = "Inter"
MONO = '"Menlo", "Consolas", "DejaVu Sans Mono", monospace'

# A control's box = border (1px top + bottom) + content. Padding is horizontal only, so every
# button, dropdown and text field comes out exactly CONTROL_H tall.
_INNER = CONTROL_H - 2
_SMALL_INNER = SMALL_H - 2
_SEG_INNER = CONTROL_H - 2 - 2 * SEG_INSET  # segmented control: 1px border + inset


def load_fonts() -> str:
    """Register the bundled fonts (the UI's Inter and every invoice font). Returns the UI family."""
    from ..doc.fonts import load_bundled

    return FONT_FAMILY if FONT_FAMILY in load_bundled() else ""


STYLESHEET = f"""
* {{ outline: none; }}
QWidget {{ color: {TEXT}; font-size: {TEXT_MD}px; }}
QMainWindow, #Root {{ background: {BG}; }}
QDialog {{ background: {PANEL}; }}
QToolTip {{ background: {RAISED}; color: {TEXT}; border: 1px solid {BORDER_STRONG};
    padding: {SPACE_1}px {SPACE_2}px; border-radius: {RADIUS_SM}px; font-size: {TEXT_SM}px; }}

/* ---------- text styles */
#Wordmark {{ font-size: {TEXT_BRAND}px; font-weight: {WEIGHT_BOLD}; letter-spacing: -0.5px; }}
#TitleBar {{ background: {BG}; border-bottom: 1px solid {BORDER}; }}
#TitleWordmark {{ font-size: {TEXT_TITLEBAR}px; font-weight: {WEIGHT_BOLD}; letter-spacing: -0.3px; }}
#DialogTitle {{ font-size: {TEXT_XL}px; font-weight: {WEIGHT_BOLD}; }}
#SectionLabel {{ color: {MUTED}; font-size: {TEXT_SM}px; font-weight: {WEIGHT_SEMIBOLD}; }}
#Hint {{ color: {FAINT}; font-size: {TEXT_SM}px; }}
#Muted {{ color: {MUTED}; }}
#Meta {{ color: {MUTED}; font-size: {TEXT_SM}px; }}

/* ---------- areas */
#StepHeader {{ border-bottom: 1px solid {BORDER}; }}
#StepBadge {{ background: {ACCENT}; color: {ON_ACCENT}; border-radius: {STEP_BADGE // 2}px;
    font-size: {TEXT_SM}px; font-weight: {WEIGHT_BOLD}; }}
#StepTitle {{ font-size: {TEXT_LG}px; font-weight: {WEIGHT_SEMIBOLD}; }}

/* ---------- buttons: all CONTROL_H tall */
QPushButton {{
    background: {RAISED}; border: 1px solid {BORDER_STRONG}; border-radius: {RADIUS}px;
    padding: 0 {SPACE_3}px; min-height: {_INNER}px; max-height: {_INNER}px; font-weight: {WEIGHT_MEDIUM};
}}
QPushButton:hover {{ background: {RAISED_HOVER}; }}
QPushButton:pressed {{ background: {RAISED_PRESS}; }}
QPushButton:disabled {{ color: {FAINT}; background: {CARD}; border-color: {BORDER}; }}
QPushButton#Primary {{ background: {ACCENT}; color: {ON_ACCENT}; border-color: {ACCENT};
    font-weight: {WEIGHT_SEMIBOLD}; padding: 0 {SPACE_4}px; }}
QPushButton#Primary:hover {{ background: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
QPushButton#Primary:pressed {{ background: {ACCENT_PRESS}; border-color: {ACCENT_PRESS}; }}
QPushButton#Primary:disabled {{ background: {ACCENT_OFF}; border-color: {ACCENT_OFF}; color: {ACCENT_OFF_TEXT}; }}
QPushButton#Ghost {{ background: transparent; border-color: transparent; color: {MUTED}; }}
QPushButton#Ghost:hover {{ background: {CARD_HOVER}; color: {TEXT}; }}
QPushButton#Disclosure {{ background: transparent; border: none; border-top: 1px solid {BORDER}; border-radius: 0;
    padding: {SPACE_2}px 0 0 0; color: {MUTED}; font-weight: {WEIGHT_SEMIBOLD}; text-align: left; }}
QPushButton#Disclosure:hover {{ color: {TEXT}; background: transparent; }}
QPushButton#Disclosure[first="true"] {{ border-top: none; padding-top: 0; }}
QPushButton#Secondary {{ background: transparent; color: {MUTED}; }}
QPushButton#Secondary:hover {{ background: {CARD_HOVER}; color: {TEXT}; }}
QPushButton#Danger {{ background: transparent; color: {BAD}; }}
QPushButton#Danger:hover {{ background: {BAD_TINT}; }}
QPushButton::menu-indicator, QToolButton::menu-indicator {{ image: none; width: 0; }}

/* ---------- small controls: all SMALL_H tall */
QToolButton#IconBtn {{ background: transparent; border: none; border-radius: {RADIUS_SM}px;
    min-width: {SMALL_H}px; max-width: {SMALL_H}px; min-height: {SMALL_H}px; max-height: {SMALL_H}px; }}
QToolButton#IconBtn:hover {{ background: {RAISED}; }}

/* ---------- fields + dropdowns: all CONTROL_H tall */
QComboBox, QLineEdit {{
    background: {CARD}; border: 1px solid {BORDER_STRONG}; border-radius: {RADIUS}px;
    padding: 0 {SPACE_3}px; min-height: {_INNER}px; max-height: {_INNER}px;
    selection-background-color: {ACCENT}; selection-color: {ON_ACCENT};
}}
QComboBox:hover, QLineEdit:hover {{ border-color: {BORDER_HOVER}; }}
QLineEdit:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: {SPACE_5}px; }}
QComboBox::down-arrow {{ image: url(__CHEVRON__); width: {SPACE_3}px; height: {SPACE_3}px; }}
QComboBox QAbstractItemView {{
    background: {RAISED}; border: 1px solid {BORDER_STRONG}; border-radius: {RADIUS_LG}px; padding: {SPACE_1}px;
    selection-background-color: {ACCENT}; selection-color: {ON_ACCENT}; outline: none;
}}
QComboBox QAbstractItemView::item {{ padding: 0 {SPACE_3}px; min-height: {CONTROL_H - SPACE_2}px; border-radius: {RADIUS_SM}px; }}
QComboBox QAbstractItemView::item:selected {{ background: {ACCENT}; color: {ON_ACCENT}; }}
QComboBox QAbstractItemView::separator {{ height: 1px; background: {BORDER_STRONG}; margin: {SPACE_1}px {SPACE_2}px; }}

/* ---------- segmented control: CONTROL_H tall overall */
#Seg {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS}px; }}
#SegBtn {{ background: transparent; border: none; border-radius: {RADIUS_SM}px; padding: 0 {SPACE_2}px;
    min-height: {_SEG_INNER}px; max-height: {_SEG_INNER}px; color: {MUTED}; font-weight: {WEIGHT_MEDIUM}; }}
#SegBtn:hover {{ color: {TEXT}; }}
#SegBtn:checked {{ background: {RAISED}; color: {TEXT}; font-weight: {WEIGHT_SEMIBOLD}; }}

/* ---------- checkboxes, sliders, progress */
QCheckBox {{ spacing: {SPACE_2}px; min-height: {SMALL_H}px; }}
QCheckBox::indicator {{ width: {INDICATOR}px; height: {INDICATOR}px; border-radius: {RADIUS_XS}px; border: 1px solid {BORDER_CHECK}; background: {CARD}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; image: url(__CHECK__); }}
QCheckBox:disabled {{ color: {FAINT}; }}
QSlider {{ min-height: {SMALL_H}px; }}
QSlider::groove:horizontal {{ height: {TRACK_H}px; background: {RAISED}; border-radius: {TRACK_H // 2}px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: {TRACK_H // 2}px; }}
QSlider::handle:horizontal {{ background: {TEXT}; width: {HANDLE}px; height: {HANDLE}px; margin: -{(HANDLE - TRACK_H) // 2}px 0; border-radius: {HANDLE // 2}px; }}
QProgressBar {{ background: {RAISED}; border: none; border-radius: {BAR_H // 2}px; max-height: {BAR_H}px; min-height: {BAR_H}px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: {BAR_H // 2}px; }}

/* ---------- scrolling */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: {SCROLL_W}px; margin: {SEG_INSET}px; }}
QScrollBar::handle:vertical {{ background: {BORDER_STRONG}; border-radius: {(SCROLL_W - 2 * SEG_INSET) // 2}px; min-height: {SCROLL_MIN}px; }}
QScrollBar::handle:vertical:hover {{ background: {BORDER_HOVER}; }}
QScrollBar:vertical:disabled, QScrollBar::handle:vertical:disabled {{ background: transparent; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ height: 0; background: none; }}

/* ---------- invoice cards */
#Card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS_LG}px; }}
#Card:hover {{ background: {CARD_HOVER}; }}
#Card[selected="true"], #Card[selected="true"]:hover {{ background: {CARD_SELECTED}; border-color: {ACCENT_EDGE}; }}
#CardClient {{ font-size: {TEXT_LG}px; font-weight: {WEIGHT_SEMIBOLD}; }}
#CardNumber {{ color: {MUTED}; font-size: {TEXT_SM}px; font-weight: {WEIGHT_MEDIUM}; }}
#CardAmount {{ font-size: {TEXT_LG}px; font-weight: {WEIGHT_SEMIBOLD}; }}
#Chip {{ border-radius: {RADIUS_SM}px; padding: 0 {SPACE_2}px; font-size: {TEXT_XS}px; font-weight: {WEIGHT_SEMIBOLD};
    min-height: {_SMALL_INNER - 4}px; max-height: {_SMALL_INNER - 4}px; border: 1px solid {BORDER_STRONG}; color: {MUTED}; }}
#Chip[tone="sent"] {{ color: {ACCENT}; border-color: {ACCENT_EDGE}; background: {ACCENT_TINT}; }}
#Chip[tone="overdue"] {{ color: {BAD}; border-color: {BAD_EDGE}; background: {BAD_TINT}; }}
#Chip[tone="paid"] {{ color: {GOOD}; border-color: {GOOD}; }}
#FooterStat {{ color: {MUTED}; font-size: {TEXT_SM}px; }}
#FooterValue {{ font-size: {TEXT_LG}px; font-weight: {WEIGHT_SEMIBOLD}; }}

/* ---------- empty states */
#EmptyTitle {{ font-size: {TEXT_XL}px; font-weight: {WEIGHT_SEMIBOLD}; }}
#EmptyText {{ color: {MUTED}; }}

/* ---------- details panel */
#Details {{ background: {PANEL}; border-left: 1px solid {BORDER}; border-right: 1px solid {BORDER}; }}
#ItemBox {{ background: {BG}; border: 1px solid {BORDER}; border-radius: {RADIUS_LG}px; }}
#ItemBox[open="false"]:hover {{ background: {CARD}; }}
#ItemTitle {{ font-weight: {WEIGHT_MEDIUM}; }}
#ItemTitle[blank="true"] {{ color: {FAINT}; }}
#ItemAmount {{ color: {MUTED}; font-size: {TEXT_SM}px; }}
QPlainTextEdit#Field {{ background: {CARD}; border: 1px solid {BORDER_STRONG}; border-radius: {RADIUS}px;
    font-family: inherit; font-size: {TEXT_MD}px; color: {TEXT}; padding: {SPACE_1}px {SPACE_2}px;
    selection-background-color: {ACCENT}; selection-color: {ON_ACCENT}; }}
QPlainTextEdit#Field:hover {{ border-color: {BORDER_HOVER}; }}
QPlainTextEdit#Field:focus {{ border-color: {ACCENT}; }}
QPlainTextEdit#Field:disabled, QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled {{ color: {FAINT}; border-color: {BORDER}; }}
QDateEdit {{ background: {CARD}; border: 1px solid {BORDER_STRONG}; border-radius: {RADIUS}px;
    padding: 0 {SPACE_3}px; min-height: {_INNER}px; max-height: {_INNER}px;
    selection-background-color: {ACCENT}; selection-color: {ON_ACCENT}; }}
QDateEdit:hover {{ border-color: {BORDER_HOVER}; }}
QDateEdit:focus {{ border-color: {ACCENT}; }}
QDateEdit::drop-down {{ border: none; width: {SPACE_5}px; }}
QDateEdit::down-arrow {{ image: url(__CHEVRON__); width: {SPACE_3}px; height: {SPACE_3}px; }}
QCalendarWidget QWidget {{ background: {RAISED}; color: {TEXT}; }}
QCalendarWidget QAbstractItemView {{ background: {CARD}; selection-background-color: {ACCENT}; selection-color: {ON_ACCENT}; }}
QCalendarWidget QToolButton {{ background: transparent; border: none; padding: {SPACE_1}px {SPACE_2}px; font-weight: {WEIGHT_SEMIBOLD}; }}
QCalendarWidget QToolButton:hover {{ background: {RAISED_HOVER}; border-radius: {RADIUS_SM}px; }}
#LogoThumb {{ background: {PAPER}; border: 1px solid {BORDER_STRONG}; border-radius: {RADIUS_SM}px; }}

/* ---------- preview panel */
#PreviewArea {{ background: {WELL}; }}
#PanelBottom {{ background: {PANEL}; border-top: 1px solid {BORDER}; }}

/* ---------- popups, toasts */
#Toast {{ background: {RAISED}; border: 1px solid {BORDER_STRONG}; border-radius: {RADIUS_LG}px; padding: {SPACE_2}px {SPACE_4}px; }}
QTextBrowser#Notes {{ background: {WELL}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: {RADIUS}px;
    padding: {SPACE_2}px; }}
QMenu {{ background: {RAISED}; border: 1px solid {BORDER_STRONG}; border-radius: {RADIUS_LG}px; padding: {SPACE_1}px; }}
QMenu::item {{ padding: 0 {SPACE_4}px 0 {SPACE_2}px; min-height: {CONTROL_H - SPACE_2}px; border-radius: {RADIUS_SM}px; }}
QMenu::item:selected {{ background: {ACCENT}; color: {ON_ACCENT}; }}
QMenu::item:disabled {{ color: {FAINT}; }}
QMenu::icon {{ padding-left: {SPACE_2}px; }}
QMenu::separator {{ height: 1px; background: {BORDER_STRONG}; margin: {SPACE_1}px {SPACE_2}px; }}
QMenu::section {{ color: {FAINT}; padding: {SPACE_2}px {SPACE_2}px 0 {SPACE_2}px; font-size: {TEXT_XS}px; font-weight: {WEIGHT_SEMIBOLD}; }}
"""

# Minimal line icons (Lucide-style, ISC licensed shapes redrawn).
_SVG = {
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "x": '<path d="M18 6 6 18M6 6l12 12"/>',
    "retry": '<path d="M3 12a9 9 0 0 1 15.5-6.2L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15.5 6.2L3 16"/><path d="M3 21v-5h5"/>',
    "reveal": '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 16v-4M12 8h.01"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "film": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 3v18M17 3v18M3 7.5h4M3 12h18M3 16.5h4M17 7.5h4M17 16.5h4"/>',
    "image": '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21"/>',
    "audio": '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
    "drop": '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/>',
    "pause": '<rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/>',
    "play": '<path d="M6 4l14 8-14 8z"/>',
    "chevron": '<path d="m6 9 6 6 6-6"/>',
    "captions": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M10 10.5a2 2 0 1 0 0 3M16 10.5a2 2 0 1 0 0 3"/>',
    "eye": '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    "terminal": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="m7 9 3 3-3 3M13 15h4"/>',
    "more": '<circle cx="5" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="19" cy="12" r="1.2"/>',
    "chevron-left": '<path d="m15 6-6 6 6 6"/>',
    "chevron-right": '<path d="m9 6 6 6-6 6"/>',
    "scissors": '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.12 15.88M14.47 14.48 20 20M8.12 8.12 12 12"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    "trash": '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/>',
    "list-x": '<path d="M11 12H3M16 6H3M16 18H3"/><path d="m15 10 4 4M19 10l-4 4"/>',
    "export": '<path d="M12 15V3"/><path d="m7 8 5-5 5 5"/><path d="M20 14v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-5"/>',
    "printer": '<path d="M6 9V3h12v6"/><rect x="3" y="9" width="18" height="8" rx="2"/><path d="M6 14h12v7H6z"/>',
    "copy": '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1"/>',
    "receipt": '<path d="M5 3h14v18l-3-2-2 2-2-2-2 2-2-2-3 2z"/><path d="M9 8h6M9 12h6M9 16h3"/>',
    "edit": '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
    "alert": '<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
    "arrow-up": '<path d="M12 19V5"/><path d="m5 12 7-7 7 7"/>',
    "arrow-down": '<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/>',
    "moon": '<path d="M20.5 14.1A8.5 8.5 0 1 1 9.9 3.5a6.6 6.6 0 0 0 10.6 10.6z"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
}


def svg_markup(name: str, color: str = TEXT, stroke: float = 2.0) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{_SVG[name]}</svg>'
    )


@lru_cache(maxsize=512)
def pixmap(
    name: str,
    size: int = ICON,
    color: str = TEXT,
    stroke: float = 2.0,
    dpr: float = 2.0,
) -> QPixmap:
    """Drawn once per look and reused (a long list redraws the same few icons thousands of times)."""
    r = QSvgRenderer(QByteArray(svg_markup(name, color, stroke).encode()))
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r.render(p, QRectF(0, 0, size * dpr, size * dpr))
    p.end()
    pm.setDevicePixelRatio(dpr)
    return pm


@lru_cache(maxsize=256)
def icon(name: str, color: str = TEXT, size: int = ICON) -> QIcon:
    """An icon that looks the same however the button is hovered, focused or pressed."""
    ic = QIcon()
    for mode in (QIcon.Mode.Normal, QIcon.Mode.Active, QIcon.Mode.Selected):
        ic.addPixmap(pixmap(name, size, color), mode)
    return ic


@lru_cache(maxsize=128)
def menu_icon(name: str, color: str = MUTED, size: int = ICON) -> QIcon:
    """For menu rows: the highlighted row is turquoise, so its icon switches to dark there."""
    ic = QIcon(pixmap(name, size, color))
    ic.addPixmap(pixmap(name, size, ON_ACCENT), QIcon.Mode.Active)
    ic.addPixmap(pixmap(name, size, ON_ACCENT), QIcon.Mode.Selected)
    return ic


def stylesheet(folder: Path) -> str:
    """QSS can only reference image files, so write the couple it needs into `folder`
    (Cobro's per-user data folder, overwritten each launch)."""
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:  # data folder not writable: fall back to a private temp folder
        import tempfile

        folder = Path(tempfile.mkdtemp(prefix="cobro-ui-"))
    chevron = folder / "chevron.svg"
    chevron.write_text(svg_markup("chevron", MUTED))
    check = folder / "check.svg"
    check.write_text(svg_markup("check", ON_ACCENT, 3))
    return STYLESHEET.replace("__CHEVRON__", chevron.as_posix()).replace("__CHECK__", check.as_posix())
