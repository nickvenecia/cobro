"""App entry point: fonts, light/dark stylesheet, rounded popups, one window at a time, and --smoke-test."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QAbstractSlider,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QMenu,
    QScrollBar,
    QWidget,
)

from cobro import APP_NAME, __version__
from cobro.core.log import get_logger, setup_logging
from cobro.core.paths import ASSETS, data_dir, log_dir, use_data_dir
from cobro.ui.components.widgets import ComboItemDelegate
from cobro.ui.style import theme, tokens

log = get_logger(__name__)


def _server_name() -> str:
    import getpass

    try:
        user = getpass.getuser()
    except Exception:
        user = "user"
    return f"cobro-{user}"


def _wake_running() -> bool:
    """If Cobro is already open, bring its window forward and return True (one window, one set of files)."""
    from PySide6.QtNetwork import QLocalSocket

    sock = QLocalSocket()
    sock.connectToServer(_server_name())
    if not sock.waitForConnected(1500):
        return False
    sock.write(b"show\n")
    sock.flush()
    sock.waitForBytesWritten(1500)
    sock.disconnectFromServer()
    return True


def _listen(window) -> object:
    from PySide6.QtNetwork import QLocalServer

    name = _server_name()
    QLocalServer.removeServer(name)  # clear a stale socket from a crash
    server = QLocalServer(window)
    server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)  # only this user's account
    if not server.listen(name):
        return None

    def on_conn() -> None:
        sock = server.nextPendingConnection()

        def read() -> None:
            sock.readAll()  # the message is always "show"; anything else is ignored
            if window.isMinimized():
                window.showNormal()
            window.raise_()
            window.activateWindow()
            sock.disconnectFromServer()

        sock.readyRead.connect(read)
        sock.disconnected.connect(sock.deleteLater)

    server.newConnection.connect(on_conn)
    return server


class _RoundPopups(QObject):
    """Qt gives menus and dropdown lists square windows; make them see-through so the
    stylesheet's rounded corners are what you actually see. Also: scrolling never changes a value
    (dropdowns, dates and sliders pass the wheel on to the panel, which scrolls instead)."""

    @staticmethod
    def _see_through(win: QWidget) -> None:
        if not win.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground):
            win.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
            win.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)
            win.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def eventFilter(self, obj, ev):
        wheel_on_control = isinstance(obj, (QComboBox, QAbstractSlider, QAbstractSpinBox)) and not isinstance(
            obj, QScrollBar
        )
        if ev.type() == QEvent.Type.Wheel and wheel_on_control:
            area = obj.parent()
            while area is not None and not isinstance(area, QAbstractScrollArea):
                area = area.parent()
            if area is not None:
                QApplication.sendEvent(area.verticalScrollBar(), ev)
            return True
        if ev.type() == QEvent.Type.Polish and isinstance(obj, QWidget):
            if (isinstance(obj, QMenu) and obj.isWindow()) or obj.inherits("QTipLabel"):
                self._see_through(obj)
            elif isinstance(obj, QComboBox):
                if not isinstance(obj.itemDelegate(), ComboItemDelegate):
                    obj.setItemDelegate(ComboItemDelegate(obj))
                container = obj.view().window()
                if container is not obj.window():
                    self._see_through(container)
                    container.setStyleSheet(
                        "QComboBoxPrivateContainer { background: transparent; border: none; }"
                    )
        return False


_crash_file = None


def _log_uncaught() -> None:
    import threading

    previous = sys.excepthook

    def hook(kind, value, tb):
        log.error("unexpected error", exc_info=(kind, value, tb))
        if previous is not None:
            previous(kind, value, tb)

    sys.excepthook = hook
    threading.excepthook = lambda a: log.error(
        "unexpected error in %s", a.thread.name if a.thread else "a thread",
        exc_info=(a.exc_type, a.exc_value, a.exc_traceback),
    )  # fmt: skip


def _crash_log() -> None:
    global _crash_file
    import faulthandler

    try:
        log_dir().mkdir(parents=True, exist_ok=True)
        _crash_file = open(log_dir() / "crash.log", "a", encoding="utf-8")  # noqa: SIM115 — open for the app's life
        faulthandler.enable(_crash_file, all_threads=True)
    except OSError:
        log.debug("no crash log", exc_info=True)


def system_is_dark(app: QApplication) -> bool:
    """The computer's Light / Dark setting. When it can't tell (some Linux desktops), Cobro stays dark."""
    hints = app.styleHints()
    return not (hasattr(hints, "colorScheme") and hints.colorScheme() == Qt.ColorScheme.Light)


def apply_scheme(app: QApplication, dark: bool | None = None) -> None:
    """Light or dark: as the computer is set, or as asked (`dark`, for screenshots and tests).
    Everything on screen repaints in the new colors; the system's own title bars follow by themselves."""
    tokens.use(system_is_dark(app) if dark is None else dark)
    app.setStyleSheet(theme.stylesheet(data_dir() / "ui"))


def setup_app(app: QApplication) -> None:
    """Fonts, stylesheet and look (also used by the tests and screenshots)."""
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName("Cobro")
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion")
    icon_path = ASSETS / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    family = theme.load_fonts()
    f = QFont(family or app.font().family())
    f.setPointSizeF(13 if sys.platform == "darwin" else 10)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    app.setFont(f)
    apply_scheme(app)
    hints = app.styleHints()
    if hasattr(hints, "colorSchemeChanged"):  # the computer switched (by hand, or on its own at sunset)
        hints.colorSchemeChanged.connect(lambda _scheme: apply_scheme(app))
    app._round = _RoundPopups(app)
    app.installEventFilter(app._round)


def _smoke(app: QApplication) -> int:
    """Used by the build pipeline: open the window on a throwaway data folder, add a business and an
    invoice, save it as a PDF, check the file, quit."""
    from cobro.core import sample
    from cobro.core.store import Library
    from cobro.doc import export
    from cobro.ui.window.main_window import MainWindow

    tmp = Path(tempfile.mkdtemp(prefix="cobro-smoke-"))
    use_data_dir(tmp)
    lib = Library(tmp).load()
    b = lib.add_business(sample.business())
    inv = lib.new_invoice(b)
    inv.client.name = "Smoke Test Client"
    inv.items[0].description, inv.items[0].rate = "Production", "1500"
    lib.save_invoice(inv)
    w = MainWindow(lib)
    w.show()
    out = tmp / "smoke.pdf"
    export.to_pdf(w.pages(), out)
    ok = out.exists() and out.stat().st_size > 1000 and out.read_bytes().startswith(b"%PDF")
    print(
        f"smoke: Cobro {__version__}, PDF {'ok' if ok else 'MISSING'} ({out.stat().st_size if out.exists() else 0} bytes)",
        flush=True,
    )
    QTimer.singleShot(1200, app.quit)
    code = app.exec()
    return code if ok else 3


def main() -> int:
    if sys.platform == "win32":
        try:  # own taskbar icon instead of python's
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Cobro.Cobro")
        except Exception:
            log.debug("couldn't set the Windows app id", exc_info=True)
    smoke = "--smoke-test" in sys.argv
    if smoke:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    setup_logging()
    log.info("Cobro %s starting (%s)", __version__, sys.platform)
    _crash_log()
    _log_uncaught()
    app = QApplication(sys.argv)
    if not smoke and _wake_running():
        return 0  # Cobro is already open: it came to the front
    setup_app(app)
    if smoke:
        return _smoke(app)

    from cobro.ui.window.main_window import MainWindow

    w = MainWindow()
    app.aboutToQuit.connect(w.shutdown)
    app._server = _listen(w)
    w.show()
    w.raise_()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
