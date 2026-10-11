"""The window (ui/): first launch, making an invoice, editing it, and it being saved."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication

from cobro.core import sample
from cobro.core.model import Client, LineItem
from cobro.core.store import Library


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


def test_first_launch_asks_for_the_business(qapp, data_folder):
    from cobro.ui.main_window import MainWindow

    w = MainWindow(Library(data_folder).load())
    assert w.inv is None
    assert w.details.empty.isVisibleTo(w.details) and w.details.empty_btn.text() == "Add Your Profile…"
    assert not w.preview.btn_pdf.isEnabled()
    w.shutdown()


def test_new_invoice_edit_and_save(qapp, data_folder):
    from cobro.ui.main_window import MainWindow

    lib = Library(data_folder)
    lib.add_business(sample.business())
    client = lib.save_client(Client(name="Digital Empire", contact="Ana"))
    w = MainWindow(lib.load())
    w.new_invoice()
    inv = w.inv
    assert inv is not None and inv.number.startswith("JLF-")
    assert w.details.client.currentIndex() == -1  # "Choose a Client"
    assert not w.details.edit_client.isVisibleTo(w.details)
    pick(w.details.client, client.id)
    assert inv.client.name == "Digital Empire" and inv.client.contact == "Ana"
    assert w.details.edit_client.isVisibleTo(w.details)
    ed = w.details.items[0]
    ed.desc.textEdited.emit("Production")
    ed.rate.textEdited.emit("1500")
    assert ed.amount.text() == "$1,500.00" and ed.title.full_text() == "Production"
    w.flush()
    again = Library(data_folder).load().invoices[inv.id]
    assert again.client.name == "Digital Empire" and again.items[0].rate == "1500"
    assert w.pages() and w.list.cards[inv.id].amount.text() == "$1,500.00"
    w.shutdown()


def test_look_changes_redraw_and_save(qapp, data_folder):
    from cobro.ui.main_window import MainWindow

    lib = Library(data_folder)
    b = lib.add_business(sample.business())
    lib.new_invoice(b)
    w = MainWindow(lib.load())
    w.details.color.setCurrentIndex(w.details.color.findData("oxblood"))
    w.details.header.setCurrentIndex(w.details.header.findData("band"))
    assert Library(data_folder).load().businesses[b.id].look.header == "band"
    assert w.pages()[0].steps[0].color == "#7A2E2E"  # the band
    w.shutdown()


def test_paid_shows_its_date(qapp, data_folder):
    from cobro.ui.main_window import MainWindow

    lib = Library(data_folder)
    b = lib.add_business(sample.business())
    lib.new_invoice(b)
    w = MainWindow(lib.load())
    w.details.status.setCurrentIndex(w.details.status.findData("paid"))
    assert w.inv.status == "paid" and w.inv.paid_on and w.inv.sent_on
    assert w.details.paid_sec.isVisibleTo(w.details)
    w.shutdown()


def test_an_unsaved_client_still_shows_and_typing_never_saves_clients(qapp, data_folder):
    from cobro.ui.details import THIS_CLIENT
    from cobro.ui.main_window import MainWindow

    lib = Library(data_folder)
    b = lib.add_business(sample.business())
    inv = lib.new_invoice(b)
    inv.client = Client(name="Old Client From 1.0")
    lib.save_invoice(inv)
    w = MainWindow(lib.load())
    assert w.details.client.currentData() == THIS_CLIENT
    assert w.details.client.currentText() == "Old Client From 1.0"
    w.shutdown()
    assert Library(data_folder).load().clients == {}  # clients are only saved on purpose


def test_line_items_fold_one_at_a_time_and_move(qapp, data_folder):
    from cobro.ui.main_window import MainWindow

    lib = Library(data_folder)
    b = lib.add_business(sample.business())
    inv = lib.new_invoice(b)
    inv.items = [LineItem("Production", "", "1", "1500"), LineItem("Edit", "", "2", "500")]
    lib.save_invoice(inv)
    w = MainWindow(lib.load())
    d = w.details
    first, second = d.items
    assert not first.is_open() and not second.is_open()  # a finished list starts folded
    first.head.clicked.emit()
    assert first.is_open() and not second.is_open()
    second.head.clicked.emit()
    assert second.is_open() and not first.is_open()
    assert not first.act_up.isEnabled() and first.act_down.isEnabled()
    d._move_item(first, 1)
    assert [i.description for i in w.inv.items] == ["Edit", "Production"]
    assert d.items == [second, first] and first.act_up.isEnabled()
    d._duplicate_item(second)
    assert [i.description for i in w.inv.items] == ["Edit", "Edit", "Production"]
    assert w.inv.items[0] is not w.inv.items[1]
    d._remove_item(first)
    assert [i.description for i in w.inv.items] == ["Edit", "Edit"]
    d.add_item.click()
    assert d.items[-1].is_open() and sum(ed.is_open() for ed in d.items) == 1
    assert "2 items" in d.groups["items"]._summary
    w.shutdown()


def test_scrolling_never_changes_a_date_or_dropdown(qapp, data_folder):
    from cobro.ui.main_window import MainWindow

    lib = Library(data_folder)
    b = lib.add_business(sample.business())
    lib.new_invoice(b)
    w = MainWindow(lib.load())
    w.show()
    issued, terms = w.details.issued.date(), w.details.terms_days.currentData()
    wheel(w.details.issued)
    wheel(w.details.terms_days)
    assert w.details.issued.date() == issued and w.details.terms_days.currentData() == terms
    w.shutdown()


def test_the_dark_page_is_only_for_the_preview(qapp, data_folder):
    from cobro.ui.main_window import MainWindow

    lib = Library(data_folder)
    b = lib.add_business(sample.business())
    lib.new_invoice(b)
    w = MainWindow(lib.load())
    w.preview.btn_dark.click()
    assert w.preview.dark and w.lib.settings["dark_preview"] is True
    assert w.preview.view.pages[0].paper != "#FFFFFF"  # the preview is dark
    assert w.pages()[0].paper == "#FFFFFF"  # what gets saved and printed is not
    w.shutdown()


def test_every_group_folds_and_is_remembered(qapp, data_folder):
    from cobro.ui.main_window import MainWindow

    lib = Library(data_folder)
    b = lib.add_business(sample.business())
    lib.new_invoice(b)
    w = MainWindow(lib.load())
    who = w.details.groups["who"]
    assert who.is_open()
    who.header.click()
    assert not who.is_open() and "from Juniper Lane Films" in who.header.text() + who._summary
    w.shutdown()
    w = MainWindow(Library(data_folder).load())
    assert not w.details.groups["who"].is_open() and w.details.groups["invoice"].is_open()
    w.shutdown()


def test_picking_a_client_gives_a_draft_its_number_when_counting_per_client(qapp, data_folder):
    from cobro.ui.main_window import MainWindow

    lib = Library(data_folder)
    b = sample.business()
    b.number_style = "client"
    lib.add_business(b)
    north = lib.save_client(Client(name="Northwind Media"))
    mesa = lib.save_client(Client(name="Mesa Coffee", code="MESA"))
    w = MainWindow(lib.load())
    w.new_invoice()
    year = w.inv.issued[:4]
    pick(w.details.client, north.id)
    assert w.inv.number == f"JLF-NRTH-{year}-001" == w.details.number.text()
    pick(w.details.client, mesa.id)
    assert w.inv.number == f"JLF-MESA-{year}-001"
    w.details.number.setText("JLF-SPECIAL")
    w.details.number.textEdited.emit("JLF-SPECIAL")
    pick(w.details.client, north.id)
    assert w.inv.number == "JLF-SPECIAL"  # a number you typed stays yours
    w.shutdown()


def test_the_profile_dialog_saves_a_copy_and_cancel_changes_nothing(qapp, data_folder):
    from cobro.ui.profile_dialog import ProfileDialog

    b = sample.business()
    d = ProfileDialog(b, can_delete=False)
    d.number_style.setCurrentIndex(d.number_style.findData("client"))
    d._set_logo("logo.png")
    assert b.look.logo == "" and b.number_style == "year"  # nothing changes until Save
    assert d.number_style.currentText().startswith("JLF-ACME-")
    d._save()
    assert d.business.number_style == "client" and d.business.look.logo == "logo.png"
    assert b.look.logo == ""


def test_new_client_from_the_menu_only_saves_it(qapp, data_folder, monkeypatch):
    from cobro.ui import main_window
    from cobro.ui.main_window import MainWindow

    lib = Library(data_folder)
    b = lib.add_business(sample.business())
    inv = lib.new_invoice(b)
    inv.client, inv.status = Client(name="Paid Client"), "paid"
    lib.save_invoice(inv)
    w = MainWindow(lib.load())

    class Saved:
        DialogCode = main_window.ClientDialog.DialogCode
        deleted, client = False, Client(name="Brand New Co")

        def __init__(self, *_a, **_k):
            pass

        def exec(self):
            return self.DialogCode.Accepted

    monkeypatch.setattr(main_window, "ClientDialog", Saved)
    w.edit_client(True, assign=False)
    assert w.inv.client.name == "Paid Client"  # the open (paid) invoice is untouched
    assert w.lib.find_client("Brand New Co") is not None
    assert w.details.client.findText("Brand New Co") >= 0  # and it's ready to pick
    w.edit_client(True)  # New Client… under Bill To fills in the open invoice
    assert w.inv.client.name == "Brand New Co"
    w.shutdown()
