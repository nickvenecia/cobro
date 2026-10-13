"""Invoice numbers (core/numbering.py)."""

from __future__ import annotations

from cobro.core import numbering


def test_initials():
    assert numbering.initials("Rosa Marquez") == "RM"
    assert numbering.initials("Mesquite Productions") == "MP"
    assert numbering.initials("Night Owl") == "NO"
    assert numbering.initials("Cobro") == "COB"
    assert numbering.initials("") == "INV"


def test_numbers_count_up_per_prefix_and_year():
    have = ["RM-2026-001", "RM-2026-007", "RM-2025-012", "MP-2026-020"]
    assert numbering.next_number("RM", have, 2026) == "RM-2026-008"
    assert numbering.next_number("RM", have, 2027) == "RM-2027-001"
    assert numbering.next_number("MP", have, 2026) == "MP-2026-021"


def test_prefix_is_safe_in_file_names():
    assert numbering.clean_prefix(" nv/2 ") == "NV2"
    assert numbering.clean_prefix("///") == "INV"


def test_client_codes_are_short_and_readable():
    assert numbering.client_code("Northwind Media") == "NRTH"
    assert numbering.client_code("Desert Sun Records") == "DSRT"
    assert numbering.client_code("A24") == "A24"
    assert numbering.client_code("") == ""
    assert numbering.clean_code(" nr-th! ") == "NRTH"


def test_each_client_gets_its_own_count():
    have = ["RM-NRTH-2026-001", "RM-NRTH-2026-002", "RM-MESA-2026-001", "RM-2026-009"]
    head = numbering.head("RM", "NRTH", "client")
    assert numbering.next_number(head, have, 2026) == "RM-NRTH-2026-003"
    assert numbering.next_number(numbering.head("RM", "MESA", "client"), have, 2026) == "RM-MESA-2026-002"
    assert numbering.next_number(numbering.head("RM", "NRTH", "client_only"), have, 2026) == "NRTH-2026-001"
    assert numbering.next_number(numbering.head("RM", "NRTH", "year"), have, 2026) == "RM-2026-010"
    assert numbering.head("RM", "", "client") == "RM"  # no client yet
