"""Invoice numbers (core/numbering.py)."""

from __future__ import annotations

from cobro.core import numbering


def test_initials():
    assert numbering.initials("Nicholas Venecia") == "NV"
    assert numbering.initials("Dopamine Productions") == "DP"
    assert numbering.initials("Bad Filmmaker") == "BF"
    assert numbering.initials("Cobro") == "COB"
    assert numbering.initials("") == "INV"


def test_numbers_count_up_per_prefix_and_year():
    have = ["NV-2026-001", "NV-2026-007", "NV-2025-012", "DP-2026-020"]
    assert numbering.next_number("NV", have, 2026) == "NV-2026-008"
    assert numbering.next_number("NV", have, 2027) == "NV-2027-001"
    assert numbering.next_number("DP", have, 2026) == "DP-2026-021"


def test_prefix_is_safe_in_file_names():
    assert numbering.clean_prefix(" nv/2 ") == "NV2"
    assert numbering.clean_prefix("///") == "INV"


def test_client_codes_are_short_and_readable():
    assert numbering.client_code("Digital Empire") == "DGTL"
    assert numbering.client_code("Desert Sun Records") == "DSRT"
    assert numbering.client_code("A24") == "A24"
    assert numbering.client_code("") == ""
    assert numbering.clean_code(" dg-tl! ") == "DGTL"


def test_each_client_gets_its_own_count():
    have = ["NV-DGTL-2026-001", "NV-DGTL-2026-002", "NV-MESA-2026-001", "NV-2026-009"]
    head = numbering.head("NV", "DGTL", "client")
    assert numbering.next_number(head, have, 2026) == "NV-DGTL-2026-003"
    assert numbering.next_number(numbering.head("NV", "MESA", "client"), have, 2026) == "NV-MESA-2026-002"
    assert numbering.next_number(numbering.head("NV", "DGTL", "client_only"), have, 2026) == "DGTL-2026-001"
    assert numbering.next_number(numbering.head("NV", "DGTL", "year"), have, 2026) == "NV-2026-010"
    assert numbering.head("NV", "", "client") == "NV"  # no client yet
