"""The menu bar (Mac) and the profile card's menu: every command with its shortcut.

A part of MainWindow (see main_window.py); it uses the window's widgets and the library."""

from __future__ import annotations

import sys

from PySide6.QtCore import QPoint
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QLineEdit, QMenu, QPlainTextEdit, QTextEdit

from cobro import __version__
from cobro.core import billing, money
from cobro.core.fileutil import reveal
from cobro.core.paths import data_dir, log_dir
from cobro.ui.dialogs.common import about
from cobro.ui.style import theme, tokens
from cobro.ui.window.common import PLACES


class MenusMixin:
    def _menus(self) -> None:
        """Commands with shortcuts. The menu bar shows on the Mac; on Windows/Linux it's hidden and the
        shortcuts still work, with the same commands in the profile card's menu and the toolbar."""
        bar = self.menuBar()

        def act(m: QMenu, text: str, slot, keys=None) -> QAction:
            a = m.addAction(text)
            a.triggered.connect(slot)
            if keys is not None:
                a.setShortcut(QKeySequence(keys))
                self.addAction(a)
            return a

        f = bar.addMenu("File")
        act(f, "New Invoice", self.new_invoice, QKeySequence.StandardKey.New)
        f.addSeparator()
        act(f, "Invoice…", self.show_page, "Ctrl+O")
        act(f, "Print…", self.print_current, QKeySequence.StandardKey.Print)
        f.addSeparator()
        act(f, "Export as CSV…", self.export_csv, "Ctrl+Shift+E")
        act(f, "Back Up…", self.back_up)
        f.addSeparator()
        prefs = act(f, "Settings…", self.open_settings, QKeySequence.StandardKey.Preferences)
        prefs.setMenuRole(QAction.MenuRole.PreferencesRole)  # the Mac puts it under Cobro, ⌘,
        if sys.platform != "darwin":
            prefs.setShortcut(QKeySequence("Ctrl+,"))  # (Windows and Linux have no standard key for it)
        quit_ = act(f, "Quit Cobro", self.close, QKeySequence.StandardKey.Quit)
        quit_.setMenuRole(QAction.MenuRole.QuitRole)

        e = bar.addMenu("Edit")
        self.act_undo = act(e, "Undo", self.undo, QKeySequence.StandardKey.Undo)
        self.act_redo = act(e, "Redo", self.redo, "Ctrl+Shift+Z")
        if sys.platform != "darwin":  # Ctrl+Y too, as Windows apps do
            self.act_redo.setShortcuts([QKeySequence("Ctrl+Shift+Z"), QKeySequence("Ctrl+Y")])
        e.aboutToShow.connect(self._edit_menu_state)
        e.addSeparator()
        act(e, "Cut", lambda: self._text_do("cut"), QKeySequence.StandardKey.Cut)
        act(e, "Copy", self.copy, QKeySequence.StandardKey.Copy)
        act(e, "Paste", lambda: self._text_do("paste"), QKeySequence.StandardKey.Paste)
        act(e, "Select All", self.select_all, QKeySequence.StandardKey.SelectAll)
        e.addSeparator()
        act(e, "Duplicate", self._duplicate_current, "Ctrl+D")
        act(e, "Delete…", self.delete_selected, "Ctrl+Backspace")
        e.addSeparator()
        act(e, "Find", self._focus_search, QKeySequence.StandardKey.Find)

        v = bar.addMenu("View")
        for n, (key, (title, _icon)) in enumerate(PLACES.items(), start=1):
            act(v, title, lambda _c=False, k=key: self.go(k), f"Ctrl+{n}")
        act(v, "Close Panel", self.deselect)
        v.addSeparator()
        self.look_actions = {}
        looks = v.addMenu("Appearance")
        for key, label in (("system", "Match System"), ("light", "Light"), ("dark", "Dark")):
            a = looks.addAction(label)
            a.setCheckable(True)
            a.triggered.connect(lambda _c=False, k=key: self.set_look(k))
            self.look_actions[key] = a

        b = bar.addMenu("Profile")
        act(b, "Edit Profile…", lambda: self.edit_business(not self.lib.businesses))
        act(b, "Add a Profile…", lambda: self.edit_business(True))
        act(b, "New Client…", lambda: self.edit_client(True, assign=False), "Ctrl+Shift+N")
        ai = bar.addMenu("AI")
        act(ai, "Assistant", self.toggle_assistant, "Ctrl+J")
        ai.addSeparator()
        act(ai, "Tidy Up Line Items…", lambda: self.open_ai_assistant("tidy"))
        ai.addSeparator()
        act(ai, "AI Settings…", self.open_ai_setup)
        w = bar.addMenu("Window")
        act(w, "Minimize", self.showMinimized, "Ctrl+M")
        act(w, "Zoom", self.toggle_zoom)
        h = bar.addMenu("Help")
        act(h, "Keyboard Shortcuts", self.show_shortcuts, "Ctrl+/")
        act(h, "Send Feedback…", self.open_feedback)
        upd = act(h, "Check for Updates…", self.check_updates)
        upd.setMenuRole(QAction.MenuRole.ApplicationSpecificRole)  # on the Mac: in the Cobro menu
        act(h, "Open Data Folder", self.open_data_folder)
        act(h, "Open Log File", lambda: reveal(log_dir() / "cobro.log"))
        act(h, "About Cobro", lambda: about(self, __version__, str(data_dir())))
        bar.setVisible(sys.platform == "darwin")
        self._share_menu()

    def _app_menu(self) -> None:
        """The profile card's menu: your profiles (pick one to work as), feedback, updates, and Settings."""
        card = self.sidebar.profile_card
        m = QMenu(card)
        current = self.business()
        if len(self.lib.businesses) > 1:
            for b in self.lib.businesses.values():
                a = m.addAction(b.name or "Unnamed Profile")
                a.setCheckable(True)
                a.setChecked(current is not None and b.id == current.id)
                a.triggered.connect(lambda _c=False, bid=b.id: self.use_business(bid))
            m.addSeparator()
        m.addAction(
            theme.menu_icon("edit"), "Edit Profile…", lambda: self.edit_business(not self.lib.businesses)
        )
        m.addAction(theme.menu_icon("plus"), "Add a Profile…", lambda: self.edit_business(True))
        m.addSeparator()
        m.addAction(theme.menu_icon("message"), "Send Feedback…", self.open_feedback)
        m.addAction(theme.menu_icon("arrow-down"), "Check for Updates…", self.check_updates)
        s = m.addAction(theme.menu_icon("cog"), "Settings…", self.open_settings)
        s.setShortcut(QKeySequence.StandardKey.Preferences)  # shown for reference; the menu bar's runs it
        s.setShortcutVisibleInContextMenu(True)
        at = card.mapToGlobal(QPoint(0, 0))
        m.exec(QPoint(at.x(), at.y() - m.sizeHint().height() - tokens.MENU_GAP))
        self.sidebar.show_who()

    # ------------------------------------------------------------------ Edit
    def _text_widget(self):
        """The text box you're typing in, if any (it keeps its own undo, cut, copy and paste)."""
        w = QApplication.focusWidget()
        return w if isinstance(w, (QLineEdit, QPlainTextEdit, QTextEdit)) else None

    def _text_do(self, what: str) -> None:
        w = self._text_widget()
        if w is not None and not (what in ("cut", "paste") and w.isReadOnly()):
            getattr(w, what)()

    def _text_can_undo(self, redo: bool = False) -> bool:
        w = self._text_widget()
        if isinstance(w, QLineEdit):
            return w.isRedoAvailable() if redo else w.isUndoAvailable()
        if w is not None:
            doc = w.document()
            return doc.isRedoAvailable() if redo else doc.isUndoAvailable()
        return False

    def undo(self) -> None:
        """⌘Z: in a text box, its typing; otherwise the last change to your invoices, clients or profiles."""
        if self._text_can_undo():
            self._text_do("undo")
            return
        self.flush()
        self._fresh = None
        what = self.history.undo() if self.history is not None else None
        if what is None:
            self.toast("Nothing to undo.")
            return
        self._after_history()
        self.toast(f"Undid the last change to {what}.")

    def redo(self) -> None:
        if self._text_can_undo(redo=True):
            self._text_do("redo")
            return
        self.flush()
        what = self.history.redo() if self.history is not None else None
        if what is None:
            self.toast("Nothing to redo.")
            return
        self._after_history()
        self.toast(f"Redid the change to {what}.")

    def _edit_menu_state(self) -> None:
        h = self.history
        self.act_undo.setEnabled(self._text_can_undo() or (h is not None and h.can_undo()))
        self.act_redo.setEnabled(self._text_can_undo(redo=True) or (h is not None and h.can_redo()))

    def _after_history(self) -> None:
        """Undo/redo put new copies of everything in the library: open the invoice again in the panel."""
        cur = self.panel.inv
        self.panel.inv = None
        if cur is not None and self.dock.opened:
            again = self.lib.invoices.get(cur.id)
            if again is not None:
                self.panel.load(again)
            else:
                self.dock.set_open(False)
        self.sidebar.show_who()
        self.refresh()

    def copy(self) -> None:
        """⌘C: text you've selected, or the invoices you've picked as a plain list (number, client, amount)."""
        if self._text_widget() is not None:
            self._text_do("copy")
            return
        lines = []
        for i in self.table.chosen_ids():
            inv = self.lib.invoices.get(i)
            if inv is not None:
                b = self.lib.businesses.get(inv.business_id)
                total = money.fmt(billing.totals(inv).total, (b.currency if b else "$") or "$")
                lines.append("\t".join([inv.number, inv.client.name, total]))
        if lines:
            QApplication.clipboard().setText("\n".join(lines))
            self.toast(f"Copied {len(lines)} invoice{'s' if len(lines) != 1 else ''}.")

    def select_all(self) -> None:
        if self._text_widget() is not None:
            self._text_do("selectAll")
        else:
            self.table.setFocus()
            self.table.select_showing()

    def delete_selected(self) -> None:
        """⌘⌫: delete what's picked (after asking)."""
        ids = self.table.chosen_ids() or ([self.panel.inv.id] if self.panel.inv is not None else [])
        if ids:
            self.delete_invoices(ids)

    def toggle_zoom(self) -> None:
        """Window › Zoom: fill the screen, or back to the smallest size (like double-clicking the title bar)."""
        from cobro.ui.components import titlebar

        titlebar.toggle_size(self)

    def show_shortcuts(self) -> None:
        self.open_settings("shortcuts")

    def _focus_search(self) -> None:
        self.search.setFocus()
        self.search.selectAll()
