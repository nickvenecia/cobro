"""Screenshots of the window without a display, for checking UI changes.

    QT_QPA_PLATFORM=offscreen python tests/screenshot.py OUTDIR

Every shot is taken in dark and in light (…-light.png). Uses a throwaway data folder with the made-up
sample business, never your real invoices.
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
from cobro.core.model import Client
from cobro.core.paths import use_data_dir
from cobro.core.store import Library


def shot(w, path: Path) -> None:
    from PySide6.QtCore import QEventLoop, QTimer

    loop = QEventLoop()
    QTimer.singleShot(400, loop.quit)  # let the preview fit itself to the panel
    loop.exec()
    w.grab().save(str(path))
    print("wrote", path)


def main(out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv[:1])
    use_data_dir(Path(tempfile.mkdtemp(prefix="cobro-shots-")))
    setup_app(app)
    for dark in (True, False):  # every shot in dark, then again in light (…-light.png)
        set_appearance(app, "dark" if dark else "light")
        shots(out, "" if dark else "-light")
    return 0


def shots(out: Path, suffix: str) -> None:
    tmp = Path(tempfile.mkdtemp(prefix="cobro-shots-"))
    use_data_dir(tmp)
    from cobro.ui.dialogs.client import ClientDialog
    from cobro.ui.dialogs.profile import ProfileDialog
    from cobro.ui.window.main_window import MainWindow

    # first launch: nothing set up yet
    w = MainWindow(Library(tmp).load())
    w.show()
    shot(w, out / f"1-first-launch{suffix}.png")
    w.close()

    lib = Library(tmp).load()
    b = lib.add_business(sample.business())
    client = lib.save_client(sample.invoice().client)
    for name in ("Desert Sun Records", "Mesa Coffee Co."):
        lib.save_client(Client(name=name))
    inv = sample.invoice()
    inv.business_id = b.id
    inv.client = client
    lib.save_invoice(inv)
    paid = lib.duplicate(inv)
    paid.status, paid.paid_on, paid.client.name = (
        "paid",
        "2026-10-02",
        "Desert Sun Records",
    )
    lib.save_invoice(paid)
    sent = lib.duplicate(inv)
    sent.status, sent.issued, sent.client.name = "sent", "2026-08-01", "Mesa Coffee Co."
    lib.save_invoice(sent)
    lib.settings["current"] = inv.id
    lib.settings["groups"] = {"look": True}
    w = MainWindow(lib)
    w.show()
    shot(w, out / f"2-invoice{suffix}.png")
    w.details.items[0].set_open(True)
    w.details.scroll.verticalScrollBar().setValue(w.details.scroll.verticalScrollBar().maximum())
    shot(w, out / f"3-look{suffix}.png")
    b.look.type_style, b.look.color, b.look.header = "screenplay", "oxblood", "band"
    w.details.load_look(b)
    w.redraw()
    shot(w, out / f"4-screenplay-band{suffix}.png")
    w.details.set_open_groups({"who": True, "invoice": False, "project": False, "items": True})
    w.details.scroll.verticalScrollBar().setValue(0)
    w.preview.btn_dark.click()
    shot(w, out / f"5-folded-dark-page{suffix}.png")
    w.preview.btn_dark.click()
    d = ProfileDialog(b, False, w)
    d.show()
    shot(d, out / f"6-profile{suffix}.png")
    d.close()
    d = ClientDialog(client, lib, True, show_code=True, parent=w)
    d.show()
    shot(d, out / f"7-client{suffix}.png")
    d.close()
    w.close()


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "shots")))
