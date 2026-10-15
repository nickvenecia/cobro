"""The window end to end, offscreen: the sidebar places, the table, editing on the right, the invoice's own
window, undo, filters, Settings, light and dark."""

from __future__ import annotations

import os
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt, QThread, QTimer
from PySide6.QtGui import QContextMenuEvent, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from saldo.core import dates, sample
from saldo.core.model import Client, LineItem, new_id
from saldo.core.store import Library


@pytest.fixture
def win(qapp, data_folder):
    from saldo.ui.window.main_window import MainWindow

    w = MainWindow(sample.fill(Library(data_folder).load()))
    w._restored = True
    w.show()
    yield w
    w.close()


def pick(box, key) -> None:
    """Choose an item in a dropdown the way a click does."""
    i = box.findData(key)
    box.setCurrentIndex(i)
    box.activated.emit(i)


def wheel(widget) -> None:
    pos = QPointF(widget.width() / 2, widget.height() / 2)
    ev = QWheelEvent(
        pos,
        widget.mapToGlobal(pos),
        QPoint(0, 0),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    QApplication.sendEvent(widget, ev)


def roll(widget) -> None:
    """The wheel as a mouse delivers it: to what's under the pointer, then up through what holds it until
    something takes it (wheel() stops at the widget it's given)."""
    at = widget.mapToGlobal(QPointF(widget.width() / 2, widget.height() / 2))
    w = widget
    while w is not None:
        ev = QWheelEvent(
            w.mapFromGlobal(at),
            at,
            QPoint(0, 0),
            QPoint(0, -120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        if (QApplication.sendEvent(w, ev) and ev.isAccepted()) or w.isWindow():
            return
        w = w.parentWidget()


def showing(w) -> list[str]:
    """The invoice numbers you can see in the table, top to bottom."""
    return [w.lib.invoices[r.data(0, Qt.ItemDataRole.UserRole)].number for r in w.table.showing_rows()]


def row_of(w, inv_id: str):
    return next(r for r in w.table.rows() if r.data(0, Qt.ItemDataRole.UserRole) == inv_id)


def when_open(kind, do) -> None:
    """`do(window)` once a window of this kind shows (it may open from inside a click and wait there)."""
    tries = [500]

    def look() -> None:
        shown = [w for w in QApplication.topLevelWidgets() if isinstance(w, kind) and w.isVisible()]
        if shown:
            do(shown[0])
        elif tries[0]:
            tries[0] -= 1
            QTimer.singleShot(10, look)

    QTimer.singleShot(0, look)


def wait_for(done, ms: int = 5000) -> None:
    for _ in range(ms // 10):
        if done():
            return
        QTest.qWait(10)
    raise AssertionError("never happened")


@contextmanager
def still_there_after(widget: QWidget):
    """A click on `widget` may open a window or a menu; anything that window throws away while it's open is
    gone before the click is over. If that's `widget` itself, Saldo crashes (on a Mac, at once). Fails if it
    happens during the `with`."""
    start = QThread.currentThread().loopLevel()
    thrown = []
    original = QWidget.deleteLater

    def delete_later(w: QWidget) -> None:
        if QThread.currentThread().loopLevel() > start and (w is widget or w.isAncestorOf(widget)):
            thrown.append(type(widget).__name__)
        original(w)

    QWidget.deleteLater = delete_later
    try:
        yield
    finally:
        QWidget.deleteLater = original
    assert not thrown, f"the {thrown[0]} was thrown away in the middle of its own click"


def test_first_launch_asks_for_your_profile(qapp, data_folder):
    from saldo.ui.window.main_window import MainWindow

    w = MainWindow(Library(data_folder).load())
    assert w.pages.currentWidget() is w.empty
    assert w.empty.titles() == ["Add Your Profile…"]
    assert not w.search.isVisibleTo(w) and not w.view_menu.isVisibleTo(w)  # nothing to search yet
    assert not w.dock.opened and w.panel.inv is None
    w.shutdown()


def test_the_mac_title_bar_never_fits_a_window_that_is_gone(qapp, data_folder, monkeypatch):
    """The Mac's title bar fits itself just after the window shows. A window thrown away before then is left
    alone: reaching into it broke every test after it on the Mac."""
    from PySide6.QtCore import QCoreApplication, QEvent

    from saldo.ui.components import titlebar
    from saldo.ui.window.main_window import MainWindow

    monkeypatch.setattr(titlebar, "supported", lambda: True)  # the Mac's bar, on any computer
    fits = []
    monkeypatch.setattr(titlebar.TitleBar, "fit", lambda bar: fits.append(bar))
    w = MainWindow(Library(data_folder).load())
    w._restored = True
    w.show()
    wait_for(lambda: fits)  # a window that stays fits its bar
    gone = MainWindow(Library(data_folder).load())
    gone._restored = True
    gone.show()
    gone.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QTest.qWait(20)
    assert len(fits) == 1
    w.shutdown()


def test_adding_your_first_profile_from_its_tile(qapp, data_folder):
    """Add Your Profile… opens Settings; saving there swaps the tile for New Invoice. That used to crash."""
    from saldo.ui.dialogs.settings import SettingsDialog
    from saldo.ui.window.main_window import MainWindow

    w = MainWindow(Library(data_folder).load())
    w._restored = True
    w.show()
    tile = w.empty.tiles[0]

    def add(settings) -> None:
        settings.profile_editor.name.setText("Juniper Lane Films")
        settings.profile_editor.save.click()
        settings.close()

    when_open(SettingsDialog, add)
    with still_there_after(tile):
        QTest.mouseClick(tile, Qt.MouseButton.LeftButton)
    wait_for(lambda: w.panel.inv is not None)
    assert [b.name for b in Library(data_folder).load().businesses.values()] == ["Juniper Lane Films"]
    assert w.empty.titles() == ["New Invoice"] and w.dock.opened  # and the first invoice is open
    w.shutdown()


def test_deleting_a_client_from_their_row_in_the_sidebar(win, monkeypatch, data_folder):
    """Right-click › Delete Client… takes away the very row that was right-clicked. That used to crash."""
    from PySide6.QtWidgets import QMenu

    from saldo.ui.window import editing

    monkeypatch.setattr(editing, "confirm", lambda *a, **k: True)
    mesa = win.lib.find_client("Mesa Coffee Co.")
    row = win.sidebar.rows[f"client:{mesa.id}"]

    def delete(menu) -> None:
        next(a for a in menu.actions() if a.text() == "Delete Client…").trigger()
        menu.close()

    when_open(QMenu, delete)
    at = row.rect().center()
    with still_there_after(row):
        QApplication.sendEvent(
            row, QContextMenuEvent(QContextMenuEvent.Reason.Mouse, at, row.mapToGlobal(at))
        )
    wait_for(lambda: mesa.id not in win.lib.clients)
    assert mesa.id not in Library(data_folder).load().clients
    assert f"client:{mesa.id}" not in win.sidebar.rows


def test_sidebar_places_and_counts(win):
    from saldo.core import document

    counts = {k: r.count.text() for k, r in win.sidebar.rows.items()}
    assert counts["all"] == "4" and counts["drafts"] == "1" and counts["paid"] == "1"
    assert counts["unpaid"] == "2"  # one sent, one overdue
    for key, want in (("drafts", {"draft"}), ("unpaid", {"sent", "overdue"}), ("paid", {"paid"})):
        win.go(key)
        assert win.view_key == key and win.sidebar.rows[key].property("selected")
        ids = [r.data(0, Qt.ItemDataRole.UserRole) for r in win.table.showing_rows()]
        assert ids and {document.status_of(win.lib.invoices[i]) for i in ids} == want
    win.go("all")
    assert len(showing(win)) == 4 and not win.dock.opened  # nothing picked: no panel


def test_open_edit_and_save(win, data_folder):
    lib = win.lib
    client = lib.save_client(Client(name="Brand New Co", contact="Sam"))
    win.new_invoice()
    inv = win.panel.inv
    assert win.dock.opened and inv is not None and inv.number.startswith("JLF-")
    assert win.panel.client.currentIndex() == -1  # "Choose a Client"
    assert not win.panel.edit_client.isVisibleTo(win.panel)
    pick(win.panel.client, client.id)
    assert inv.client.name == "Brand New Co" and inv.client.contact == "Sam"
    assert win.panel.edit_client.isVisibleTo(win.panel)
    ed = win.panel.items[0]
    ed.desc.textEdited.emit("Production")
    ed.rate.textEdited.emit("1500")
    assert ed.amount.text() == "$1,500.00" and ed.title.full_text() == "Production"
    win.flush()
    win.refresh()
    again = Library(data_folder).load().invoices[inv.id]
    assert again.client.name == "Brand New Co" and again.items[0].rate == "1500"
    from saldo.ui.window.tables import COL

    assert row_of(win, inv.id).text(COL["total"]) == "$1,500.00"
    win.deselect()  # Esc
    assert not win.dock.opened and inv.id in win.lib.invoices  # filled in: kept


def test_a_new_invoice_left_blank_goes_away(win, data_folder):
    n = len(win.lib.invoices)
    win.new_invoice()
    assert len(win.lib.invoices) == n + 1
    steps = len(win.history.undos)
    win.deselect()  # Esc
    assert len(win.lib.invoices) == n and len(Library(data_folder).load().invoices) == n
    assert len(win.history.undos) == steps - 1  # and it left no undo step


def test_toasts(win):
    import time

    t = win.toaster
    win.toast("Copied 3 invoices.", "done")
    assert t.isVisible() and (t.text, t.tone) == ("Copied 3 invoices.", "done")
    pill = t._pill.translated(t.pos().x(), t.pos().y())
    area = win._toast_area()  # over the list, above the totals
    assert area.contains(pill.toRect()) and pill.center().x() == pytest.approx(area.center().x(), abs=2)
    win.toast("Something odd.", "sparkly")  # an unknown tone is plain news
    assert t.tone == ""

    def wait(ms):
        stop = time.monotonic() + ms / 1000
        while time.monotonic() < stop:
            QApplication.processEvents()
            time.sleep(0.01)

    t.dismiss()
    win.toast("Saved.", "done")  # a new one while the last fades away stays up
    wait(500)
    assert t.isVisible() and t.text == "Saved."
    t.dismiss()
    wait(500)
    assert not t.isVisible()


def test_the_invoice_window_and_its_dark_page(win, monkeypatch):
    from saldo.ui.dialogs.preview import PageDialog

    seen = []

    def run(d):
        panel = d.panel
        assert panel.view.pages and panel.btn_pdf.isEnabled()
        panel.btn_dark.click()
        seen.append(panel.view.pages[0].paper)
        return 0

    monkeypatch.setattr(PageDialog, "exec", run)
    first = win.lib.ordered()[0]
    win.show_page(first.id)
    assert seen and seen[0] != "#FFFFFF"  # the Dark Page, in the window only
    assert win.lib.settings["dark_preview"] is True
    win.page_inv = first.id
    assert win.page_list()[0].paper == "#FFFFFF"  # what gets saved and printed stays white
    assert win.page is None  # closed again


def test_paid_shows_its_date(win):
    win.new_invoice()
    win.panel.status.setCurrentIndex(win.panel.status.findData("paid"))
    inv = win.panel.inv
    assert inv.status == "paid" and inv.paid_on and inv.sent_on
    assert win.panel.paid_sec.isVisibleTo(win.panel)


def test_an_unsaved_client_still_shows_and_typing_never_saves_clients(qapp, data_folder):
    from saldo.ui.panels.invoice import THIS_CLIENT
    from saldo.ui.window.main_window import MainWindow

    lib = Library(data_folder)
    b = lib.add_business(sample.business())
    inv = lib.new_invoice(b)
    inv.client = Client(name="Old Client From 1.0")
    lib.save_invoice(inv)
    w = MainWindow(lib.load())
    w.open(inv.id)
    assert w.panel.client.currentData() == THIS_CLIENT
    assert w.panel.client.currentText() == "Old Client From 1.0"
    w.shutdown()
    assert Library(data_folder).load().clients == {}  # clients are only saved on purpose


def test_line_items_fold_one_at_a_time_and_move(win):
    inv = win.lib.ordered()[0]
    inv.items = [LineItem("Production", "", "1", "1500"), LineItem("Edit", "", "2", "500")]
    win.open(inv.id)
    d = win.panel
    first, second = d.items
    assert not first.is_open() and not second.is_open()  # a finished list starts folded
    first.head.clicked.emit()
    assert first.is_open() and not second.is_open()
    second.head.clicked.emit()
    assert second.is_open() and not first.is_open()
    assert not first.act_up.isEnabled() and first.act_down.isEnabled()
    d._move_item(first, 1)
    assert [i.description for i in inv.items] == ["Edit", "Production"]
    assert d.items == [second, first] and first.act_up.isEnabled()
    d._duplicate_item(second)
    assert [i.description for i in inv.items] == ["Edit", "Edit", "Production"]
    assert inv.items[0] is not inv.items[1]
    d._remove_item(first)
    assert [i.description for i in inv.items] == ["Edit", "Edit"]
    d.add_item.click()
    assert d.items[-1].is_open() and sum(ed.is_open() for ed in d.items) == 1
    assert "2 items" in d.groups["items"]._summary


def test_scrolling_never_changes_a_date_or_dropdown(win):
    win.open(win.lib.ordered()[0].id)
    issued, terms = win.panel.issued.date(), win.panel.terms_days.currentData()
    wheel(win.panel.issued)
    wheel(win.panel.terms_days)
    assert win.panel.issued.date() == issued and win.panel.terms_days.currentData() == terms


def test_the_wheel_scrolls_the_panel_past_a_text_box(win):
    """Long terms (or a line item's details) used to catch the wheel and scroll inside their box, and the
    panel stopped there. A box you're typing in still scrolls what's in it."""
    inv = next(i for i in win.lib.invoices.values() if i.status == "draft")
    inv.terms = "\n".join(
        f"Term {n}: payment is due within thirty days of the invoice date." for n in range(12)
    )
    win.open(inv.id)
    p = win.panel
    p.groups["payment"].set_open(True)
    bar, box = p.scroll.verticalScrollBar(), p.terms
    wait_for(lambda: bar.maximum() > 0 and box.verticalScrollBar().maximum() > 0)
    bar.setValue(0)
    p.scroll.ensureWidgetVisible(box)
    at = bar.value()
    assert at < bar.maximum()
    roll(box.viewport())
    assert bar.value() > at and box.verticalScrollBar().value() == 0
    win.activateWindow()
    QTest.qWaitForWindowActive(win)
    box.setFocus()
    if box.hasFocus():  # (only once the window is active)
        at = bar.value()
        roll(box.viewport())
        assert box.verticalScrollBar().value() > 0 and bar.value() == at


def test_another_invoice_opens_at_its_top(win):
    """The panel used to keep the last invoice's place, so the next one opened partway down."""
    a, b = win.lib.ordered()[:2]
    win.open(a.id)
    p = win.panel
    for g in p.groups.values():
        g.set_open(True)
    bar = p.scroll.verticalScrollBar()
    wait_for(lambda: bar.maximum() > 0)
    bar.setValue(bar.maximum())
    p.load(a)  # the same invoice again (undo, a client picked under Bill To…): it stays where you are
    assert bar.value() == bar.maximum() > 0
    win.open(b.id)
    assert bar.value() == 0


def test_the_table_stays_where_you_left_it(win):
    """Every edit refills the table a moment later; it used to jump back to the top each time."""
    first = win.lib.ordered()[0]
    for n in range(40):
        win.lib.save_invoice(replace(first, id=new_id(), number=f"JLF-2026-{100 + n}"))
    win.refresh()
    bar = win.table.verticalScrollBar()
    wait_for(lambda: bar.maximum() > 0)
    bar.setValue(bar.maximum() // 2)
    at = bar.value()
    win.refresh()
    assert bar.value() == at
    win.open(first.id)  # picked, then scrolled away from to look at the others while you edit it
    bar.setValue(bar.maximum())
    at = bar.value()
    win.panel.project.setText("Brand film")
    win.panel.project.textEdited.emit("Brand film")
    win._table_timer.timeout.emit()  # the refill after an edit
    assert bar.value() == at and win.table.current_id() == first.id


def test_dates_are_picked_in_a_calendar_never_typed(win, data_folder):
    from PySide6.QtCore import QDate

    p = win.panel
    win.open(win.lib.ordered()[0].id)
    inv = p.inv
    issued = p.issued
    before = inv.issued
    QTest.keyClicks(issued, "2027")  # typing does nothing
    assert inv.issued == before and issued.words.full_text() == dates.fmt_day(dates.parse(before))
    QTest.mouseClick(issued, Qt.MouseButton.LeftButton)  # a click anywhere on it opens the calendar
    cal = issued.popup
    assert cal is not None and cal.isVisible() and cal.cal.selectedDate() == issued.date()
    cal.cal.clicked.emit(QDate(2026, 10, 2))  # a day, picked
    assert inv.issued == "2026-10-02" and issued.words.full_text() == "Fri, Oct 2, 2026"
    wait_for(lambda: issued.popup is None)  # and the calendar is gone
    QTest.keyClick(issued, Qt.Key.Key_Space)  # the keyboard opens it too; Esc puts it away unchanged
    QTest.keyClick(issued.popup.cal, Qt.Key.Key_Escape)
    wait_for(lambda: issued.popup is None)
    assert inv.issued == "2026-10-02"


def test_work_dates_are_two_days_picked_in_a_calendar(win, data_folder):
    from PySide6.QtCore import QDate

    p = win.panel
    win.open(win.lib.ordered()[0].id)
    inv = p.inv
    inv.work_dates = "Sep 26–27, 2026"
    p.load(inv)
    assert p.show_work.isChecked() and not p.work_typed.isVisibleTo(p)
    assert (p.work_first.date(), p.work_last.date()) == (QDate(2026, 9, 26), QDate(2026, 9, 27))
    p.work_last.setDate(QDate(2026, 10, 2))
    assert inv.work_dates == "Sep 26 – Oct 2, 2026"
    p.work_first.setDate(QDate(2026, 10, 5))  # after the last day: the last day follows
    assert inv.work_dates == "Oct 5, 2026" and p.work_last.date() == QDate(2026, 10, 5)
    p.show_work.setChecked(False)
    assert inv.work_dates == "" and not p.work_days.isVisibleTo(p)
    inv.work_dates = "Sep 26, 27 and Oct 2"  # typed in an older Saldo: shown and printed as it is
    p.load(inv)
    assert p.work_typed.isVisibleTo(p) and p.work_typed.full_text() == "Sep 26, 27 and Oct 2"
    assert inv.work_dates == "Sep 26, 27 and Oct 2"
    p.work_first.setDate(QDate(2026, 9, 26))  # until you pick days
    assert not p.work_typed.isVisibleTo(p) and inv.work_dates.startswith("Sep 26")
    win.flush()
    assert Library(data_folder).load().invoices[inv.id].work_dates == inv.work_dates


def test_every_group_folds_and_is_remembered(qapp, data_folder):
    from saldo.ui.window.main_window import MainWindow

    w = MainWindow(sample.fill(Library(data_folder).load()))
    w.open(w.lib.ordered()[0].id)
    who = w.panel.groups["who"]
    assert who.is_open()
    who.header.click()
    assert not who.is_open() and "Juniper Lane Films" in who._summary
    w.shutdown()
    w = MainWindow(Library(data_folder).load())
    assert not w.panel.groups["who"].is_open() and w.panel.groups["invoice"].is_open()
    w.shutdown()


def test_picking_a_client_gives_a_draft_its_number_when_counting_per_client(qapp, data_folder):
    from saldo.ui.window.main_window import MainWindow

    lib = Library(data_folder)
    b = sample.business()
    b.number_style = "client"
    lib.add_business(b)
    north = lib.save_client(Client(name="Northwind Media"))
    mesa = lib.save_client(Client(name="Mesa Coffee", code="MESA"))
    w = MainWindow(lib.load())
    w.new_invoice()
    inv = w.panel.inv
    year = inv.issued[:4]
    pick(w.panel.client, north.id)
    assert inv.number == f"JLF-NRTH-{year}-001" == w.panel.number.text()
    pick(w.panel.client, mesa.id)
    assert inv.number == f"JLF-MESA-{year}-001"
    w.panel.number.setText("JLF-SPECIAL")
    w.panel.number.textEdited.emit("JLF-SPECIAL")
    pick(w.panel.client, north.id)
    assert inv.number == "JLF-SPECIAL"  # a number you typed stays yours
    w.shutdown()


def test_the_profile_editor_saves_a_copy_and_cancel_changes_nothing(qapp, data_folder):
    from saldo.ui.dialogs.profile import ProfileDialog

    b = sample.business()
    d = ProfileDialog(b, can_delete=False)
    d.number_style.setCurrentIndex(d.number_style.findData("client"))
    d._set_logo("logo.png")
    assert b.look.logo == "" and b.number_style == "year"  # nothing changes until Save
    assert d.number_style.currentText().startswith("JLF-ACME-")
    d._save()
    assert d.business.number_style == "client" and d.business.look.logo == "logo.png"
    assert b.look.logo == ""


def test_the_paper_changes_with_the_profile(win, data_folder):
    from saldo.ui.dialogs.profile import ProfileDialog

    b = win.business()
    d = ProfileDialog(b, can_delete=False)
    d.color.setCurrentIndex(d.color.findData("oxblood"))
    d.header.setCurrentIndex(d.header.findData("band"))
    d._save()
    win.profile_saved(d, b)
    assert Library(data_folder).load().businesses[b.id].look.header == "band"
    win.page_inv = win.lib.ordered()[0].id
    assert win.page_list()[0].steps[0].color == "#7A2E2E"  # the band


def test_saving_a_profile_hides_the_old_form_before_throwing_it_away(win, monkeypatch):
    """Save Changes builds the profile form again. The old one was thrown away while it still showed, holding
    the focus of the field you'd typed in; it handed that focus on halfway through being taken apart, and
    Saldo crashed (on a Mac, every time: offscreen windows never hold the focus, so
    test_saving_a_profile_in_a_macs_own_windows saves one in real windows too)."""
    from PySide6.QtWidgets import QDialog

    from saldo.ui.dialogs.settings import SettingsDialog

    showing = []
    original = QWidget.deleteLater

    def delete_later(w) -> None:
        if w.isVisible() and (isinstance(w, QDialog) or w.findChildren(QDialog)):
            showing.append(type(w).__name__)
        original(w)

    monkeypatch.setattr(QWidget, "deleteLater", delete_later)
    s = SettingsDialog(win.lib, win, "profiles")
    s.show()
    for name in ("Juniper Lane", "Juniper Lane Films"):
        s.profile_editor.name.setText(name)
        s.profile_editor.save.click()
    s._add_profile()  # Add a Profile builds it again too
    s.profile_editor.name.setText("Second Profile")
    s.profile_editor.save.click()
    s.close()
    assert not showing, f"a {showing[0]} was thrown away while it showed"
    assert sorted(b.name for b in win.lib.businesses.values()) == ["Juniper Lane Films", "Second Profile"]


@pytest.mark.skipif(sys.platform != "darwin", reason="a Mac's own windows")
@pytest.mark.parametrize("route", ["tile", "settings", "card", "from", "add", "menubar"])
def test_saving_a_profile_in_a_macs_own_windows(route):
    """Saving a profile crashed on a Mac every time, by every route (tests/mac_windows.py lists them), and no
    offscreen test could see it. Each route runs in a Saldo of its own, so a crash fails only that route."""
    drive = Path(__file__).with_name("mac_windows.py")
    env = {**os.environ, "QT_QPA_PLATFORM": "cocoa"}
    r = subprocess.run(
        [sys.executable, str(drive), route], env=env, capture_output=True, text=True, timeout=120
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_new_client_under_bill_to_fills_in_the_invoice(win, monkeypatch):
    from saldo.ui.window import editing

    class Saved:
        DialogCode = editing.ClientDialog.DialogCode
        deleted, client = False, Client(name="Brand New Co")

        def __init__(self, *_a, **_k):
            pass

        def exec(self):
            return self.DialogCode.Accepted

    monkeypatch.setattr(editing, "ClientDialog", Saved)
    draft = next(i for i in win.lib.invoices.values() if i.status == "draft")
    win.open(draft.id)
    win.edit_client(True)  # New Client… under Bill To
    assert draft.client.name == "Brand New Co" and win.lib.find_client("Brand New Co") is not None
    assert "client:" + draft.client.id in win.sidebar.rows  # and it's in the sidebar


def test_all_invoices_folds_its_places_and_remembers(qapp, data_folder):
    from saldo.ui.window.main_window import MainWindow

    lib = sample.fill(Library(data_folder).load())
    w = MainWindow(lib)
    sb = w.sidebar
    for key in ("drafts", "unpaid", "paid"):
        assert sb.rows[key].label.objectName() == "NavSub"  # rows under All Invoices
        assert sb.rows[key].parentWidget() is sb.boxes["all"]
    assert sb.rows["all"].count.text() == "4" and sb.rows["all"].count.property("tone") == ""
    sb.rows["all"].fold_wanted.emit("all")  # its arrow
    assert not sb.boxes["all"].isVisibleTo(sb) and "all" in lib.settings["sidebar_folded"]
    assert sb.rows["all"].count.property("tone") == "overdue"  # folded, it still says something's late
    w.go("unpaid")  # the places still work from the menu (⌘3)
    assert w.view_key == "unpaid"
    w.shutdown()
    again = MainWindow(Library(data_folder).load())
    assert again.sidebar.rows["all"].folded and not again.sidebar.boxes["all"].isVisibleTo(again.sidebar)
    again.shutdown()


def test_clients_their_table_and_their_panel(win, data_folder):
    from PySide6.QtCore import Qt

    lib, sb = win.lib, win.sidebar
    names = [sb.rows[k].label.text() for k in sb.rows if k.startswith("client:")]
    assert names == ["Desert Sun Records", "Mesa Coffee Co.", "Northwind Media"]
    assert sb.rows["clients"].count.text() == "3"
    desert = lib.find_client("Desert Sun Records")
    assert sb.rows[f"client:{desert.id}"].count.text() == "2"  # its invoices
    win.go("clients")
    assert win.pages.currentWidget() is win.client_table and win.title.text() == "All Clients"
    assert not win.view_menu.isVisibleTo(win) and not win.btn_export.isVisibleTo(win)
    rows = list(win.client_table.showing_rows())
    assert [r.text(0) for r in rows] == names  # A to Z
    owed = {r.text(0): r.text(win.client_table.col["owed"]) for r in rows}
    assert owed["Northwind Media"] == ""  # a draft owes nothing yet
    win.search.setText("jordan")  # the contact person
    assert [r.text(0) for r in win.client_table.showing_rows()] == ["Mesa Coffee Co."]
    win.search.clear()

    sb.pick(f"client:{desert.id}")  # its row in the sidebar opens it
    cp = win.client_panel
    assert win.dock.opened and win.inspector.currentWidget() is cp and cp.c.id == desert.id
    assert sb.rows[f"client:{desert.id}"].property("selected")
    assert cp.lines_lay.count() == 2 and cp.sums.isVisibleTo(cp)
    cp.email.textEdited.emit("hello@desertsun.example")
    win.flush()
    assert Library(data_folder).load().clients[desert.id].email == "hello@desertsun.example"
    paid = next(i for i in lib.invoices.values() if i.status == "paid")
    cp.name.textEdited.emit("Mesa Coffee Co.")  # another client's name: not kept
    assert cp.name_hint.isVisibleTo(cp) and not cp.can_save()
    win.flush()
    assert lib.clients[desert.id].name == "Desert Sun Records"
    cp.name.textEdited.emit("Desert Sun Music")
    win.flush()
    assert lib.clients[desert.id].name == "Desert Sun Music"
    assert paid.client.name == "Desert Sun Records"  # paid invoices keep what they said

    line = cp.lines_lay.itemAt(0).widget()  # one of their invoices: opens it in All Invoices
    line.clicked.emit(line.inv_id)
    QApplication.processEvents()
    assert win.view_key == "all" and win.panel.inv.id == line.inv_id
    assert win.inspector.currentWidget() is win.panel
    assert win.table.currentItem().data(0, Qt.ItemDataRole.UserRole) == line.inv_id


def test_a_new_client_is_kept_once_it_has_a_name(win, data_folder):
    lib = win.lib
    n = len(lib.clients)
    win.new_client()  # ⇧⌘N, the sidebar's +, or the round + in All Clients
    cp = win.client_panel
    assert win.on_clients() and win.dock.opened and cp.fresh
    assert cp.save_btn.isVisibleTo(cp) and not cp.save_btn.isEnabled()  # Save Client, once it has a name
    assert not cp.new_inv.isVisibleTo(cp)
    win.deselect()  # left without a name: nothing kept
    assert len(lib.clients) == n
    win.new_client()
    cp.name.textEdited.emit("Sol Studio")
    cp.contact.textEdited.emit("Ana")
    assert cp.save_btn.isEnabled()
    win.flush()  # kept as you type all the same: nothing's lost if you click away
    saved = lib.find_client("Sol Studio")
    assert saved is not None and saved.contact == "Ana" and not cp.fresh
    assert Library(data_folder).load().find_client("Sol Studio") is not None
    assert cp.save_btn.isVisibleTo(cp)  # still making it: Save Client stays until it's clicked
    cp.email.textEdited.emit("ana@sol.example")
    cp.save_btn.click()
    assert Library(data_folder).load().find_client("Sol Studio").email == "ana@sol.example"
    assert not cp.save_btn.isVisibleTo(cp) and cp.new_inv.isVisibleTo(cp) and cp.new_inv.isEnabled()
    assert f"client:{saved.id}" in win.sidebar.rows and win.sidebar.rows[f"client:{saved.id}"].property(
        "selected"
    )
    win.open_client(lib.find_client("Mesa Coffee Co.").id)  # a saved client: New Invoice, never Save Client
    assert not cp.save_btn.isVisibleTo(cp) and cp.new_inv.isVisibleTo(cp)


def test_a_new_invoice_for_a_client_and_deleting_one(win, monkeypatch, data_folder):
    from saldo.ui.window import editing

    lib = win.lib
    mesa = lib.find_client("Mesa Coffee Co.")
    win.open_client(mesa.id)
    n = len(lib.invoices)
    win.new_invoice_for(mesa.id)
    inv = win.panel.inv
    assert inv.client.id == mesa.id and len(lib.invoices) == n + 1
    win.deselect()  # left untouched: it goes, like any new invoice
    assert len(lib.invoices) == n
    monkeypatch.setattr(editing, "confirm", lambda *a, **k: True)
    win.open_client(mesa.id)
    before = {i.id: i.client.name for i in lib.invoices.values()}
    win.delete_client(mesa.id)
    assert mesa.id not in lib.clients and mesa.id not in Library(data_folder).load().clients
    assert {i.id: i.client.name for i in lib.invoices.values()} == before  # every invoice as it was
    assert not win.dock.opened and f"client:{mesa.id}" not in win.sidebar.rows


def test_undo_and_redo(win, monkeypatch, data_folder):
    from saldo.ui.window import editing

    monkeypatch.setattr(editing, "confirm", lambda *a, **k: True)
    lib = win.lib
    victim = lib.ordered()[0]
    win.delete_invoices([victim.id])
    assert victim.id not in lib.invoices
    win.setFocus()
    win.undo()
    assert victim.id in lib.invoices and victim.id in Library(data_folder).load().invoices  # saved back
    win.redo()
    assert victim.id not in lib.invoices and victim.id not in Library(data_folder).load().invoices
    win.undo()
    # an edit with the invoice open, then undo: the panel shows it as it was
    win.open(victim.id)
    inv = win.panel.inv
    old = inv.project
    win.panel.project.setText("Renamed")
    win.panel.project.textEdited.emit("Renamed")
    win.flush()
    win.setFocus()
    win.undo()
    assert lib.invoices[victim.id].project == old and win.panel.inv is lib.invoices[victim.id]
    assert win.panel.project.text() == old


def test_delete_many_after_one_alert(win, monkeypatch):
    from saldo.ui.window import editing

    asked = []
    monkeypatch.setattr(editing, "confirm", lambda _w, title, *_a, **_k: asked.append(title) or True)
    win.table.setFocus()
    win.select_all()
    ids = win.table.chosen_ids()
    assert len(ids) == 4 and win.count.full_text() == "4 selected"
    win.delete_selected()
    assert asked == ["Delete 4 invoices?"] and not win.lib.invoices
    assert win.empty.titles() == ["New Invoice"] and not win.search.isVisibleTo(win)
    win.empty.tiles[0].clicked.emit()  # New Invoice, open on the right
    assert (
        len(win.lib.invoices) == 1 and win.pages.currentWidget() is win.table and win.search.isVisibleTo(win)
    )
    win.deselect()  # left blank, so it goes
    assert not win.lib.invoices and win.pages.currentWidget() is win.empty


def test_search_filter_and_totals(win):
    win.search.setText("mesa")
    (only,) = [r.data(0, Qt.ItemDataRole.UserRole) for r in win.table.showing_rows()]
    assert win.lib.invoices[only].client.name == "Mesa Coffee Co."
    assert win.total_values["overdue"].text() == "$1,500.00"
    win.search.clear()
    f = win.view_menu
    assert f.is_default() and not f.property("active")
    f.filter.show = "paid"
    f.show_state()
    f.changed.emit()
    paid = [r.data(0, Qt.ItemDataRole.UserRole) for r in win.table.showing_rows()]
    assert len(paid) == 1 and win.lib.invoices[paid[0]].status == "paid"
    assert f.property("active") and "Paid" in f.toolTip()
    assert not win.total_labels["overdue"].isVisibleTo(win)  # only what applies
    f.filter.year = "1999"
    f.changed.emit()
    assert win.pages.currentWidget() is win.empty and win.empty.titles() == ["Clear Filters"]
    win.empty.tiles[0].clicked.emit()
    assert f.is_default() and len(showing(win)) == 4
    f.m.aboutToShow.emit()  # the menu builds, with Divide By first
    texts = [a.text() for a in f.m.actions() if a.text()]
    assert texts[:3] == ["Month", "Client", "No Dividers"] and "Clear Filters" in texts


def test_divide_by_client_and_fold_a_band(win):
    from datetime import date

    from saldo.ui.window.tables import HEAD

    root = win.table.invisibleRootItem()
    months = [root.child(i).text(0) for i in range(root.childCount())]
    newest = max(win.lib.invoices.values(), key=lambda i: i.issued)
    assert months[0] == f"{date.fromisoformat(newest.issued):%B %Y}"  # the newest month on top
    f = win.view_menu
    f._pick("divide", "client")
    assert win.lib.settings["divide"] == "client"
    bands = [root.child(i) for i in range(root.childCount()) if root.child(i).data(0, HEAD) is not None]
    assert [b.text(0) for b in bands] == ["Desert Sun Records", "Mesa Coffee Co.", "Northwind Media"]
    win.table.itemClicked.emit(bands[0], 0)  # a click on the band
    assert not bands[0].isExpanded() and len(showing(win)) == 2
    assert win.lib.settings["folded"] == ["client/Desert Sun Records"]  # remembered


def test_settings_window(win, qapp, data_folder):
    from saldo.app import set_appearance
    from saldo.core.store import read_json
    from saldo.ui.dialogs.settings import SettingsDialog
    from saldo.ui.style import tokens

    d = SettingsDialog(win.lib, win)
    try:
        d.look.changed.emit("light")
        assert win.lib.settings["appearance"] == "light" and tokens.SCHEME == "light"
        d.auto.setChecked(False)
        assert win.lib.settings["auto_update"] is False
        assert d.accent.current == tokens.APP_ACCENT
        d.accent._pick("purple")
        assert tokens.ACCENTS["purple"][2] == tokens.ACCENT and tokens.ACCENT in qapp.styleSheet()
        assert read_json(data_folder / "settings.json", {}).get("accent") == "purple"
        d.accent._pick(tokens.APP_ACCENT)
        assert read_json(data_folder / "settings.json", {}).get("accent") == ""
        assert tokens.LIGHT["ACCENT"] == tokens.ACCENT
        for key in ("profiles", "account", "shortcuts", "data"):
            d.show_pane(key)
            assert d.current_pane() == key
    finally:
        d.close()
        set_appearance(qapp, "dark", "")


def test_shortcuts_listed(win):
    from saldo.ui.dialogs.shortcuts import keys_by_menu

    menus = dict(keys_by_menu(win.menuBar()))
    edit = dict(menus["Edit"])
    assert {"Undo", "Redo", "Copy", "Select All", "Find"} <= set(edit)
    assert "New Invoice" in dict(menus["File"])


def test_alert_return_says_yes(win):
    from PySide6.QtCore import QTimer
    from PySide6.QtTest import QTest

    from saldo.ui.dialogs.common import confirm

    QTimer.singleShot(50, lambda: QTest.keyClick(QApplication.activeModalWidget(), Qt.Key.Key_Return))
    assert confirm(win, "Delete it?", "", "Delete") is True
    QTimer.singleShot(50, lambda: QTest.keyClick(QApplication.activeModalWidget(), Qt.Key.Key_Escape))
    assert confirm(win, "Delete it?", "", "Delete") is False


def test_back_up_zips_the_data(tmp_path):
    import zipfile

    from saldo.core.fileutil import zip_folder

    src = tmp_path / "Saldo"
    (src / "invoices").mkdir(parents=True)
    (src / "businesses.json").write_text("{}")
    (src / "invoices" / "a.json").write_text("{}")
    (src / "ui").mkdir()
    (src / "ui" / "x.svg").write_text("<svg/>")
    dest = tmp_path / "backup.zip"
    assert zip_folder(src, dest, skip=("ui",)) == 2
    assert sorted(zipfile.ZipFile(dest).namelist()) == ["Saldo/businesses.json", "Saldo/invoices/a.json"]


def test_light_or_dark_follows_the_computer(qapp, data_folder, monkeypatch):
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QStyleHints

    from saldo.app import set_appearance
    from saldo.ui.style import theme, tokens
    from saldo.ui.window.main_window import MainWindow

    assert set(tokens.LIGHT) == set(tokens.DARK)  # every color has both versions
    lib = Library(data_folder)
    lib.add_business(sample.business())
    w = MainWindow(lib.load())
    plus = theme.icon("plus", theme.TEXT)

    def computer_says(scheme) -> None:
        monkeypatch.setattr(QStyleHints, "colorScheme", lambda _hints: scheme)
        qapp.styleHints().colorSchemeChanged.emit(scheme)

    def ink(icon) -> str:  # the icon's color where it's fully drawn
        img = icon.pixmap(QSize(64, 64), 1.0).toImage()
        return next(
            img.pixelColor(x, y).name()
            for x in range(img.width())
            for y in range(img.height())
            if img.pixelColor(x, y).alpha() == 255
        )

    try:
        set_appearance(qapp, "system")
        computer_says(Qt.ColorScheme.Light)  # e.g. switched in System Settings while Saldo is open
        assert tokens.SCHEME == "light" and tokens.LIGHT["BG"] == tokens.BG
        assert ink(plus) == tokens.LIGHT["TEXT"].lower()  # icons already made follow too
        assert tokens.LIGHT["ACCENT"] in theme.wordmark()
        computer_says(Qt.ColorScheme.Dark)
        assert tokens.SCHEME == "dark" and tokens.DARK["BG"] == tokens.BG
        assert ink(plus) == tokens.DARK["TEXT"].lower()
        computer_says(Qt.ColorScheme.Unknown)  # can't tell: Saldo's dark
        assert tokens.SCHEME == "dark"
        set_appearance(qapp, "light")  # pinned in Settings: the computer no longer decides
        computer_says(Qt.ColorScheme.Dark)
        assert tokens.SCHEME == "light"
    finally:
        set_appearance(qapp, "dark", "")
    w.shutdown()


def test_a_data_folder_from_version_1_opens_and_nothing_in_it_is_lost(qapp, data_folder):
    """Files written by version 1.0 (type styles, no clients file, the old window's settings) open in the new
    window, print, and come back out with everything they held."""
    import json

    from saldo.core.store import write_json
    from saldo.ui.window.main_window import MainWindow

    look = {
        "type_style": "classic",
        "heading_font": "",
        "body_font": "",
        "heading_caps": False,
        "color": "sage",
        "custom_color": "#284B63",
        "header": "band",
        "logo": "",
        "logo_size": "medium",
        "name_with_logo": True,
        "paper": "letter",
    }
    biz = {"id": "b1", "name": "Juniper Lane Films", "prefix": "JLF", "currency": "$", "terms_days": 30}
    biz["look"] = look
    write_json(data_folder / "businesses.json", [biz])
    inv = {
        "id": "i1",
        "business_id": "b1",
        "number": "JLF-2025-007",
        "client": {"name": "Mesa Coffee Co.", "contact": "", "address": "", "email": ""},
        "issued": "2025-11-02",
        "terms_days": 30,
        "items": [{"description": "Edit", "details": "", "qty": "2", "rate": "650"}],
        "status": "sent",
        "sent_on": "2025-11-02",
    }
    write_json(data_folder / "invoices" / "i1.json", inv)
    write_json(data_folder / "settings.json", {"current": "i1", "splitter": "abc", "dark_preview": False})
    before = (data_folder / "invoices" / "i1.json").read_bytes()

    w = MainWindow(Library(data_folder).load())
    w.open("i1")
    assert w.panel.inv.number == "JLF-2025-007" and w.panel.items[0].amount.text() == "$1,300.00"
    w.page_inv = "i1"
    pages = w.page_list()
    assert pages and pages[0].steps[0].color == "#4C6A55"  # its sage band, as before
    w.shutdown()

    assert (data_folder / "invoices" / "i1.json").read_bytes() == before  # opened, not rewritten
    saved = json.loads((data_folder / "businesses.json").read_text(encoding="utf-8"))
    assert saved[0]["look"]["type_style"] == "classic" and saved[0]["look"]["color"] == "sage"
    settings = json.loads((data_folder / "settings.json").read_text(encoding="utf-8"))
    assert settings["splitter"] == "abc"  # settings the new window doesn't use are kept too


def test_only_the_adjustments_an_invoice_has_show(win):
    def on(w) -> bool:  # shown (the group they're in may be folded)
        return not w.isHidden()

    win.new_invoice()
    p = win.panel
    assert not any(on(part) for part in p.parts.values())
    assert all(on(b) for b in p.add_parts.values())  # + Discount, + Deposit, + Sales Tax
    p.add_parts["discount"].click()
    part = p.parts["discount"]
    assert on(part) and on(part.x) and not on(p.add_parts["discount"])
    part.x.click()  # still empty: × takes it off again
    assert not on(part) and on(p.add_parts["discount"])
    p.add_parts["deposit"].click()
    p.deposit.setText("500")
    p.deposit.textEdited.emit("500")
    assert p.inv.deposit == "500" and not on(p.parts["deposit"].x)  # it holds something now
    inv = p.inv
    win.deselect()
    win.open(inv.id)
    assert on(p.parts["deposit"]) and not on(p.parts["discount"])


def test_a_line_items_details_show_once_it_has_some(win):
    win.new_invoice()
    ed = win.panel.items[0]
    assert ed.is_open() and not ed.details.isVisibleTo(ed) and ed.add_details.isVisibleTo(ed)
    ed.add_details.click()
    assert ed.details.isVisibleTo(ed) and not ed.add_details.isVisibleTo(ed)
    filled = next(i for i in win.lib.invoices.values() if i.items and i.items[0].details)
    win.open(filled.id)
    first = win.panel.items[0]
    first.head.clicked.emit()
    assert first.details.isVisibleTo(first) and not first.add_details.isVisibleTo(first)


def test_drag_a_line_item_by_its_grip(win, data_folder):
    from PySide6.QtCore import QPoint

    inv = win.lib.ordered()[0]
    inv.items = [LineItem("Production"), LineItem("Edit"), LineItem("Color")]
    win.open(inv.id)
    p = win.panel
    QApplication.processEvents()
    first, second, third = p.items
    assert all(ed.grip.active for ed in p.items)
    first.head.clicked.emit()  # open: it folds while it travels
    assert first.is_open()

    def drag(ed, to, cancel=False):
        start = ed.grip.mapToGlobal(ed.grip.rect().center())
        ed.grip.pressed.emit(start)
        assert p._lift is not None and not ed.isVisible()  # the drawing stands in while it moves
        for step in range(1, 9):
            ed.grip.moved.emit(start + QPoint(0, round((to - start.y()) * step / 8)))
            p._lift._step()
        ed.grip.released.emit(cancel)
        assert p._lift is None and all(e.isVisible() for e in p.items)

    below = third.mapToGlobal(third.rect().bottomLeft()).y() + 4
    drag(first, below)  # Production goes to the bottom
    assert [i.description for i in inv.items] == ["Edit", "Color", "Production"]
    assert p.items == [second, third, first] and not first.is_open()
    drag(first, second.mapToGlobal(QPoint(0, 0)).y() - 40, cancel=True)  # Esc: it stays where it was
    assert [i.description for i in inv.items] == ["Edit", "Color", "Production"]
    win.flush()
    assert [i.description for i in Library(data_folder).load().invoices[inv.id].items] == [
        "Edit",
        "Color",
        "Production",
    ]
    win.setFocus()
    win.undo()  # and undo puts it back
    assert [i.description for i in win.lib.invoices[inv.id].items] == ["Production", "Edit", "Color"]


def test_one_line_item_has_nothing_to_drag(win):
    win.new_invoice()
    (only,) = win.panel.items
    assert not only.grip.active
    only.grip.pressed.emit(only.grip.mapToGlobal(only.grip.rect().center()))
    assert win.panel._lift is None


def test_the_checker_finds_words_that_dont_fit(qapp):
    from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

    from tests.cut_off import cut_off

    box = QWidget()
    lay = QVBoxLayout(box)
    words = "Your name, logo and how you get paid"
    cut, wraps, button = QLabel(words), QLabel(words), QPushButton(words)
    for w in (cut, wraps, button):
        w.setFixedWidth(60)
        lay.addWidget(w)
    wraps.setWordWrap(True)
    wraps.setMinimumHeight(wraps.heightForWidth(60))
    box.show()
    QApplication.processEvents()
    found = cut_off(box)  # the label and the button; the one that wraps fits
    assert len(found) == 2 and all(words in f for f in found)
    box.close()


def test_no_words_are_cut_off_anywhere(qapp, data_folder):
    """Every label, button and tab has room for its words, in the first window size and the smallest: words that
    might not fit wrap onto another line or end in "…", never run off an edge."""
    import time

    from saldo.ui.dialogs.client import ClientDialog
    from saldo.ui.dialogs.settings import SettingsDialog
    from saldo.ui.style import tokens
    from saldo.ui.window.main_window import MainWindow
    from tests.cut_off import cut_off

    def check(w, where: str) -> None:
        stop = time.monotonic() + (tokens.DOCK_MS + 150) / 1000  # the right panel has slid all the way in
        while time.monotonic() < stop:
            QApplication.processEvents()
            time.sleep(0.01)
        assert cut_off(w) == [], where

    def window(lib):
        w = MainWindow(lib)
        w._restored = True
        w.show()
        return w

    for size in (tokens.WINDOW_SIZE, tokens.WINDOW_MIN):
        w = window(Library(data_folder / f"{size[0]}-first").load())
        w.resize(*size)
        check(w, f"first launch, {size}")
        w.shutdown()
        w.close()
        lib = Library(data_folder / f"{size[0]}-no-invoices").load()
        lib.add_business(sample.business())
        w = window(lib)
        w.resize(*size)
        check(w, f"no invoices yet, {size}")
        w.shutdown()
        w.close()

        lib = sample.fill(Library(data_folder / f"{size[0]}-sample").load())
        w = window(lib)
        w.resize(*size)
        check(w, f"All Invoices, {size}")
        first = lib.ordered()[0]
        w.open(first.id)
        w.panel.groups["adjustments"].set_open(True)
        check(w, f"an invoice, {size}")
        w.deselect()
        w.go("clients")
        check(w, f"All Clients, {size}")
        w.open_client(lib.find_client("Desert Sun Records").id)
        check(w, f"a client, {size}")
        w.new_client()
        check(w, f"a new client, {size}")
        w.deselect()
        w.go("all")
        w.view_menu.filter.year = "1999"  # nothing showing: Clear Filters
        w._view_picked()
        check(w, f"Clear Filters, {size}")
        if size == tokens.WINDOW_SIZE:
            for pane in ("general", "profiles", "ai", "account", "shortcuts", "data"):
                d = SettingsDialog(w.lib, w, pane)
                d.show()
                check(d, f"Settings › {pane}")
                d.close()
            d = ClientDialog(first.client, lib, True, show_code=True, parent=w)
            d.show()
            check(d, "the client window")
            d.close()
        w.shutdown()
        w.close()
