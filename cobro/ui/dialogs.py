"""Small dialogs: confirming something that can't be undone, and the About box."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QWidget

from .tokens import DIALOG_W, SPACE_2, SPACE_3, SPACE_5
from .widgets import Wordmark, hbox, hint, vbox


def confirm(parent: QWidget, title: str, text: str, action: str, danger: bool = True) -> bool:
    """Ask before doing something that can't be undone. The safe answer (Cancel) is the default."""
    d = QDialog(parent)
    d.setWindowTitle(title)
    d.setMinimumWidth(DIALOG_W)
    lay = vbox(d, SPACE_5, SPACE_3)
    t = QLabel(title)
    t.setObjectName("DialogTitle")
    lay.addWidget(t)
    lay.addWidget(hint(text))
    row = hbox(spacing=SPACE_2)
    row.addStretch(1)
    cancel = QPushButton("Cancel")
    cancel.setDefault(True)
    cancel.clicked.connect(d.reject)
    go = QPushButton(action)
    go.setObjectName("Danger" if danger else "Primary")
    go.clicked.connect(d.accept)
    row.addWidget(cancel)
    row.addWidget(go)
    lay.addLayout(row)
    return d.exec() == QDialog.DialogCode.Accepted


def about(parent: QWidget, version: str, data_folder: str) -> None:
    d = QDialog(parent)
    d.setWindowTitle("About Cobro")
    d.setMinimumWidth(DIALOG_W)
    lay = vbox(d, SPACE_5, SPACE_3)
    lay.addWidget(Wordmark())
    lay.addWidget(hint(f"Version {version}. Make an invoice, send it, get paid."))
    lay.addWidget(hint(f"Your invoices are saved on this computer only, in {data_folder}"))
    lay.addWidget(
        hint("Open source under GPL-3.0. Fonts under the SIL Open Font License. Made by Bad Filmmaker.")
    )
    row = hbox()
    row.addStretch(1)
    ok = QPushButton("Done")
    ok.setObjectName("Primary")
    ok.clicked.connect(d.accept)
    row.addWidget(ok)
    lay.addLayout(row)
    d.exec()
