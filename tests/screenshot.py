"""Screenshots of every screen without a display, for checking UI changes.

    QT_QPA_PLATFORM=offscreen python tests/screenshot.py OUTDIR [--only dark|light|yellow]

Every shot is taken in dark, in light (…-light.png) and once in a light accent (…-yellow.png, to catch
anything that assumed white words on the accent). Uses a throwaway data folder with the made-up sample
business, never your real invoices.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication

from cobro.app import set_appearance, setup_app
from cobro.core import sample
from cobro.core.paths import use_data_dir
from cobro.core.store import Library

SIZE = (1600, 1000)
LOOKS = {"dark": ("dark", "", ""), "light": ("light", "", "-light"), "yellow": ("light", "yellow", "-yellow")}


def wait(ms: int = 400) -> None:
    from PySide6.QtCore import QEventLoop, QTimer

    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def shot(w, path: Path) -> None:
    wait()
    w.grab().save(str(path))
    print("wrote", path)


def shots(out: Path, suffix: str) -> None:
    from cobro.ui.dialogs.common import Alert
    from cobro.ui.dialogs.preview import PageDialog
    from cobro.ui.dialogs.settings import SettingsDialog
    from cobro.ui.window.main_window import MainWindow

    tmp = Path(tempfile.mkdtemp(prefix="cobro-shots-"))
    use_data_dir(tmp)

    def window(lib):
        w = MainWindow(lib)
        w._restored = True  # a fixed size, not the screen's
        w.resize(*SIZE)
        w.show()
        return w

    w = window(Library(tmp).load())
    shot(w, out / f"1-first-launch{suffix}.png")
    w.close()
    empty = Library(tmp).load()
    empty.add_business(sample.business())
    w = window(empty)
    shot(w, out / f"1b-no-invoices{suffix}.png")
    w.close()

    lib = sample.fill(Library(tmp).load())
    w = window(lib)
    shot(w, out / f"2-all-invoices{suffix}.png")
    first = lib.ordered()[0]
    w.open(first.id)
    wait()
    shot(w, out / f"3-invoice-open{suffix}.png")
    w.panel.items[0].set_open(True)
    w.panel.groups["adjustments"].set_open(True)
    wait()
    w.panel.scroll.verticalScrollBar().setValue(w.panel.scroll.verticalScrollBar().maximum())
    shot(w, out / f"4-line-items{suffix}.png")
    from PySide6.QtCore import QPoint

    w.panel.items[0].set_open(False)
    w.panel.scroll.verticalScrollBar().setValue(w.panel.groups["items"].y())
    wait()
    ed = w.panel.items[0]  # a line item lifted halfway down the list
    start = ed.grip.mapToGlobal(ed.grip.rect().center())
    ed.grip.pressed.emit(start)
    for step in range(1, 11):
        ed.grip.moved.emit(start + QPoint(0, 6 * step))
        w.panel._lift._step()
    shot(w, out / f"4c-drag{suffix}.png")
    ed.grip.released.emit(True)
    w.open_ai_assistant()
    w.assistant.say("You", "Is anything spelled wrong?")
    w.assistant.say("AI", "No, everything reads well. The details could be shorter.")
    shot(w, out / f"4b-assistant{suffix}.png")
    from cobro.ui.style import tokens

    w.deselect()
    w.resize(*tokens.WINDOW_MIN)  # the smallest window: everything still fits
    w.open(first.id)
    w.panel.groups["adjustments"].set_open(True)
    wait()
    w.panel.scroll.verticalScrollBar().setValue(w.panel.scroll.verticalScrollBar().maximum())
    shot(w, out / f"12-smallest{suffix}.png")
    w.resize(*SIZE)
    w.deselect()
    w.go("unpaid")
    shot(w, out / f"5-unpaid{suffix}.png")
    w.toast("Saved Cobro Unpaid 2026-10-13.csv.", "done")
    shot(w, out / f"13-toast{suffix}.png")
    w.toast("Couldn't save the CSV. Check that there's free space on this computer.", "problem")
    shot(w, out / f"13b-toast-problem{suffix}.png")
    w.toaster.dismiss()
    w.go("all")
    for name, menu in (("6-filter-menu", w.view_menu.m), ("6b-share-menu", w.btn_export.menu())):
        menu.popup(w.mapToGlobal(w.rect().center()))
        shot(menu, out / f"{name}{suffix}.png")
        menu.close()

    names = iter([f"7-invoice-window{suffix}.png", f"7b-dark-page{suffix}.png"])

    def page_shot(d):
        d.show()
        shot(d, out / next(names))
        d.close()
        return 0

    PageDialog.exec = page_shot
    w.show_page(first.id)
    lib.settings["dark_preview"] = True
    w.show_page(first.id)
    lib.settings["dark_preview"] = False

    d = Alert(
        w, f"Delete {first.number}?", "PDFs you already saved stay where they are.", "Delete", "Cancel", True
    )
    d.show()
    shot(d, out / f"8-alert{suffix}.png")
    d.close()
    for pane in ("general", "profiles", "ai", "account", "shortcuts", "data"):
        d = SettingsDialog(w.lib, w, pane)
        d.show()
        shot(d, out / f"9-settings-{pane}{suffix}.png")
        d.close()
    import importlib.util

    from cobro.core import update
    from cobro.ui.dialogs.client import ClientDialog
    from cobro.ui.dialogs.update import UpdateDialog

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("release_notes", root / "scripts" / "release_notes.py")
    rn = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rn)
    from cobro import __version__

    notes = rn.notes(rn.CHANGELOG.read_text(encoding="utf-8"), __version__)  # what the release will say
    d = UpdateDialog(update.Release(version=__version__, notes=notes), parent=w)
    d.show()
    shot(d, out / f"11-update{suffix}.png")
    d.close()

    d = ClientDialog(first.client, lib, True, show_code=True, parent=w)
    d.show()
    shot(d, out / f"10-client{suffix}.png")
    d.close()
    w.close()


def main(out: Path, only: str = "") -> int:
    out.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv[:1])
    use_data_dir(Path(tempfile.mkdtemp(prefix="cobro-shots-")))
    setup_app(app)
    for key, (appearance, accent, suffix) in LOOKS.items():
        if only and key != only:
            continue
        set_appearance(app, appearance, accent)
        shots(out, suffix)
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    only = args[args.index("--only") + 1] if "--only" in args else ""
    sys.exit(main(Path(args[0] if args else "shots"), only))
