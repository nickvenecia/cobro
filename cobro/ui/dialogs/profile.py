"""Your profile: who the invoice is from. Name, logo, contact details, the defaults every invoice starts
with, and how the paper looks (its color, header, logo size and paper size). Entered once, in Settings ›
Profiles, then picked under From; keep as many as you invoice from. (In the code a profile is a `Business`.)
"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QDialog, QFileDialog, QLabel, QLineEdit, QPushButton, QWidget

from cobro.core import numbering
from cobro.core.dates import terms_label, today
from cobro.core.log import get_logger
from cobro.core.looks import COLORS, CUSTOM, HEADERS, LOGO_SIZES, PAPERS, accent_of
from cobro.core.model import TERMS_DAYS, Business
from cobro.core.paths import logo_path, logos_dir
from cobro.core.store import DEFAULT_NOTE, DEFAULT_TERMS, suggested_payment
from cobro.ui.components.widgets import (
    Disclosure,
    Embeddable,
    FitScroll,
    Section,
    TextBox,
    ToggleRow,
    combo,
    hbox,
    hint,
    vbox,
)
from cobro.ui.style.tokens import (
    COLOR_DOT,
    DIALOG_W_WIDE,
    LOGO_THUMB,
    LOGO_THUMB_MAX_W,
    PROFILE_DIALOG_H,
    SCROLL_GUTTER,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    SPACE_5,
    TEXT_BOX_TALL,
)

log = get_logger(__name__)

LOGO_MAX_PX = 1600  # a logo's long side once it's kept (sharp on paper, small in a PDF)
LOGO_MAX_BYTES = 40_000_000  # a logo file you pick, before it's redrawn


def import_logo(src: Path) -> str:
    """Keep a copy of a logo in Cobro's own folder (so moving or deleting the original never breaks an invoice).

    Every logo is read and drawn again by Cobro before it's kept, as a PNG no bigger than LOGO_MAX_PX: whatever
    else the file carried (camera details, scripts or links inside an SVG, anything odd) is left behind, and a
    file that isn't really a picture is refused. Named by what's in it; written whole or not at all.
    Returns the stored file name. Raises ValueError with a plain message if it can't be used."""
    bad = f"Cobro can't read {src.name}. Use a PNG, JPG or SVG file."
    try:
        if src.stat().st_size > LOGO_MAX_BYTES:
            raise ValueError(f"{src.name} is too big for a logo. Use a smaller PNG, JPG or SVG file.")
        data = src.read_bytes()
    except OSError as e:
        raise ValueError(f"Couldn't open {src.name}.") from e
    img = _svg_picture(data) if src.suffix.lower() == ".svg" else QImage.fromData(QByteArray(data))
    if img is None or img.isNull() or img.width() < 2 or img.height() < 2:
        raise ValueError(bad)
    if max(img.width(), img.height()) > LOGO_MAX_PX:
        img = img.scaled(
            LOGO_MAX_PX,
            LOGO_MAX_PX,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    name = f"{hashlib.sha256(data).hexdigest()[:16]}.png"
    folder = logos_dir()
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / name
    if not dest.exists():
        tmp = folder / f".{name}.part"
        if not img.save(str(tmp), "PNG"):
            tmp.unlink(missing_ok=True)
            raise ValueError("Couldn't save the logo. Check that there's free space on this computer.")
        tmp.replace(dest)
    return name


def _svg_picture(data: bytes) -> QImage | None:
    """An SVG logo drawn as a picture LOGO_MAX_PX on its long side (on a see-through background)."""
    from PySide6.QtSvg import QSvgRenderer

    r = QSvgRenderer(QByteArray(data))
    if not r.isValid():
        return None
    size = r.defaultSize()
    w, h = max(1, size.width()), max(1, size.height())
    scale = LOGO_MAX_PX / max(w, h)
    img = QImage(
        max(2, round(w * scale)), max(2, round(h * scale)), QImage.Format.Format_ARGB32_Premultiplied
    )
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r.render(p)
    p.end()
    return img


def logo_thumbnail(path: Path, height: int) -> QPixmap:
    """A sharp little picture of a logo file, `height` px tall (empty if it can't be read)."""
    dpr = 2
    if path.suffix.lower() == ".svg":
        from PySide6.QtSvg import QSvgRenderer

        r = QSvgRenderer(str(path))
        size = r.defaultSize()
        h = height * dpr
        w = max(1, round(h * size.width() / max(1, size.height())))
        pm = QPixmap(w, h)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        r.render(p)
        p.end()
    else:
        pm = QPixmap(str(path))
        if pm.isNull():
            return pm
        pm = pm.scaledToHeight(height * dpr, Qt.TransformationMode.SmoothTransformation)
    pm.setDevicePixelRatio(dpr)
    return pm


def color_dot(color: str) -> QIcon:
    """The little circle of a paper color, beside its name in the Paper Color dropdown."""
    size = COLOR_DOT * 2
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    p.drawEllipse(1, 1, size - 2, size - 2)
    p.end()
    pm.setDevicePixelRatio(2)
    return QIcon(pm)


class ProfileDialog(Embeddable, QDialog):
    """Add or edit a profile. After Save, `.business` holds the result; `.deleted` if Delete was chosen."""

    def __init__(
        self, business: Business | None, can_delete: bool, parent: QWidget | None = None, new: bool = False
    ):
        """`new` with a business: a new profile that starts from those values."""
        super().__init__(parent)
        self.editing = business is not None and not new
        # a real copy (the look too), so Cancel leaves the profile exactly as it was
        self.business = replace(business, look=replace(business.look)) if business else Business()
        self.deleted = False
        title_text = "Edit Profile" if self.editing else "Add Your Profile"
        self.setWindowTitle(title_text)
        self.setMinimumWidth(DIALOG_W_WIDE)
        self.resize(DIALOG_W_WIDE, PROFILE_DIALOG_H)
        outer = vbox(self, (0, SPACE_5, 0, SPACE_5), SPACE_3)

        head = self._head = vbox(spacing=SPACE_2)
        head.setContentsMargins(SPACE_5, 0, SPACE_5, 0)
        self.title_label = QLabel(title_text)
        self.title_label.setObjectName("DialogTitle")
        head.addWidget(self.title_label)
        outer.addLayout(head)

        body = QWidget()
        lay = self._body_lay = vbox(body, (SPACE_5, 0, SPACE_5 - SCROLL_GUTTER, 0), SPACE_3)
        b = self.business

        self.name = self._line(lay, "Name", b.name, "Your name or your company's")
        self.name.setToolTip("Who your invoices are from")
        self.tagline = self._line(lay, "Tagline", b.tagline, "Director · Cinematographer · Editor")
        lay.addWidget(self._build_logo())

        self.contact = Disclosure("Contact", is_open=not self.editing)
        c = self.contact.lay
        self.address = self._box(c, "Address", b.address, "Street\nCity, State ZIP")
        self.mail = self._box(c, "Mail Payments To", b.mail_address, "Only if checks go somewhere else")
        self.email = self._line(c, "Email", b.email, "you@example.com")
        self.phone = self._line(c, "Phone", b.phone, "")
        self.website = self._line(c, "Website", b.website, "")
        lay.addWidget(self.contact)

        self.numbers = Disclosure("Numbers && Tax")
        row = hbox(spacing=SPACE_2)
        sec = Section("Invoice Numbers Start With")
        self.prefix = QLineEdit(b.prefix)
        self.prefix.setPlaceholderText(numbering.initials(b.name))
        self.prefix.setToolTip("Numbers look like JLF-2026-001, counting up each year.")
        sec.add(self.prefix)
        row.addWidget(sec, 1)
        sec = Section("Currency")
        self.currency = QLineEdit(b.currency or "$")
        self.currency.setMaxLength(4)
        self.currency.setToolTip("The symbol in front of every amount, like $ or €.")
        sec.add(self.currency)
        row.addWidget(sec, 1)
        self.numbers.add(row)
        sec = Section("Number Style")
        self.number_style = combo(self._style_items(b.prefix or numbering.initials(b.name)), b.number_style)
        sec.add(self.number_style)
        self.numbers.add(sec)
        row = hbox(spacing=SPACE_2)
        sec = Section("Payment Terms")
        self.terms_days = combo([(str(d), terms_label(d), "") for d in TERMS_DAYS], str(b.terms_days))
        sec.add(self.terms_days)
        row.addWidget(sec, 1)
        sec = Section("Sales Tax %")
        self.tax = QLineEdit(b.tax_rate)
        self.tax.setPlaceholderText("None")
        sec.add(self.tax)
        row.addWidget(sec, 1)
        self.numbers.add(row)
        lay.addWidget(self.numbers)

        self.pay = Disclosure("Payment && Terms")
        self.pay.setToolTip("These start every new invoice. Each invoice can still say something different.")
        self.payment = self._box(self.pay.lay, "How to Pay", b.payment, "", TEXT_BOX_TALL)
        self.terms = self._box(self.pay.lay, "Terms", b.terms or DEFAULT_TERMS, "", TEXT_BOX_TALL)
        self.note = self._line(self.pay.lay, "Closing Note", b.note or DEFAULT_NOTE, "")
        lay.addWidget(self.pay)

        self.paper = Disclosure("Paper")
        self.paper.setToolTip(f"How every invoice from {b.name or 'this profile'} looks")
        sec = Section("Paper Color")
        self.color = combo([], "")
        for k, sw in COLORS.items():
            self.color.addItem(color_dot(sw.accent), sw.label, k)
        if b.look.color == CUSTOM:  # picked in an older Cobro: kept as it was
            self.color.addItem(color_dot(accent_of(b.look)), f"Custom {accent_of(b.look)}", CUSTOM)
        self.color.setCurrentIndex(max(0, self.color.findData(b.look.color)))
        self.color.setToolTip("The accent on the amount due, the balance and the color band")
        sec.add(self.color)
        self.paper.add(sec)
        row = hbox(spacing=SPACE_2)
        sec = Section("Header")
        self.header = combo([(k, v, "") for k, v in HEADERS.items()], b.look.header)
        sec.add(self.header)
        row.addWidget(sec, 1)
        sec = Section("Paper Size")
        self.paper_size = combo([(k, v[0], "") for k, v in PAPERS.items()], b.look.paper)
        sec.add(self.paper_size)
        row.addWidget(sec, 1)
        self.paper.add(row)
        self.logo_size_sec = Section("Logo Size")
        self.logo_size = combo([(k, v[0], "") for k, v in LOGO_SIZES.items()], b.look.logo_size)
        self.logo_size_sec.add(self.logo_size)
        self.name_with_logo = ToggleRow("Show Name Next to Logo", b.look.name_with_logo)
        self.name_with_logo.setToolTip("Turn off if your logo already spells out the name")
        self.logo_size_sec.add(self.name_with_logo)
        self.paper.add(self.logo_size_sec)
        lay.addWidget(self.paper)
        lay.addStretch(1)

        self.name.textChanged.connect(self._name_changed)
        self.prefix.textChanged.connect(
            lambda t: self._show_styles(t or numbering.initials(self.name.text()))
        )
        self.mail.edited.connect(self._suggest_payment)
        self.address.edited.connect(self._suggest_payment)
        self.payment.edited.connect(self._payment_typed)
        for f in (self.color, self.header, self.paper_size, self.logo_size):
            f.currentIndexChanged.connect(lambda _i: self._summaries())
        for group in (self.contact, self.numbers, self.pay, self.paper):
            group.toggled.connect(lambda _on: self._summaries())
        self._payment_was_suggested = not b.payment.strip()
        self._suggest_payment()

        scroll = FitScroll()
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        buttons = self._buttons = hbox(spacing=SPACE_2)
        buttons.setContentsMargins(SPACE_5, SPACE_4, SPACE_5, 0)
        if self.editing and can_delete:
            delete = QPushButton("Delete Profile…")
            delete.setObjectName("Danger")
            delete.clicked.connect(self._delete)
            buttons.addWidget(delete)
        buttons.addStretch(1)
        self.cancel_btn = cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.save = QPushButton("Save")
        self.save.setObjectName("Primary")
        self.save.setDefault(True)
        self.save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(self.save)
        outer.addLayout(buttons)
        self._name_changed(self.name.text())
        self._show_logo()

    def side_margin(self, px: int) -> None:
        """The room on the left and right (none inside Settings, which has its own)."""
        self._head.setContentsMargins(px, 0, px, 0)
        self._body_lay.setContentsMargins(px, 0, SPACE_3, 0)
        self._buttons.setContentsMargins(px, SPACE_4, SPACE_3 + SCROLL_GUTTER, 0)  # lines up with the fields

    # ------------------------------------------------------------------ helpers
    def _line(self, lay, label: str, value: str, placeholder: str) -> QLineEdit:
        sec = Section(label)
        f = QLineEdit(value)
        f.setPlaceholderText(placeholder)
        sec.add(f)
        lay.addWidget(sec)
        return f

    def _box(self, lay, label: str, value: str, placeholder: str, height: int | None = None) -> TextBox:
        sec = Section(label)
        f = TextBox(placeholder, height) if height else TextBox(placeholder)
        f.set_text(value)
        sec.add(f)
        lay.addWidget(sec)
        return f

    @staticmethod
    def _style_items(prefix: str) -> list[tuple[str, str, str]]:
        """The Number Style choices, each shown as an example number with these letters."""
        year, p = today().year, numbering.clean_prefix(prefix)
        return [
            ("year", f"{p}-{year}-001", "One count for all your invoices"),
            ("client", f"{p}-ACME-{year}-001", "A count for each client, with their code in the middle"),
            ("client_only", f"ACME-{year}-001", "A count for each client, named by their code alone"),
        ]

    def _show_styles(self, prefix: str) -> None:
        for i, (_key, label, _tip) in enumerate(self._style_items(prefix)):
            self.number_style.setItemText(i, label)

    def _draft(self) -> Business:
        b = replace(self.business, look=replace(self.business.look))
        b.name = self.name.text().strip()
        b.tagline = self.tagline.text().strip()
        b.address = self.address.text().strip()
        b.mail_address = self.mail.text().strip()
        b.email = self.email.text().strip()
        b.phone = self.phone.text().strip()
        b.website = self.website.text().strip()
        b.prefix = numbering.clean_prefix(self.prefix.text() or numbering.initials(b.name))
        b.number_style = self.number_style.currentData()
        b.currency = self.currency.text().strip() or "$"
        b.terms_days = int(self.terms_days.currentData())
        b.tax_rate = self.tax.text().strip()
        b.payment = self.payment.text().strip()
        b.terms = self.terms.text().strip()
        b.note = self.note.text().strip()
        b.look.color = self.color.currentData()
        b.look.header = self.header.currentData()
        b.look.paper = self.paper_size.currentData()
        b.look.logo_size = self.logo_size.currentData()
        b.look.name_with_logo = self.name_with_logo.isChecked()
        return b

    def _name_changed(self, text: str) -> None:
        self.prefix.setPlaceholderText(numbering.initials(text))
        self._show_styles(self.prefix.text() or numbering.initials(text))
        self.save.setEnabled(bool(text.strip()))
        self._suggest_payment()
        self._summaries()

    def _summaries(self) -> None:
        """What each folded group holds, so nothing is hidden silently."""
        b = self._draft()
        self.contact.set_summary(b.email or b.address.split("\n")[0])
        self.numbers.set_summary(
            f"{b.prefix}-{today().year}-001 · {b.currency} · {terms_label(b.terms_days)}"
        )
        color = COLORS.get(b.look.color)
        parts = [color.label if color else accent_of(b.look), HEADERS.get(b.look.header, "")]
        parts.append(PAPERS.get(b.look.paper, PAPERS["letter"])[0])
        self.paper.set_summary(" · ".join(p for p in parts if p))

    def _suggest_payment(self) -> None:
        """Until you type your own, "How to Pay" follows the name and address."""
        if self._payment_was_suggested or not self.payment.text().strip():
            self.payment.set_text(suggested_payment(self._draft()))
            self._payment_was_suggested = True

    def _payment_typed(self) -> None:
        self._payment_was_suggested = False

    # ------------------------------------------------------------------ logo
    def _build_logo(self) -> Section:
        sec = Section("Logo")
        row = hbox(spacing=SPACE_2)
        self.logo_thumb = QLabel()
        self.logo_thumb.setObjectName("LogoThumb")
        self.logo_thumb.setFixedHeight(LOGO_THUMB)
        self.logo_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_btn = QPushButton("Choose Logo…")
        self.logo_btn.setToolTip("A logo or a photo: PNG, JPG or SVG.")
        self.logo_btn.clicked.connect(self._choose_logo)
        self.logo_remove = QPushButton("Remove")
        self.logo_remove.setObjectName("Ghost")
        self.logo_remove.setToolTip("Leave the logo off. Cancel puts it back.")
        self.logo_remove.clicked.connect(lambda: self._set_logo(""))
        row.addWidget(self.logo_thumb)
        row.addWidget(self.logo_btn)
        row.addWidget(self.logo_remove)
        row.addStretch(1)
        sec.add(row)
        self.logo_error = hint("")
        self.logo_error.hide()
        sec.add(self.logo_error)
        return sec

    def _show_logo(self) -> None:
        name = self.business.look.logo
        path = logo_path(name)
        pm = logo_thumbnail(path, LOGO_THUMB - SPACE_2) if path and path.is_file() else QPixmap()
        has_logo = not pm.isNull()
        if has_logo:
            self.logo_thumb.setPixmap(pm)
            width = round(pm.width() / pm.devicePixelRatio()) + SPACE_2
            self.logo_thumb.setFixedWidth(min(width, LOGO_THUMB_MAX_W))
        self.logo_thumb.setVisible(has_logo)
        self.logo_remove.setVisible(has_logo)
        self.logo_btn.setText("Change…" if has_logo else "Choose Logo…")
        if hasattr(self, "logo_size_sec"):
            self.logo_size_sec.setVisible(has_logo)  # only what applies: sizes need a logo

    def _set_logo(self, name: str) -> None:
        self.business.look.logo = name
        self._show_logo()

    def _choose_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose a Logo", str(Path.home()), "Logos (*.png *.jpg *.jpeg *.svg)"
        )
        if not path:
            return
        try:
            name = import_logo(Path(path))
        except (OSError, ValueError) as e:
            log.warning("logo not added: %s", e)
            self.logo_error.setText(str(e) if isinstance(e, ValueError) else "Couldn't read that file.")
            self.logo_error.show()
            return
        log.info("logo added")
        self.logo_error.hide()
        self._set_logo(name)

    # ------------------------------------------------------------------ buttons
    def _save(self) -> None:
        self.business = self._draft()
        self.accept()

    def _delete(self) -> None:
        from cobro.ui.dialogs.common import confirm

        if confirm(
            self,
            f"Delete {self.business.name or 'This Profile'}?",
            "No invoice uses it.",
            "Delete Profile",
        ):
            self.deleted = True
            self.accept()
