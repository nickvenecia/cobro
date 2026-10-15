"""Save a profile in a Mac's own windows: `python tests/mac_windows.py ROUTE` (see ROUTES), on its own data.

Offscreen windows (every other test) never hold the keyboard focus, and the crash saving a profile came from
the focus, so it only ever showed on a real Mac. test_window.py runs this once per route, each in its own
Saldo, so a crash fails just that route. Exits 0 once the profile is saved and Settings is closed again.
"""

from __future__ import annotations

import faulthandler
import os
import sys
import tempfile
from pathlib import Path

faulthandler.enable()  # a crash prints where it happened
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QMenu, QWidget  # noqa: E402

ROUTES = {
    "tile": "Add Your Profile… on the empty page, the first time",
    "settings": "Settings › Profiles, saved twice in a row",
    "card": "the profile card › Edit Profile…",
    "from": "Edit… beside From, on an invoice",
    "add": "From › Add a Profile…",
    "menubar": "Profile › Edit Profile… in the menu bar",
}


def when_open(kind: type, do) -> None:
    """`do(window)` once a window of this kind shows (it opens inside a click, and waits there)."""
    tries = [3000]

    def look() -> None:
        shown = [w for w in QApplication.topLevelWidgets() if isinstance(w, kind) and w.isVisible()]
        if shown:
            do(shown[0])
        elif tries[0]:
            tries[0] -= 1
            QTimer.singleShot(10, look)

    QTimer.singleShot(0, look)


def click(w: QWidget) -> None:
    QTest.mouseClick(w, Qt.MouseButton.LeftButton)


def main(route: str) -> None:
    app = QApplication(sys.argv[:1])
    from saldo.app import setup_app
    from saldo.core import sample
    from saldo.core.paths import use_data_dir
    from saldo.core.store import Library
    from saldo.ui.dialogs.settings import SettingsDialog
    from saldo.ui.window.main_window import MainWindow

    setup_app(app)
    QTimer.singleShot(60_000, lambda: (print("never finished", flush=True), os._exit(3)))
    folder = Path(tempfile.mkdtemp()) / "data"
    use_data_dir(folder)
    lib = Library(folder).load()
    win = MainWindow(lib if route == "tile" else sample.fill(lib))
    win.show()
    names = (
        ["Juniper Lane Films"]
        if route == "tile"
        else ["JLF Edited", "JLF Again"][: 2 if route == "settings" else 1]
    )

    def save(settings) -> None:
        """Type a name (the field keeps the focus, as when you type), click Save, close Settings."""
        QTest.qWait(300)
        for name in names:
            form = settings.profile_editor
            form.name.setFocus()
            form.name.selectAll()
            QTest.keyClicks(form.name, name)
            click(form.save)
            QTest.qWait(400)
        settings.reject()

    def finish() -> None:
        QTest.qWait(500)
        saved = [b.name for b in Library(folder).load().businesses.values()]
        print("profiles:", saved, flush=True)
        win.shutdown()
        os._exit(0 if names[-1] in saved else 4)

    def go() -> None:
        QTest.qWait(500)
        when_open(SettingsDialog, save)
        if route == "tile":
            click(win.empty.tiles[0])
        elif route == "settings":
            win.open_settings("profiles")
        elif route == "card":

            def edit_profile(m) -> None:
                QTest.qWait(200)
                a = next(a for a in m.actions() if a.text() == "Edit Profile…")
                QTest.mouseClick(m, Qt.MouseButton.LeftButton, pos=m.actionGeometry(a).center())

            when_open(QMenu, edit_profile)
            click(win.sidebar.profile_card)
        elif route in ("from", "add"):
            win.open(next(i for i in win.lib.invoices.values() if i.status == "draft").id)
            QTest.qWait(300)
            if route == "from":
                click(win.panel.edit_business)
            else:
                box = win.panel.business
                i = box.findData("__add__")
                box.setCurrentIndex(i)
                box.activated.emit(i)
        elif route == "menubar":
            menus = [m.menu() for m in win.menuBar().actions() if m.menu() is not None]
            next(a for m in menus for a in m.actions() if a.text() == "Edit Profile…").trigger()
        QTimer.singleShot(0, finish)

    QTimer.singleShot(0, go)
    app.exec()


if __name__ == "__main__":
    main(sys.argv[1])
