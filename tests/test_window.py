"""The window (ui/): first launch, making an invoice, editing it, and it being saved."""

from __future__ import annotations

from cobro.core import sample
from cobro.core.store import Library


def test_first_launch_asks_for_the_business(qapp, data_folder):
    from cobro.ui.main_window import MainWindow

    w = MainWindow(Library(data_folder).load())
    assert w.inv is None
    assert w.details.empty.isVisibleTo(w.details) and w.details.empty_btn.text() == "Add Your Business…"
    assert not w.preview.btn_pdf.isEnabled()
    w.shutdown()


def test_new_invoice_edit_and_save(qapp, data_folder):
    from cobro.ui.main_window import MainWindow

    lib = Library(data_folder)
    lib.add_business(sample.business())
    w = MainWindow(lib.load())
    w.new_invoice()
    inv = w.inv
    assert inv is not None and inv.number.startswith("JLF-")
    w.details.client.setText("Digital Empire")
    w.details.client.textEdited.emit("Digital Empire")
    ed = w.details.items[0]
    ed.desc.textEdited.emit("Production")
    ed.rate.textEdited.emit("1500")
    w.flush()
    again = Library(data_folder).load().invoices[inv.id]
    assert again.client.name == "Digital Empire" and again.items[0].rate == "1500"
    assert w.pages() and w.list.cards[inv.id].amount.text() == "$1,500.00"
    w.shutdown()
    assert Library(data_folder).load().find_client("Digital Empire") is not None


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
