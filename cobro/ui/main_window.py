"""The window: ① Invoices | ② Details | ③ Preview, left to right in the order you work.

Edits save themselves (a moment after you stop typing) and redraw the preview. Nothing needs a
Save button except the PDF itself.
"""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QByteArray, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QGuiApplication, QKeySequence
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMenu, QWidget

from .. import __version__
from ..core import document, update
from ..core.fileutil import reveal
from ..core.log import get_logger
from ..core.looks import resolve
from ..core.model import Business, Invoice
from ..core.paths import data_dir, documents_dir, log_dir, logos_dir
from ..core.store import Library
from ..doc import export, fonts, render
from . import theme, titlebar, tokens
from .business_dialog import BusinessDialog
from .details import DetailsPanel
from .dialogs import about, confirm
from .invoice_list import InvoiceList
from .preview import PreviewPanel
from .widgets import Toast, hbox, vbox

log = get_logger(__name__)

SAVE_DELAY_MS = 400  # save this long after the last keystroke
DRAW_DELAY_MS = 90  # redraw the preview this long after the last change


class MainWindow(QMainWindow):
    def __init__(self, lib: Library | None = None):
        super().__init__()
        self.lib = lib or Library().load()
        self.setWindowTitle("Cobro")
        self.resize(*tokens.WINDOW_SIZE)
        self.setMinimumSize(*tokens.WINDOW_MIN)
        self._dirty: set[str] = set()
        self._fonts = fonts.installed_families()
        self.last_export: Path | None = None
        self._release: update.Release | None = None

        root = QWidget()
        root.setObjectName("Root")
        outer = vbox(root, 0, 0)
        self.titlebar = titlebar.install(self)
        if self.titlebar is not None:
            outer.addWidget(self.titlebar)
        body = hbox(spacing=0)
        self.list = InvoiceList(self.lib)
        self.details = DetailsPanel(self.lib)
        self.preview = PreviewPanel()
        body.addWidget(self.list)
        body.addWidget(self.details)
        body.addWidget(self.preview, 1)
        outer.addLayout(body, 1)
        self.setCentralWidget(root)
        self.toaster = Toast(self)

        self._save_timer = QTimer(self, singleShot=True, interval=SAVE_DELAY_MS, timeout=self.flush)
        self._draw_timer = QTimer(self, singleShot=True, interval=DRAW_DELAY_MS, timeout=self.redraw)

        self._wire()
        self._menus()
        self.details.set_open_groups(self.lib.settings.get("groups", {}))
        geo = self.lib.settings.get("geometry")
        if isinstance(geo, str) and geo:
            self.restoreGeometry(QByteArray.fromHex(geo.encode()))
        self.list.refresh()
        self._start()

    # ------------------------------------------------------------------ setup
    def _wire(self) -> None:
        self.list.picked.connect(self.open_invoice)
        self.list.new_wanted.connect(self.new_invoice)
        self.list.duplicate_wanted.connect(self.duplicate)
        self.list.delete_wanted.connect(self.delete)
        self.list.btn_update.clicked.connect(self.show_update)
        self.details.invoice_changed.connect(self._invoice_edited)
        self.details.status_changed.connect(self._status_changed)
        self.details.look_changed.connect(self._look_edited)
        self.details.business_wanted.connect(lambda kind: self.edit_business(kind == "add"))
        self.details.defaults_saved.connect(self._defaults_saved)
        self.details.groups_changed.connect(self._groups_changed)
        self.preview.save_pdf.connect(self.save_pdf)
        self.preview.print_wanted.connect(self.print_invoice)
        self.preview.save_png.connect(self.save_png)
        self.preview.copy_text.connect(self.copy_text)
        self.preview.open_folder.connect(self.open_folder)
        self.preview.show_file.connect(lambda: self.last_export and reveal(self.last_export))
        self.preview.mark_sent.connect(self._mark_sent)

    def _menus(self) -> None:
        """Commands with shortcuts. The menu bar shows on the Mac; on Windows/Linux it's hidden (no strip
        across the window) and the shortcuts still work, with the same commands in the ⋯ menus."""
        bar = self.menuBar()

        def act(menu: QMenu, text: str, slot, keys=None) -> QAction:
            a = menu.addAction(text)
            a.triggered.connect(slot)
            if keys is not None:
                a.setShortcut(QKeySequence(keys))
                self.addAction(a)  # shortcuts work with the bar hidden
            return a

        f = bar.addMenu("File")
        act(f, "New Invoice", self.new_invoice, QKeySequence.StandardKey.New)
        act(f, "Duplicate Invoice", self._duplicate_current, "Ctrl+D")
        f.addSeparator()
        act(f, "Save PDF…", self.save_pdf, QKeySequence.StandardKey.Save)
        act(f, "Save as PNG…", self.save_png)
        act(f, "Print…", self.print_invoice, QKeySequence.StandardKey.Print)
        f.addSeparator()
        act(f, "Delete Invoice…", self._delete_current)
        b = bar.addMenu("Business")
        act(b, "Edit Business…", lambda: self.edit_business(False))
        act(b, "Add a Business…", lambda: self.edit_business(True))
        h = bar.addMenu("Help")
        act(h, "Check for Updates…", self.check_updates)
        act(
            h,
            "Open Data Folder",
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir()))),
        )
        act(h, "Open Log File", lambda: reveal(log_dir() / "cobro.log"))
        act(h, "About Cobro", lambda: about(self, __version__, str(data_dir())))
        bar.setVisible(sys_is_mac())

        # the same tools under ⋯ in the list's bottom bar, on every system
        m = QMenu(self.list.btn_more)
        m.addAction(theme.menu_icon("edit"), "Edit Business…", lambda: self.edit_business(False))
        m.addAction(theme.menu_icon("plus"), "Add a Business…", lambda: self.edit_business(True))
        m.addSeparator()
        m.addAction(theme.menu_icon("retry"), "Check for Updates…", self.check_updates)
        auto = m.addAction("Check for Updates Daily")
        auto.setCheckable(True)
        auto.setChecked(bool(self.lib.settings.get("auto_update", True)))
        auto.toggled.connect(self._set_auto_update)
        m.addSeparator()
        m.addAction(
            theme.menu_icon("folder"),
            "Open Data Folder",
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir()))),
        )
        m.addAction(
            theme.menu_icon("info"),
            "About Cobro",
            lambda: about(self, __version__, str(data_dir())),
        )
        self.list.btn_more.setMenu(m)

    def _start(self) -> None:
        if not self.lib.businesses:
            self.details.show_empty("business", lambda: self.edit_business(True))
            self.preview.clear("Your invoice shows up here.")
            return
        last = self.lib.settings.get("current", "")
        if last in self.lib.invoices:
            self.open_invoice(last)
        elif self.lib.invoices:
            self.open_invoice(self.lib.ordered()[0].id)
        else:
            self.details.show_empty("invoice", self.new_invoice)
            self.preview.clear("Your invoice shows up here.")
        QTimer.singleShot(8000, self._auto_check_updates)

    # ------------------------------------------------------------------ invoices
    @property
    def inv(self) -> Invoice | None:
        return self.details.inv

    def open_invoice(self, inv_id: str) -> None:
        if self.inv is not None and self.inv.id == inv_id:
            return
        self.flush()
        self._remember_client()
        inv = self.lib.invoices.get(inv_id)
        if inv is None:
            return
        if inv.business_id not in self.lib.businesses and self.lib.businesses:
            inv.business_id = next(iter(self.lib.businesses))  # its business was deleted
        self.details.load(inv)
        self.list.select(inv.id)
        self.preview.saved_hint(None, False)
        self.lib.settings["current"] = inv.id
        self.redraw()

    def default_business(self) -> Business | None:
        cur = self.details.current_business()
        if cur is not None:
            return cur
        last = self.lib.settings.get("business", "")
        return self.lib.businesses.get(last) or next(iter(self.lib.businesses.values()), None)

    def new_invoice(self) -> None:
        b = self.default_business()
        if b is None:
            self.edit_business(True)
            return
        self.flush()
        inv = self.lib.new_invoice(b)
        self.list.refresh()
        self.open_invoice(inv.id)
        self.details.client.setFocus()

    def _duplicate_current(self) -> None:
        if self.inv is not None:
            self.duplicate(self.inv.id)

    def duplicate(self, inv_id: str) -> None:
        self.flush()
        src = self.lib.invoices.get(inv_id)
        if src is None:
            return
        copy = self.lib.duplicate(src)
        self.list.refresh()
        self.open_invoice(copy.id)
        self.toast(f"Made {copy.number} from {src.number}.")

    def _delete_current(self) -> None:
        if self.inv is not None:
            self.delete(self.inv.id)

    def delete(self, inv_id: str) -> None:
        inv = self.lib.invoices.get(inv_id)
        if inv is None:
            return
        who = f" for {inv.client.name}" if inv.client.name.strip() else ""
        if not confirm(
            self,
            f"Delete {inv.number}?",
            f"The invoice{who} will be removed from Cobro. PDFs you already saved stay where they are.",
            "Delete Invoice",
        ):
            return
        self._dirty.discard(inv_id)
        self.lib.delete_invoice(inv_id)
        log.info("deleted invoice %s", inv.number)
        if self.inv is not None and self.inv.id == inv_id:
            self.details.inv = None
            rest = self.lib.ordered()
            if rest:
                self.list.refresh()
                self.open_invoice(rest[0].id)
            else:
                self.details.show_empty("invoice", self.new_invoice)
                self.preview.clear("Your invoice shows up here.")
        self.list.refresh()

    def _invoice_edited(self, inv: Invoice) -> None:
        self._dirty.add(inv.id)
        self._save_timer.start()
        self._draw_timer.start()
        self.list.update_card(inv)
        self.preview.saved_hint(None, False)

    def _status_changed(self, inv: Invoice) -> None:
        self._remember_client()
        self.flush()
        self.list.refresh()

    def flush(self) -> None:
        """Write any edited invoices now."""
        for inv_id in list(self._dirty):
            inv = self.lib.invoices.get(inv_id)
            if inv is not None:
                try:
                    self.lib.save_invoice(inv)
                except OSError:
                    log.warning("couldn't save %s", inv.number, exc_info=True)
                    self.toast("Couldn't save the invoice. Check that there's free space on this computer.")
                    continue
            self._dirty.discard(inv_id)

    def _remember_client(self) -> None:
        """Keep the client for next time (only finished names, so half-typed ones never pile up)."""
        if self.inv is None:
            return
        saved = self.lib.remember_client(self.inv.client)
        if saved is not None and self.inv.client.id != saved.id:
            self.inv.client.id = saved.id
            self._dirty.add(self.inv.id)

    # ------------------------------------------------------------------ business + look
    def edit_business(self, add: bool) -> None:
        current = None if add else self.default_business()
        can_delete = (
            current is not None
            and len(self.lib.businesses) > 1
            and not any(i.business_id == current.id for i in self.lib.invoices.values())
        )
        d = BusinessDialog(current, can_delete, self)
        if d.exec() != BusinessDialog.DialogCode.Accepted:
            return
        if d.deleted and current is not None:
            self.lib.delete_business(current.id)
            self.toast(f"Deleted {current.name}.")
            return
        b = d.business
        first = not self.lib.businesses
        if current is None:
            self.lib.add_business(b)
            log.info("added business %s", b.name)
        else:
            self.lib.businesses[b.id] = b
            self.lib.save_businesses()
        self.lib.settings["business"] = b.id
        if first or (add and self.inv is None):
            self.new_invoice()
        elif add and self.inv is not None:
            self.toast(f"Added {b.name}. Pick it under From, or start a new invoice.")
            self.details.refresh_businesses()
        else:
            if self.inv is not None:
                self.details.load(self.inv)
            self.list.refresh()
            self.redraw()

    def _look_edited(self, b: Business) -> None:
        self.lib.businesses[b.id] = b
        try:
            self.lib.save_businesses()
        except OSError:
            log.warning("couldn't save the look", exc_info=True)
        self._draw_timer.start()

    def _defaults_saved(self, b: Business) -> None:
        self.lib.save_businesses()
        self.toast(f"New invoices from {b.name} will start with this payment text and terms.")

    def _groups_changed(self, groups: dict) -> None:
        self.lib.settings["groups"] = groups

    # ------------------------------------------------------------------ drawing
    def pages(self) -> list[render.Page]:
        inv = self.inv
        b = self.details.current_business()
        if inv is None or b is None:
            return []
        view = document.build(inv, b)
        logo = logos_dir() / b.look.logo if b.look.logo else None
        return render.layout(view, resolve(b.look, self._fonts), logo)

    def redraw(self) -> None:
        pages = self.pages()
        if pages:
            self.preview.set_pages(pages)
        else:
            self.preview.clear("Your invoice shows up here.")

    # ------------------------------------------------------------------ exporting
    def _export_folder(self) -> Path:
        saved = self.lib.settings.get("export_dir")
        if isinstance(saved, str) and Path(saved).is_dir():
            return Path(saved)
        return documents_dir()

    def _ask_path(self, title: str, suffix: str, kinds: str) -> Path | None:
        if self.inv is None:
            return None
        self.flush()
        folder = self._export_folder()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            folder = Path.home()
        default = folder / f"{document.file_stem(self.inv)}{suffix}"
        path, _ = QFileDialog.getSaveFileName(self, title, str(default), kinds)
        if not path:
            return None
        p = Path(path)
        if p.suffix.lower() != suffix:
            p = p.with_name(p.name + suffix)
        self.lib.settings["export_dir"] = str(p.parent)
        return p

    def _exported(self, path: Path) -> None:
        self.last_export = path
        self._remember_client()
        self.flush()
        self.preview.saved_hint(path.name, self.inv is not None and self.inv.status == "draft")

    def save_pdf(self) -> None:
        pages = self.pages()
        if not pages:
            return
        path = self._ask_path("Save PDF", ".pdf", "PDF (*.pdf)")
        if path is None:
            return
        try:
            export.to_pdf(pages, path, title=f"Invoice {self.inv.number}")
        except OSError as e:
            log.warning("PDF not saved", exc_info=True)
            self.toast(str(e) or "Couldn't save the PDF.")
            return
        self._exported(path)

    def save_png(self) -> None:
        pages = self.pages()
        if not pages:
            return
        path = self._ask_path("Save as PNG", ".png", "PNG picture (*.png)")
        if path is None:
            return
        try:
            files = export.to_png(pages, path)
        except OSError as e:
            log.warning("PNG not saved", exc_info=True)
            self.toast(str(e) or "Couldn't save the picture.")
            return
        self._exported(files[0])

    def print_invoice(self) -> None:
        pages = self.pages()
        if not pages:
            return
        try:
            from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        except ImportError:
            self.toast("Printing isn't available here. Save a PDF and print that instead.")
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setDocName(f"Invoice {self.inv.number}")
        dlg = QPrintDialog(printer, self)
        if dlg.exec() != QPrintDialog.DialogCode.Accepted:
            return
        try:
            export.print_pages(printer, pages)
        except OSError as e:
            log.warning("print failed", exc_info=True)
            self.toast(str(e))
            return
        self._remember_client()
        self.toast("Sent to the printer.")

    def copy_text(self) -> None:
        if self.inv is None:
            return
        b = self.details.current_business()
        if b is None:
            return
        QGuiApplication.clipboard().setText(document.summary_text(document.build(self.inv, b)))
        self.toast("Copied. Paste it into an email or a message.")

    def open_folder(self) -> None:
        folder = self._export_folder()
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _mark_sent(self) -> None:
        if self.inv is not None and self.inv.status == "draft":
            self.details.set_status("sent")
            self.preview.saved_hint(self.last_export.name if self.last_export else None, False)

    # ------------------------------------------------------------------ updates
    def _set_auto_update(self, on: bool) -> None:
        self.lib.settings["auto_update"] = on

    def _auto_check_updates(self) -> None:
        if not self.lib.settings.get("auto_update", True) or update.install_kind() == "source":
            return
        last = float(self.lib.settings.get("last_update_check", 0) or 0)
        if time.time() - last < update.CHECK_EVERY_S:
            return
        self.check_updates(quiet=True)

    def check_updates(self, quiet: bool = False) -> None:
        from .update_dialog import CheckThread

        self._check = CheckThread(self)
        self._check.found.connect(lambda rel: self._found_release(rel, quiet))
        self._check.failed.connect(
            lambda _m: (
                None if quiet else self.toast("Couldn't reach GitHub. Check your internet and try again.")
            )
        )
        self._check.start()

    def _found_release(self, rel: update.Release, quiet: bool) -> None:
        self.lib.settings["last_update_check"] = time.time()
        if rel.newer:
            self._release = rel
            self.list.btn_update.setText(f"Update to {rel.version}")
            self.list.btn_update.show()
            if not quiet:
                self.show_update()
        elif not quiet:
            self.toast(f"You have the newest Cobro ({__version__}).")

    def show_update(self) -> None:
        if self._release is None:
            return
        from .update_dialog import UpdateDialog, restart_into

        d = UpdateDialog(self._release, parent=self)
        if d.exec() == UpdateDialog.DialogCode.Accepted and d.plan is not None:
            self.shutdown()
            restart_into(d.plan)

    # ------------------------------------------------------------------ misc
    def toast(self, text: str) -> None:
        self.toaster.show_message(text)

    def showEvent(self, e):
        super().showEvent(e)
        if self.titlebar is not None:
            QTimer.singleShot(0, self.titlebar.fit)

    def closeEvent(self, e):
        self.shutdown()
        super().closeEvent(e)

    def shutdown(self) -> None:
        """Save everything before quitting."""
        self._remember_client()
        self.flush()
        self.lib.settings["geometry"] = bytes(self.saveGeometry().toHex()).decode()
        try:
            self.lib.save_settings()
        except OSError:
            log.warning("couldn't save settings", exc_info=True)


def sys_is_mac() -> bool:
    import sys

    return sys.platform == "darwin"
