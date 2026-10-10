"""Your Business: the name, addresses and defaults that go on every invoice. Entered once, then reused.

How it looks (fonts, colors, logo) lives in the Details panel's Look group, where the preview
updates as you change it.
"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QWidget

from ..core import numbering
from ..core.dates import terms_label
from ..core.model import TERMS_DAYS, Business
from ..core.store import DEFAULT_NOTE, DEFAULT_TERMS, suggested_payment
from .tokens import (
    BUSINESS_DIALOG_H,
    DIALOG_W,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    SPACE_5,
    TEXT_BOX_TALL,
)
from .widgets import FitScroll, Section, TextBox, combo, hbox, hint, vbox


class BusinessDialog(QDialog):
    """Add or edit a business. After Save, `.business` holds the result."""

    def __init__(self, business: Business | None, can_delete: bool, parent: QWidget | None = None):
        super().__init__(parent)
        self.editing = business is not None
        self.business = replace(business) if business else Business()
        self.deleted = False
        self.setWindowTitle("Edit Business" if self.editing else "Add Your Business")
        self.setMinimumWidth(DIALOG_W + 2 * SPACE_5)
        self.resize(DIALOG_W + 2 * SPACE_5, BUSINESS_DIALOG_H)
        outer = vbox(self, (0, SPACE_5, 0, SPACE_5), SPACE_3)

        head = vbox(spacing=SPACE_2)
        head.setContentsMargins(SPACE_5, 0, SPACE_5, 0)
        title = QLabel("Edit Business" if self.editing else "Add Your Business")
        title.setObjectName("DialogTitle")
        head.addWidget(title)
        head.addWidget(
            hint("Fill this in once. Every new invoice starts with it, and you can change it any time.")
        )
        outer.addLayout(head)

        body = QWidget()
        lay = vbox(body, (SPACE_5, 0, SPACE_5 - SPACE_2, 0), SPACE_3)
        b = self.business

        self.name = self._line(lay, "Name", b.name, "Your name or your company's")
        self.tagline = self._line(lay, "Tagline", b.tagline, "Director · Cinematographer · Editor")
        self.address = self._box(lay, "Address", b.address, "Street\nCity, State ZIP")
        self.mail = self._box(lay, "Mail Payments To", b.mail_address, "Only if checks go somewhere else")
        self.email = self._line(lay, "Email", b.email, "you@example.com")
        self.phone = self._line(lay, "Phone", b.phone, "")
        self.website = self._line(lay, "Website", b.website, "")

        row = hbox(spacing=SPACE_2)
        sec = Section("Invoice Numbers Start With")
        self.prefix = QLineEdit(b.prefix)
        self.prefix.setPlaceholderText(numbering.initials(b.name))
        self.prefix.setToolTip("Numbers look like NV-2026-001, counting up each year.")
        sec.add(self.prefix)
        row.addWidget(sec, 1)
        sec = Section("Currency")
        self.currency = QLineEdit(b.currency or "$")
        self.currency.setMaxLength(4)
        self.currency.setToolTip("The symbol in front of every amount, like $ or €.")
        sec.add(self.currency)
        row.addWidget(sec, 1)
        lay.addLayout(row)

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
        lay.addLayout(row)

        self.payment = self._box(lay, "How to Pay", b.payment, "", TEXT_BOX_TALL)
        self.terms = self._box(lay, "Terms", b.terms or DEFAULT_TERMS, "", TEXT_BOX_TALL)
        self.note = self._line(lay, "Closing Note", b.note or DEFAULT_NOTE, "")
        lay.addWidget(hint("These start every new invoice. Each invoice can still say something different."))
        lay.addStretch(1)

        self.name.textChanged.connect(self._name_changed)
        self.mail.edited.connect(self._suggest_payment)
        self.address.edited.connect(self._suggest_payment)
        self.payment.edited.connect(self._payment_typed)
        self._payment_was_suggested = not b.payment.strip()
        self._suggest_payment()

        scroll = FitScroll()
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        buttons = hbox(spacing=SPACE_2)
        buttons.setContentsMargins(SPACE_5, SPACE_4, SPACE_5, 0)
        if self.editing and can_delete:
            delete = QPushButton("Delete Business…")
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
        b.currency = self.currency.text().strip() or "$"
        b.terms_days = int(self.terms_days.currentData())
        b.tax_rate = self.tax.text().strip()
        b.payment = self.payment.text().strip()
        b.terms = self.terms.text().strip()
        b.note = self.note.text().strip()
        return b

    def _name_changed(self, text: str) -> None:
        self.prefix.setPlaceholderText(numbering.initials(text))
        self.save.setEnabled(bool(text.strip()))
        self._suggest_payment()

    def _suggest_payment(self) -> None:
        """Until you type your own, "How to Pay" follows the name and address."""
        if self._payment_was_suggested or not self.payment.text().strip():
            self.payment.set_text(suggested_payment(self._draft()))
            self._payment_was_suggested = True

    def _payment_typed(self) -> None:
        self._payment_was_suggested = False

    def _save(self) -> None:
        self.business = self._draft()
        self.accept()

    def _delete(self) -> None:
        from .dialogs import confirm

        if confirm(
            self,
            "Delete This Business?",
            f"{self.business.name} will be removed from Cobro. This can't be undone.",
            "Delete Business",
        ):
            self.deleted = True
            self.accept()
