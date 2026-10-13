"""Saving and loading (core/store.py)."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date

from saldo.core.model import Business, Client, Invoice, LineItem
from saldo.core.store import Library, write_json


def test_business_gets_sensible_defaults(data_folder):
    lib = Library(data_folder)
    b = lib.add_business(Business(name="Lupine Hill Pictures", mail_address="1 Main St\nEl Paso, TX"))
    assert b.prefix == "LHP"
    assert "Checks payable to Lupine Hill Pictures" in b.payment
    assert "1 Main St, El Paso, TX" in b.payment
    assert b.terms and b.note


def test_everything_survives_a_restart(data_folder):
    lib = Library(data_folder)
    b = lib.add_business(Business(name="Lupine Hill Pictures"))
    inv = lib.new_invoice(b, today=date(2026, 10, 10))
    inv.client = Client(name="Northwind Media")
    inv.items = [LineItem("Production", "Shoot day", "1", "1500")]
    lib.save_invoice(inv)
    again = Library(data_folder).load()
    got = again.invoices[inv.id]
    assert got.number == "LHP-2026-001"
    assert got.client.name == "Northwind Media"
    assert got.items[0].rate == "1500"
    assert again.businesses[b.id].name == "Lupine Hill Pictures"


def test_new_invoices_start_from_the_business(data_folder):
    lib = Library(data_folder)
    b = lib.add_business(Business(name="Lupine Hill Pictures", terms_days=30, tax_rate="8.25"))
    first = lib.new_invoice(b, today=date(2026, 10, 10))
    second = lib.new_invoice(b, today=date(2026, 10, 11))
    assert (first.number, second.number) == ("LHP-2026-001", "LHP-2026-002")
    assert second.terms_days == 30 and second.tax_rate == "8.25"
    assert second.payment == b.payment and second.issued == "2026-10-11"


def test_duplicate_is_a_fresh_draft(data_folder):
    lib = Library(data_folder)
    b = lib.add_business(Business(name="Lupine Hill Pictures"))
    inv = lib.new_invoice(b, today=date(2026, 10, 10))
    inv.status, inv.paid_on = "paid", "2026-10-20"
    inv.client.name = "Northwind Media"
    copy = lib.duplicate(inv, today=date(2026, 11, 1))
    assert copy.id != inv.id and copy.number == "LHP-2026-002"
    assert copy.status == "draft" and not copy.paid_on
    assert copy.client.name == "Northwind Media"
    copy.client.name = "Someone Else"
    assert inv.client.name == "Northwind Media"  # a real copy, not the same object


def test_saved_clients_survive_a_restart(data_folder):
    lib = Library(data_folder)
    c = lib.save_client(Client(name=" Northwind Media ", contact="Alex"))
    assert c.name == "Northwind Media" and c.id
    lib.save_client(replace(c, contact="Alex R"))
    again = Library(data_folder).load()
    assert len(again.clients) == 1 and again.clients[c.id].contact == "Alex R"
    assert again.find_client("northwind media") is not None


def test_drafts_follow_a_client_edit_but_sent_invoices_keep_theirs(data_folder):
    lib = Library(data_folder)
    b = lib.add_business(Business(name="Lupine Hill Pictures"))
    c = lib.save_client(Client(name="Northwind Media", address="1 Old St"))
    draft, sent = lib.new_invoice(b), lib.new_invoice(b)
    draft.client, sent.client = replace(c), replace(c)
    sent.status = "sent"
    lib.save_invoice(draft)
    lib.save_invoice(sent)
    lib.save_client(replace(c, address="2 New Ave"))
    again = Library(data_folder).load()
    assert again.invoices[draft.id].client.address == "2 New Ave"
    assert again.invoices[sent.id].client.address == "1 Old St"


def test_deleting_a_client_leaves_invoices_alone(data_folder):
    lib = Library(data_folder)
    b = lib.add_business(Business(name="Lupine Hill Pictures"))
    c = lib.save_client(Client(name="Northwind Media"))
    inv = lib.new_invoice(b)
    inv.client = replace(c)
    lib.save_invoice(inv)
    lib.delete_client(c.id)
    again = Library(data_folder).load()
    assert again.clients == {} and again.invoices[inv.id].client.name == "Northwind Media"
    assert again.match_client(again.invoices[inv.id].client) is None


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


def test_a_draft_takes_its_clients_number_when_counting_per_client(data_folder):
    lib = Library(data_folder)
    b = lib.add_business(Business(name="Lupine Hill Pictures", number_style="client"))
    nm = lib.save_client(Client(name="Northwind Media"))
    mesa = lib.save_client(Client(name="Mesa Coffee", code="MESA"))
    first = lib.new_invoice(b, today=date(2026, 10, 10))
    assert first.number == "LHP-2026-001"  # no client picked yet
    first.client = replace(nm)
    assert lib.renumber(first) and first.number == "LHP-NRTH-2026-001"
    lib.save_invoice(first)
    second = lib.new_invoice(b, today=date(2026, 10, 11))
    second.client = replace(nm)
    lib.renumber(second)
    assert second.number == "LHP-NRTH-2026-002"
    second.client = replace(mesa)
    lib.renumber(second)
    assert second.number == "LHP-MESA-2026-001"
    assert not lib.renumber(second)  # already right: left alone
    assert lib.duplicate(first, today=date(2026, 11, 1)).number == "LHP-NRTH-2026-002"


def test_typed_numbers_and_sent_invoices_keep_their_number(data_folder):
    lib = Library(data_folder)
    b = lib.add_business(Business(name="Lupine Hill Pictures", number_style="client"))
    nm = lib.save_client(Client(name="Northwind Media"))
    typed = lib.new_invoice(b, today=date(2026, 10, 10))
    typed.number, typed.auto_number = "SPECIAL-7", False
    typed.client = replace(nm)
    assert not lib.renumber(typed) and typed.number == "SPECIAL-7"
    sent = lib.new_invoice(b, today=date(2026, 10, 10))
    sent.status = "sent"
    sent.client = replace(nm)
    assert not lib.renumber(sent)
    old = Invoice.from_dict({"number": "LHP-2026-004", "client": {"name": "Northwind Media"}})
    assert old.auto_number is False  # invoices from before keep the number they have
