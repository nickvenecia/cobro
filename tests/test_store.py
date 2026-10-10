"""Saving and loading (core/store.py)."""

from __future__ import annotations

import json
from datetime import date

from cobro.core.model import Business, Client, Invoice, LineItem
from cobro.core.store import Library, write_json


def test_business_gets_sensible_defaults(data_folder):
    lib = Library(data_folder)
    b = lib.add_business(Business(name="Nicholas Venecia", mail_address="1 Main St\nEl Paso, TX"))
    assert b.prefix == "NV"
    assert "Checks payable to Nicholas Venecia" in b.payment
    assert "1 Main St, El Paso, TX" in b.payment
    assert b.terms and b.note


def test_everything_survives_a_restart(data_folder):
    lib = Library(data_folder)
    b = lib.add_business(Business(name="Nicholas Venecia"))
    inv = lib.new_invoice(b, today=date(2026, 10, 10))
    inv.client = Client(name="Digital Empire")
    inv.items = [LineItem("Production", "Shoot day", "1", "1500")]
    lib.save_invoice(inv)
    again = Library(data_folder).load()
    got = again.invoices[inv.id]
    assert got.number == "NV-2026-001"
    assert got.client.name == "Digital Empire"
    assert got.items[0].rate == "1500"
    assert again.businesses[b.id].name == "Nicholas Venecia"


def test_new_invoices_start_from_the_business(data_folder):
    lib = Library(data_folder)
    b = lib.add_business(Business(name="Nicholas Venecia", terms_days=30, tax_rate="8.25"))
    first = lib.new_invoice(b, today=date(2026, 10, 10))
    second = lib.new_invoice(b, today=date(2026, 10, 11))
    assert (first.number, second.number) == ("NV-2026-001", "NV-2026-002")
    assert second.terms_days == 30 and second.tax_rate == "8.25"
    assert second.payment == b.payment and second.issued == "2026-10-11"


def test_duplicate_is_a_fresh_draft(data_folder):
    lib = Library(data_folder)
    b = lib.add_business(Business(name="Nicholas Venecia"))
    inv = lib.new_invoice(b, today=date(2026, 10, 10))
    inv.status, inv.paid_on = "paid", "2026-10-20"
    inv.client.name = "Digital Empire"
    copy = lib.duplicate(inv, today=date(2026, 11, 1))
    assert copy.id != inv.id and copy.number == "NV-2026-002"
    assert copy.status == "draft" and not copy.paid_on
    assert copy.client.name == "Digital Empire"
    copy.client.name = "Someone Else"
    assert inv.client.name == "Digital Empire"  # a real copy, not the same object


def test_clients_are_remembered_by_name(data_folder):
    lib = Library(data_folder)
    c = lib.remember_client(Client(name="Digital Empire", contact="Ana"))
    again = lib.remember_client(Client(name="digital empire ", contact="Ana B"))
    assert again.id == c.id and len(lib.clients) == 1
    assert Library(data_folder).load().clients[c.id].contact == "Ana B"
    assert lib.remember_client(Client(name="  ")) is None


def test_a_broken_file_is_set_aside_not_lost(data_folder):
    data_folder.mkdir(parents=True)
    (data_folder / "businesses.json").write_text("{not json", encoding="utf-8")
    lib = Library(data_folder).load()
    assert lib.businesses == {}
    kept = list(data_folder.glob("businesses.json.unreadable-*"))
    assert len(kept) == 1 and kept[0].read_text(encoding="utf-8") == "{not json"


def test_files_from_other_versions_still_open(data_folder):
    data = Invoice().to_dict()
    data["some_future_field"] = 1
    del data["note"]
    data["items"] = [{"description": "x", "qty": 2, "rate": 5}]
    write_json(data_folder / "invoices" / "x.json", data)
    inv = next(iter(Library(data_folder).load().invoices.values()))
    assert inv.note == "" and inv.items[0].qty == "2"


def test_writes_are_atomic(data_folder):
    path = data_folder / "a.json"
    write_json(path, {"a": 1})
    write_json(path, {"a": 2})
    assert json.loads(path.read_text()) == {"a": 2}
    assert [p.name for p in data_folder.iterdir()] == ["a.json"]  # no temp files left
