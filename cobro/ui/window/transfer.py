"""Getting things out of Cobro: the invoices showing as a CSV, and a backup of everything.

A part of MainWindow (see main_window.py); it uses the window's widgets and the library."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMenu

from cobro.core import dates, spreadsheet
from cobro.core.log import get_logger
from cobro.core.paths import data_dir, documents_dir
from cobro.ui.dialogs.common import notice
from cobro.ui.style import theme

log = get_logger(__name__)


class TransferMixin:
    def _share_menu(self) -> None:
        """The round share button's menu: the invoice picked, the list as a CSV, a backup."""
        m = QMenu(self.btn_export)
        m.addAction(theme.menu_icon("receipt"), "Invoice…", self.show_page)
        m.addSeparator()
        m.addAction(theme.menu_icon("table"), "Export as CSV…", self.export_csv)
        m.addAction(theme.menu_icon("box"), "Back Up…", self.back_up)
        self.btn_export.setMenu(m)

    def export_csv(self) -> None:
        """The invoices showing (this place, the filter and the search), one row each; from All Clients,
        every invoice."""
        self.flush()
        if self.on_clients():
            invoices = self.lib.ordered()
        else:
            ids = set(self.table.show_only(self.search.text()))
            invoices = [inv for inv in self._showing() if inv.id in ids]
        if not invoices:
            self.toast("No invoices to export.", "problem")
            return
        place = "All Invoices" if self.on_clients() else self.title.text()
        name = f"Cobro {place} {dates.iso(dates.today())}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export as CSV", str(self._export_folder() / name), "CSV (*.csv)"
        )
        if not path:
            return
        p = Path(path)
        if p.suffix.lower() != ".csv":
            p = p.with_name(p.name + ".csv")
        try:
            spreadsheet.write_csv(invoices, self.lib.businesses, p)
        except OSError:
            log.warning("CSV not saved", exc_info=True)
            self.toast("Couldn't save the CSV.", "problem")
            return
        self.last_export = p
        self.toast(f"Saved {p.name}.", "done")

    def back_up(self) -> None:
        """Save everything (invoices, clients, profiles, logos, settings) as one zip file."""
        from cobro.core.fileutil import zip_folder

        self.flush()
        name = f"Cobro Backup {dates.iso(dates.today())}.zip"
        path, _ = QFileDialog.getSaveFileName(
            self, "Back Up", str(documents_dir() / name), "Zip Files (*.zip)"
        )
        if not path:
            return
        try:
            zip_folder(data_dir(), Path(path), skip=("ui",))
        except OSError as e:
            notice(self, "Couldn't back up", str(e))
            return
        self.toast("Backed up.", "done")
