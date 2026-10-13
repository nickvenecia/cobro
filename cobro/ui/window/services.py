"""Settings, your account, feedback, updates, and light or dark.

A part of MainWindow (see main_window.py); it uses the window's widgets and the library."""

from __future__ import annotations

import time

from cobro import __version__
from cobro.core import update
from cobro.ui.style import theme, tokens


class ServicesMixin:
    def open_settings(self, pane: str = "general", **kw) -> None:
        """Settings, at a section: general, profiles, ai, account, shortcuts, data."""
        from cobro.ui.dialogs.settings import SettingsDialog

        self.flush()
        SettingsDialog(self.lib, self, pane, **kw).exec()
        self.lib.save_settings()
        self.after_settings()
        self.sidebar.show_who()

    def after_settings(self) -> None:
        """Settings closed: anything it changed shows."""
        self._ai_state()

    def open_account(self) -> None:
        """Sign in or out, in Settings › Account."""
        self.open_settings("account")

    def open_feedback(self) -> None:
        from cobro.ui.dialogs.feedback import FeedbackDialog

        d = FeedbackDialog(self)
        if d.exec():
            self.toast(
                "Thanks! Sent."
                if d.sent_now
                else "Thanks! It's saved and goes out once sending is switched on."
            )

    def open_data_folder(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        from cobro.core.paths import data_dir

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir())))

    # ------------------------------------------------------------------ updates
    def _auto_check_updates(self) -> None:
        if not self.lib.settings.get("auto_update", True) or update.install_kind() == "source":
            return
        self.check_updates(quiet=True)  # every time Cobro opens

    def check_updates(self, quiet: bool = False) -> None:
        from cobro.ui.dialogs.update import CheckThread

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
            self.sidebar.btn_update.setText(f"Update to {rel.version}")
            self.sidebar.btn_update.show()
            if quiet:
                self._offer_update()  # found on its own: say so right away (Later closes it, like any window)
            else:
                self.show_update()
        elif not quiet:
            self.toast(f"You have the newest Cobro ({__version__}).")

    def _offer_update(self) -> None:
        """Show the update window once Cobro is free: never on top of another window or an open menu."""
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        busy = QApplication.activeModalWidget() is not None or QApplication.activePopupWidget() is not None
        if busy or not self.isVisible():
            QTimer.singleShot(tokens.UPDATE_WAIT_MS, self._offer_update)
            return
        self.show_update()

    def show_update(self) -> None:
        if self._release is None:
            return
        from cobro.ui.dialogs.update import UpdateDialog, restart_into

        d = UpdateDialog(self._release, parent=self)
        if d.exec() == UpdateDialog.DialogCode.Accepted and d.plan is not None:
            self.shutdown()
            restart_into(d.plan)

    # ------------------------------------------------------------------ light, dark, accent
    def set_look(self, appearance: str) -> None:
        """Light, Dark, or Match the System."""
        from PySide6.QtWidgets import QApplication

        from cobro.app import set_appearance

        self.lib.settings["appearance"] = appearance
        set_appearance(QApplication.instance(), appearance)

    def set_accent(self, key: str) -> None:
        """The accent color ("" or Cobro's own turquoise: the default)."""
        from PySide6.QtWidgets import QApplication

        from cobro.app import set_appearance

        key = "" if key == tokens.APP_ACCENT or key not in tokens.ACCENTS else key
        self.lib.settings["accent"] = key
        self.lib.save_settings()
        app = QApplication.instance()
        set_appearance(app, getattr(app, "_appearance", "system"), key)

    def look_changed(self) -> None:
        """The colors changed: redraw what holds its own."""
        from PySide6.QtWidgets import QApplication

        current = getattr(QApplication.instance(), "_appearance", "system")
        for k, a in getattr(self, "look_actions", {}).items():
            a.setChecked(k == current)
        self.sidebar.word.setText(theme.wordmark())
        self.sidebar.recolor()
        self.assistant.recolor()
        if self.titlebar is not None:
            self.titlebar.word.setText(theme.wordmark())
        self.refresh()
        self.redraw()
