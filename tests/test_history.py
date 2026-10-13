"""Undo and redo (core/history.py)."""

from __future__ import annotations

from saldo.core import sample
from saldo.core.history import History
from saldo.core.model import Client
from saldo.core.store import Library


def test_undo_redo_round_trip(tmp_path):
    lib = sample.fill(Library(tmp_path).load())
    h = History(lib)
    assert not h.can_undo() and h.undo() is None
    first = lib.ordered()[0]
    old = first.project
    first.project = "Changed"
    h.mark()
    victim = lib.ordered()[-1].id
    lib.delete_invoice(victim)
    h.mark()
    assert h.undo() == "1 invoice"
    assert victim in lib.invoices and victim in Library(tmp_path).load().invoices
    assert h.undo() == first.number
    assert lib.invoices[first.id].project == old
    assert h.undo() is None
    h.redo()
    assert lib.invoices[first.id].project == "Changed"
    h.redo()
    assert victim not in lib.invoices and victim not in Library(tmp_path).load().invoices
    assert h.redo() is None


def test_clients_and_profiles_too(tmp_path):
    lib = sample.fill(Library(tmp_path).load())
    h = History(lib)
    lib.save_client(Client(name="Undo Test"))
    h.mark()
    assert h.undo() == "clients"
    assert lib.find_client("Undo Test") is None and Library(tmp_path).load().find_client("Undo Test") is None


def test_a_change_taken_back_leaves_no_step(tmp_path):
    lib = sample.fill(Library(tmp_path).load())
    h = History(lib)
    inv = lib.ordered()[0]
    old = inv.note
    inv.note = "x"
    h.mark()
    inv.note = old
    h.mark()
    assert not h.undos


def test_saving_alone_is_not_a_change(tmp_path):
    lib = sample.fill(Library(tmp_path).load())
    h = History(lib)
    lib.save_invoice(lib.ordered()[0])  # stamps "updated"
    assert not h.mark()
