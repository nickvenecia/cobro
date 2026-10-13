"""Safety (the standard's security rules, as they apply to Saldo): logos are redrawn and capped, names show as
typed, logo names can't point outside the logos folder, CSVs can't carry formulas, and files another app writes
into Saldo's folder open without being touched."""

from __future__ import annotations

import pytest

from saldo.core import sample
from saldo.core.store import Library, write_json


def _png(path, w=40, h=20, color="#336699"):
    from PySide6.QtGui import QColor, QImage

    img = QImage(w, h, QImage.Format.Format_ARGB32)
    img.fill(QColor(color))
    img.save(str(path))
    return path


def test_a_logo_is_redrawn_capped_and_kept_whole(qapp, tmp_path):
    from PySide6.QtGui import QImage

    from saldo.core.paths import logos_dir
    from saldo.ui.dialogs import profile

    name = profile.import_logo(_png(tmp_path / "logo.png", 4000, 1000))
    kept = QImage(str(logos_dir() / name))
    assert name.endswith(".png") and max(kept.width(), kept.height()) == profile.LOGO_MAX_PX
    assert not list(logos_dir().glob(".*"))  # no half-written file left behind
    assert profile.import_logo(tmp_path / "logo.png") == name  # the same picture is kept once


def test_an_svg_logo_is_kept_as_a_picture_without_whatever_else_it_carried(qapp, tmp_path):
    from saldo.core.paths import logos_dir
    from saldo.ui.dialogs import profile

    svg = tmp_path / "mark.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50">'
        '<script>alert(1)</script><rect width="100" height="50" fill="#123456"/></svg>',
        encoding="utf-8",
    )
    name = profile.import_logo(svg)
    data = (logos_dir() / name).read_bytes()
    assert name.endswith(".png") and data.startswith(b"\x89PNG") and b"script" not in data


@pytest.mark.parametrize("content", [b"not a picture", b"", b"\x89PNG\r\n\x1a\n broken"])
def test_files_that_arent_pictures_are_refused(qapp, tmp_path, content):
    from saldo.core.paths import logos_dir
    from saldo.ui.dialogs import profile

    bad = tmp_path / "logo.png"
    bad.write_bytes(content)
    with pytest.raises(ValueError, match="Use a PNG, JPG or SVG"):
        profile.import_logo(bad)
    assert not logos_dir().exists() or not any(logos_dir().iterdir())


def test_huge_logo_files_are_refused(qapp, tmp_path, monkeypatch):
    from saldo.ui.dialogs import profile

    monkeypatch.setattr(profile, "LOGO_MAX_BYTES", 10)
    with pytest.raises(ValueError, match="too big"):
        profile.import_logo(_png(tmp_path / "logo.png"))


def test_a_logo_name_cant_lead_outside_the_logos_folder():
    from saldo.core.paths import logo_path, logos_dir

    assert logo_path("abc123.png") == logos_dir() / "abc123.png"
    for name in ("", "../settings.json", "/etc/passwd", "..", ".hidden.png", "a/b.png", "a\\b.png"):
        assert logo_path(name) is None, name


def test_names_show_as_typed(qapp):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel

    from saldo.app import setup_app

    setup_app(qapp)
    lbl = QLabel('<img src="x.png"> <b>Evil</b>')
    lbl.ensurePolished()
    assert lbl.textFormat() == Qt.TextFormat.PlainText


def test_a_draft_another_app_writes_into_the_folder_opens_untouched(data_folder):
    """Another app can hand Saldo a draft by writing an invoice file into the invoices folder (in Saldo's own
    format). Saldo opens it and never renames or rewrites it just for reading it."""
    lib = sample.fill(Library(data_folder).load())
    b = next(iter(lib.businesses.values()))
    draft = {
        "id": "handed1",
        "business_id": b.id,
        "number": "JLF-2026-099",
        "auto_number": True,
        "client": {
            "id": "c9",
            "name": "Mesa Coffee Co.",
            "contact": "",
            "address": "",
            "email": "",
            "code": "",
        },
        "issued": "2026-10-01",
        "terms_days": 15,
        "project": "R-1042",
        "work_dates": "Oct 1–3, 2026",
        "items": [
            {"description": "Camera package", "details": "Oct 1–3 · 3 days", "qty": "1", "rate": "900"}
        ],
        "discount": "",
        "tax_rate": "8.25",
        "note": "Rental R-1042",
        "status": "draft",
        "created": "2026-10-01T10:00:00",
        "updated": "2026-10-01T10:00:00",
    }
    path = data_folder / "invoices" / "handed1.json"
    write_json(path, draft)
    before = path.read_bytes()
    inv = Library(data_folder).load().invoices["handed1"]
    assert inv.number == "JLF-2026-099" and inv.items[0].rate == "900" and inv.tax_rate == "8.25"
    assert path.read_bytes() == before
