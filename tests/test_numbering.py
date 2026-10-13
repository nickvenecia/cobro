"""Invoice numbers (core/numbering.py)."""

from __future__ import annotations

from saldo.core import numbering


def test_initials():
    assert numbering.initials("Juniper Lane Films") == "JLF"
    assert numbering.initials("Desert Sun Records") == "DSR"
    assert numbering.initials("Mesa Coffee") == "MC"
    assert numbering.initials("Saldo") == "SAL"
    assert numbering.initials("") == "INV"


def test_numbers_count_up_per_prefix_and_year():
    have = ["JLF-2026-001", "JLF-2026-007", "JLF-2025-012", "DSR-2026-020"]
    assert numbering.next_number("JLF", have, 2026) == "JLF-2026-008"
    assert numbering.next_number("JLF", have, 2027) == "JLF-2027-001"
    assert numbering.next_number("DSR", have, 2026) == "DSR-2026-021"


def test_prefix_is_safe_in_file_names():
    assert numbering.clean_prefix(" jl/2 ") == "JL2"
    assert numbering.clean_prefix("///") == "INV"


def test_client_codes_are_short_and_readable():
    assert numbering.client_code("Northwind Media") == "NRTH"
    assert numbering.client_code("Desert Sun Records") == "DSRT"
    assert numbering.client_code("A24") == "A24"
    assert numbering.client_code("") == ""
    assert numbering.clean_code(" nr-th! ") == "NRTH"


def test_each_client_gets_its_own_count():
    have = ["JLF-NRTH-2026-001", "JLF-NRTH-2026-002", "JLF-MESA-2026-001", "JLF-2026-009"]
    head = numbering.head("JLF", "NRTH", "client")
    assert numbering.next_number(head, have, 2026) == "JLF-NRTH-2026-003"
    assert numbering.next_number(numbering.head("JLF", "MESA", "client"), have, 2026) == "JLF-MESA-2026-002"
    assert numbering.next_number(numbering.head("JLF", "NRTH", "client_only"), have, 2026) == "NRTH-2026-001"
    assert numbering.next_number(numbering.head("JLF", "NRTH", "year"), have, 2026) == "JLF-2026-010"
    assert numbering.head("JLF", "", "client") == "JLF"  # no client yet
