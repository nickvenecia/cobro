"""Your Profile: who the invoice is from. Name, logo, contact details and the defaults every invoice
starts with. Entered once, then picked under From; keep as many as you invoice from.

How it looks (fonts, colors, header, paper) lives in the Details panel's Look group, where the preview
updates as you change it. (In the code a profile is a `Business`.)
"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import QDialog, QFileDialog, QLabel, QLineEdit, QPushButton, QWidget

from ..core import numbering
from ..core.dates import terms_label, today
from ..core.log import get_logger
from ..core.model import TERMS_DAYS, Business
from ..core.paths import logos_dir
from ..core.store import DEFAULT_NOTE, DEFAULT_TERMS, suggested_payment
from .tokens import (
    DIALOG_W,
    LOGO_THUMB,
    PROFILE_DIALOG_H,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    SPACE_5,
    TEXT_BOX_TALL,
)
from .widgets import Disclosure, FitScroll, Section, TextBox, combo, hbox, hint, vbox

log = get_logger(__name__)

LOGO_MAX_PX = 1600  # bigger pictures are scaled down when added (keeps PDFs small)


def import_logo(src: Path) -> str:
    """Copy a logo into Cobro's own folder (so moving or deleting the original never breaks an invoice).
    Returns the stored file name. Raises ValueError if it isn't a picture Cobro can read."""
    from ..doc.render import logo_size

    if logo_size(src) is None:
        raise ValueError(f"Cobro can't read {src.name}. Use a PNG, JPG or SVG file.")
    data = src.read_bytes()
    digest = hashlib.sha256(data).hexdigest()[:16]
    folder = logos_dir()
    folder.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".svg":
        name = f"{digest}.svg"
        (folder / name).write_bytes(data)
        return name
    img = QImage(str(src))
    if img.isNull():
        raise ValueError(f"Cobro can't read {src.name}. Use a PNG, JPG or SVG file.")
    if max(img.width(), img.height()) > LOGO_MAX_PX:
        img = img.scaled(
            LOGO_MAX_PX,
            LOGO_MAX_PX,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    name = f"{digest}.png"
    if not img.save(str(folder / name), "PNG"):
        raise ValueError("Couldn't save the logo. Check that there's free space on this computer.")
    return name


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


class ProfileDialog(QDialog):
    """Add or edit a profile. After Save, `.business` holds the result; `.deleted` if Delete was chosen."""

    def __init__(self, business: Business | None, can_delete: bool, parent: QWidget | None = None):
        super().__init__(parent)
        self.editing = business is not None
        # a real copy (the look too), so Cancel leaves the profile exactly as it was
        self.business = replace(business, look=replace(business.look)) if business else Business()
        self.deleted = False
        title_text = "Edit Profile" if self.editing else "Add Your Profile"
        self.setWindowTitle(title_text)
        self.setMinimumWidth(DIALOG_W + 2 * SPACE_5)
        self.resize(DIALOG_W + 2 * SPACE_5, PROFILE_DIALOG_H)
        outer = vbox(self, (0, SPACE_5, 0, SPACE_5), SPACE_3)

        head = vbox(spacing=SPACE_2)
        head.setContentsMargins(SPACE_5, 0, SPACE_5, 0)
        title = QLabel(title_text)
        title.setObjectName("DialogTitle")
        head.addWidget(title)
        head.addWidget(hint("Who your invoices are from. Fill it in once; every new invoice starts with it."))
        outer.addLayout(head)

        body = QWidget()
        lay = vbox(body, (SPACE_5, 0, SPACE_5 - SPACE_2, 0), SPACE_3)
        b = self.business

        self.name = self._line(lay, "Name", b.name, "Your name or your company's")
        self.tagline = self._line(lay, "Tagline", b.tagline, "Director · Cinematographer · Editor")
        lay.addWidget(self._build_logo())

        self.contact = Disclosure("Contact", is_open=True)
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
        self.prefix.setToolTip("Numbers look like RM-2026-001, counting up each year.")
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
        self.payment = self._box(self.pay.lay, "How to Pay", b.payment, "", TEXT_BOX_TALL)
        self.terms = self._box(self.pay.lay, "Terms", b.terms or DEFAULT_TERMS, "", TEXT_BOX_TALL)
        self.note = self._line(self.pay.lay, "Closing Note", b.note or DEFAULT_NOTE, "")
        self.pay.add(hint("These start every new invoice. Each invoice can still say something different."))
        lay.addWidget(self.pay)
        lay.addStretch(1)

        self.name.textChanged.connect(self._name_changed)
        self.prefix.textChanged.connect(
            lambda t: self._show_styles(t or numbering.initials(self.name.text()))
        )
        self.mail.edited.connect(self._suggest_payment)
        self.address.edited.connect(self._suggest_payment)
        self.payment.edited.connect(self._payment_typed)
        for group in (self.contact, self.numbers, self.pay):
            group.toggled.connect(lambda _on: self._summaries())
        self._payment_was_suggested = not b.payment.strip()
        self._suggest_payment()

        scroll = FitScroll()
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        buttons = hbox(spacing=SPACE_2)
        buttons.setContentsMargins(SPACE_5, SPACE_4, SPACE_5, 0)
        if self.editing and can_delete:
            delete = QPushButton("Delete Profile…")
            delete.setObjectName("Danger")
            delete.clicked.connect(self._delete)
            buttons.addWidget(delete)
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
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
        b = replace(self.business)
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
        path = logos_dir() / name if name else None
        pm = logo_thumbnail(path, LOGO_THUMB - SPACE_2) if path and path.is_file() else QPixmap()
        has_logo = not pm.isNull()
        if has_logo:
            self.logo_thumb.setPixmap(pm)
            width = round(pm.width() / pm.devicePixelRatio()) + SPACE_2
            self.logo_thumb.setFixedWidth(min(width, LOGO_THUMB * 4))
        self.logo_thumb.setVisible(has_logo)
        self.logo_remove.setVisible(has_logo)
        self.logo_btn.setText("Change…" if has_logo else "Choose Logo…")

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
        from .dialogs import confirm

        if confirm(
            self,
            "Delete This Profile?",
            f"{self.business.name} will be removed from Cobro. This can't be undone.",
            "Delete Profile",
        ):
            self.deleted = True
            self.accept()
