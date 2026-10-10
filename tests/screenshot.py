"""Screenshots of the window without a display, for checking UI changes.

    QT_QPA_PLATFORM=offscreen python tests/screenshot.py OUTDIR

Uses a throwaway data folder with the made-up sample business, never your real invoices.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication

from cobro.app import setup_app
from cobro.core import sample
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
    tmp = Path(tempfile.mkdtemp(prefix="cobro-shots-"))
    use_data_dir(tmp)
    setup_app(app)
    from cobro.ui.business_dialog import BusinessDialog
    from cobro.ui.main_window import MainWindow

    # first launch: nothing set up yet
    w = MainWindow(Library(tmp).load())
    w.show()
    shot(w, out / "1-first-launch.png")
    w.close()

    lib = Library(tmp).load()
    b = lib.add_business(sample.business())
    inv = sample.invoice()
    inv.business_id = b.id
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
    shot(w, out / "2-invoice.png")
    w.details.scroll.verticalScrollBar().setValue(w.details.scroll.verticalScrollBar().maximum())
    shot(w, out / "3-look.png")
    b.look.type_style, b.look.color, b.look.header = "screenplay", "oxblood", "band"
    w.details.load_look(b)
    w.redraw()
    shot(w, out / "4-screenplay-band.png")
    d = BusinessDialog(b, False, w)
    d.show()
    shot(d, out / "5-business.png")
    d.close()
    w.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "shots")))
