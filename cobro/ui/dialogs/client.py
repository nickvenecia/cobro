"""A saved client: who you bill. Filled in once, then picked under Bill To on every invoice after that."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QWidget

from cobro.core import numbering
from cobro.core.model import Client
from cobro.core.store import Library
from cobro.ui.components.widgets import Section, TextBox, button_row, hbox, hint, vbox
from cobro.ui.style.tokens import DIALOG_W_WIDE, NUM_FIELD_W, SPACE_2, SPACE_3, SPACE_5


class ClientDialog(QDialog):
    """Add or edit a saved client. After Save, `.client` holds the result; `.deleted` if Delete was chosen."""

    def __init__(
        self,
        client: Client | None,
        lib: Library,
        can_delete: bool,
        show_code: bool = False,
        parent: QWidget | None = None,
    ):
        """`show_code`: a profile counts invoice numbers per client, so the client's code matters."""
        super().__init__(parent)
        self.lib = lib
        self.editing = client is not None
        self.client = replace(client) if client else Client()
        self.deleted = False
        title_text = "Edit Client" if self.editing else "New Client"
        self.setWindowTitle(title_text)
        self.setMinimumWidth(DIALOG_W_WIDE)
        lay = vbox(self, SPACE_5, SPACE_3)

        title = QLabel(title_text)
        title.setObjectName("DialogTitle")
        title.setToolTip(
            "Saved for next time: pick them under Bill To. Changes reach this invoice and your drafts; "
            "invoices you already sent keep what they said."
        )
        lay.addWidget(title)

        c = self.client
        sec = Section("Name")
        self.name = QLineEdit(c.name)
        self.name.setPlaceholderText("Company or person")
        sec.add(self.name)
        self.taken = hint("Name taken. Pick that client under Bill To instead.")
        self.taken.hide()
        sec.add(self.taken)
        lay.addWidget(sec)
        sec = Section("Attention")
        self.contact = QLineEdit(c.contact)
        self.contact.setPlaceholderText("Contact person (optional)")
        sec.add(self.contact)
        lay.addWidget(sec)
        sec = Section("Address")
        self.address = TextBox("Street\nCity, State ZIP")
        self.address.set_text(c.address)
        sec.add(self.address)
        lay.addWidget(sec)
        row = hbox(spacing=SPACE_2)
        sec = Section("Email")
        self.email = QLineEdit(c.email)
        self.email.setPlaceholderText("Where invoices go (optional)")
        sec.add(self.email)
        row.addWidget(sec, 1)
        self.code_sec = Section("Code")
        self.code = QLineEdit(c.code)
        self.code.setMaxLength(8)
        self.code.setFixedWidth(NUM_FIELD_W)
        self.code.setToolTip("Goes in invoice numbers that count per client, like JLF-NRTH-2026-001.")
        self.code_sec.add(self.code)
        self.code_sec.setVisible(show_code)
        row.addWidget(self.code_sec)
        lay.addLayout(row)

        lay.addStretch(1)
        buttons = button_row()
        if self.editing and can_delete:
            delete = QPushButton("Delete Client…")
            delete.setObjectName("Danger")
            delete.clicked.connect(self._delete)
            buttons.insertWidget(0, delete)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.save = QPushButton("Save")
        self.save.setObjectName("Primary")
        self.save.setDefault(True)
        self.save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(self.save)
        lay.addLayout(buttons)

        self.name.textChanged.connect(self._name_changed)
        self._name_changed(self.name.text())

    def _name_changed(self, text: str) -> None:
        self.code.setPlaceholderText(numbering.client_code(text))
        other = self.lib.find_client(text)
        taken = other is not None and other.id != self.client.id
        self.taken.setVisible(taken)
        self.save.setEnabled(bool(text.strip()) and not taken)

    def _save(self) -> None:
        self.client = replace(
            self.client,
            name=self.name.text().strip(),
            contact=self.contact.text().strip(),
            address=self.address.text().strip(),
            email=self.email.text().strip(),
            code=numbering.clean_code(self.code.text()),
        )
        self.accept()

    def _delete(self) -> None:
        from cobro.ui.dialogs.common import confirm

        if confirm(
            self,
            f"Delete {self.client.name}?",
            f"{self.client.name} will be taken off your clients. Invoices you already made keep their details.",
            "Delete Client",
        ):
            self.deleted = True
            self.accept()
