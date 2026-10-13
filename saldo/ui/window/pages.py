"""The invoice's own window: the page, and PDF, PNG, print, copy, email.

A part of MainWindow (see main_window.py); it uses the window's widgets and the library."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QFileDialog

from saldo.core import document
from saldo.core.fileutil import reveal
from saldo.core.log import get_logger
from saldo.core.looks import resolve
from saldo.core.model import Invoice
from saldo.core.paths import documents_dir, logo_path
from saldo.doc import export, render
from saldo.ui.dialogs.preview import PageDialog

log = get_logger(__name__)


class PagesMixin:
    def show_page(self, inv_id: str = "") -> None:
        """Open an invoice (the one picked, by default) in its own window."""
        inv_id = inv_id or (self.panel.inv.id if self.panel.inv is not None else "")
        if inv_id not in self.lib.invoices:
            self.toast("Pick an invoice first.", "problem")
            return
        self.flush()
        self.page_inv = inv_id
        d = PageDialog(self)
        self.page = d
        panel = d.panel
        inv = self.lib.invoices[inv_id]
        panel.header.set_title(f"Invoice {inv.number}")
        panel.set_dark(bool(self.lib.settings.get("dark_preview", False)))
        panel.save_pdf.connect(self.save_pdf)
        panel.print_wanted.connect(self.print_invoice)
        panel.save_png.connect(self.save_png)
        panel.copy_text.connect(self.copy_text)
        panel.open_folder.connect(self.open_folder)
        panel.show_file.connect(lambda: self.last_export and reveal(self.last_export))
        panel.mark_sent.connect(self._mark_sent)
        panel.email_wanted.connect(self.email_client)
        panel.dark_changed.connect(self._dark_changed)
        self.redraw()
        d.exec()
        self.page = None
        self.refresh()

    def _page_invoice(self) -> Invoice | None:
        return self.lib.invoices.get(self.page_inv) if self.page_inv else self.panel.inv

    def page_list(self, dark: bool = False) -> list[render.Page]:
        """The invoice, laid out. `dark` is only ever for the page window's Dark Page: everything that
        leaves Saldo (PDF, PNG, print) is drawn on white paper."""
        inv = self._page_invoice()
        b = self.lib.businesses.get(inv.business_id) if inv is not None else None
        if inv is None or b is None:
            return []
        view = document.build(inv, b)
        logo = logo_path(b.look.logo)
        return render.layout(view, resolve(b.look, dark=dark), logo)

    def redraw(self) -> None:
        if self.page is None:
            return
        panel = self.page.panel
        pages = self.page_list(dark=panel.dark)
        if pages:
            panel.set_pages(pages)
        else:
            panel.clear("Nothing to show.")

    # ------------------------------------------------------------------ exporting
    def _export_folder(self) -> Path:
        saved = self.lib.settings.get("export_dir")
        if isinstance(saved, str) and Path(saved).is_dir():
            return Path(saved)
        return documents_dir()

    def _ask_path(self, title: str, suffix: str, kinds: str) -> Path | None:
        inv = self._page_invoice()
        if inv is None:
            return None
        self.flush()
        folder = self._export_folder()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            folder = Path.home()
        default = folder / f"{document.file_stem(inv)}{suffix}"
        path, _ = QFileDialog.getSaveFileName(self.page or self, title, str(default), kinds)
        if not path:
            return None
        p = Path(path)
        if p.suffix.lower() != suffix:
            p = p.with_name(p.name + suffix)
        self.lib.settings["export_dir"] = str(p.parent)
        return p

    def _exported(self, path: Path) -> None:
        self.last_export = path
        self.flush()
        inv = self._page_invoice()
        if self.page is not None:
            self.page.panel.saved_hint(path.name, inv is not None and inv.status == "draft")

    def save_pdf(self) -> None:
        pages = self.page_list()
        if not pages:
            return
        path = self._ask_path("Save PDF", ".pdf", "PDF (*.pdf)")
        if path is None:
            return
        try:
            export.to_pdf(pages, path, title=f"Invoice {self._page_invoice().number}")
        except OSError as e:
            log.warning("PDF not saved", exc_info=True)
            self.toast(str(e) or "Couldn't save the PDF.", "problem")
            return
        self._exported(path)

    def save_png(self) -> None:
        pages = self.page_list()
        if not pages:
            return
        path = self._ask_path("Save as PNG", ".png", "PNG picture (*.png)")
        if path is None:
            return
        try:
            files = export.to_png(pages, path)
        except OSError as e:
            log.warning("PNG not saved", exc_info=True)
            self.toast(str(e) or "Couldn't save the picture.", "problem")
            return
        self._exported(files[0])

    def print_invoice(self) -> None:
        pages = self.page_list()
        if not pages:
            return
        try:
            from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        except ImportError:
            self.toast("Printing isn't available here. Save a PDF and print that instead.", "problem")
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setDocName(f"Invoice {self._page_invoice().number}")
        dlg = QPrintDialog(printer, self.page or self)
        if dlg.exec() != QPrintDialog.DialogCode.Accepted:
            return
        try:
            export.print_pages(printer, pages)
        except OSError as e:
            log.warning("print failed", exc_info=True)
            self.toast(str(e), "problem")
            return
        self.toast("Sent to the printer.", "done")

    def print_current(self) -> None:
        """⌘P: the invoice's window, ready to print (or print right away from inside it)."""
        if self.page is not None:
            self.print_invoice()
        else:
            self.show_page()

    def copy_text(self) -> None:
        inv = self._page_invoice()
        b = self.lib.businesses.get(inv.business_id) if inv is not None else None
        if inv is None or b is None:
            return
        QGuiApplication.clipboard().setText(document.summary_text(document.build(inv, b)))
        self.toast("Copied. Paste it into an email or a message.", "done")

    def email_client(self) -> None:
        """A new email to the client with the summary in it; the saved PDF is shown, ready to drag in."""
        inv = self._page_invoice()
        b = self.lib.businesses.get(inv.business_id) if inv is not None else None
        if inv is None or b is None:
            return
        subject = f"Invoice {inv.number}" + (f": {inv.project}" if inv.project.strip() else "")
        body = document.summary_text(document.build(inv, b)) + "\n\nThe invoice is attached."
        if b.name:
            body += f"\n\n{b.name}"
        QDesktopServices.openUrl(
            QUrl(f"mailto:{quote(inv.client.email.strip())}?subject={quote(subject)}&body={quote(body)}")
        )
        if self.last_export is not None and self.last_export.exists():
            reveal(self.last_export)

    def open_folder(self) -> None:
        folder = self._export_folder()
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _dark_changed(self, on: bool) -> None:
        self.lib.settings["dark_preview"] = on
        self.redraw()

    def _mark_sent(self) -> None:
        inv = self._page_invoice()
        if inv is None or inv.status != "draft":
            return
        if self.panel.inv is inv:
            self.panel.set_status("sent")
        else:
            from saldo.core import dates

            inv.status, inv.auto_number = "sent", False
            inv.sent_on = inv.sent_on or dates.iso(dates.today())
            self._dirty.add(inv.id)
            self.flush()
        if self.page is not None:
            self.page.panel.saved_hint(self.last_export.name if self.last_export else None, False)
        self.redraw()
