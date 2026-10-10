"""Drawing and exporting (doc/): the PDF, PNG and page layout."""

from __future__ import annotations

from cobro.core import document, sample
from cobro.core.looks import TYPE_STYLES, resolve
from cobro.core.model import Look
from cobro.doc import export, fonts, render


def _pages(qapp, look=None, items=3, logo=None):
    fonts.load_bundled()
    look = look or Look()
    v = document.build(sample.invoice(items), sample.business(look))
    return render.layout(v, resolve(look, fonts.installed_families()), logo)


def test_bundled_fonts_load(qapp):
    have = fonts.load_bundled()
    for fam in fonts.bundled_families():
        assert fam in have, fam


def test_pdf_is_a_real_pdf_with_the_text_in_it(qapp, tmp_path):
    out = tmp_path / "a.pdf"
    export.to_pdf(_pages(qapp), out, title="Invoice")
    data = out.read_bytes()
    assert data.startswith(b"%PDF") and len(data) > 5000
    assert b"/FontFile2" in data  # fonts embedded, so it looks the same everywhere
    assert [p.name for p in tmp_path.iterdir()] == ["a.pdf"]  # no temp file left


def test_every_style_lays_out(qapp):
    for key in TYPE_STYLES:
        for header in ("clean", "band"):
            pages = _pages(qapp, Look(type_style=key, header=header))
            assert len(pages) == 1, (key, header)


def test_long_invoices_flow_onto_more_pages(qapp):
    pages = _pages(qapp, items=40)
    assert len(pages) >= 2
    texts = [s.text for s in pages[-1].steps if isinstance(s, render.Text)]
    assert any("Page 2 of" in t or f"Page {len(pages)} of" in t for t in texts)
    for page in pages:  # nothing runs into the footer
        for s in page.steps:
            if (
                isinstance(s, render.Text)
                and "Page" not in s.text
                and s.rect.top() < page.size[1] - render.MARGIN
            ):
                assert s.rect.bottom() <= page.size[1] - render.MARGIN + 2, s.text


def test_png_and_a4(qapp, tmp_path):
    pages = _pages(qapp, Look(paper="a4"))
    assert pages[0].size == (595.28, 841.89)
    files = export.to_png(pages, tmp_path / "a.png", dpi=72)
    assert files[0].exists()


def test_logo(qapp, tmp_path):
    from cobro.doc.fonts import ASSETS

    pages = _pages(qapp, logo=ASSETS / "icon.png")
    assert any(isinstance(s, render.Logo) for s in pages[0].steps)
    pages = _pages(qapp, logo=tmp_path / "missing.png")  # a lost logo file never breaks the invoice
    assert not any(isinstance(s, render.Logo) for s in pages[0].steps)
