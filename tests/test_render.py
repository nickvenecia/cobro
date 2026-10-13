"""Drawing and exporting (doc/): the PDF, PNG and page layout."""

from __future__ import annotations

from cobro.core import document, sample
from cobro.core.looks import COLORS, MONO, resolve
from cobro.core.model import Look
from cobro.doc import export, fonts, render


def _pages(qapp, look=None, items=3, logo=None):
    fonts.load_bundled()
    look = look or Look()
    v = document.build(sample.invoice(items), sample.business(look))
    return render.layout(v, resolve(look), logo)


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


def test_every_color_and_header_lays_out(qapp):
    for key in COLORS:
        for header in ("clean", "band"):
            pages = _pages(qapp, Look(color=key, header=header))
            assert len(pages) == 1, (key, header)


def test_inter_throughout_and_mono_for_the_number(qapp):
    steps = [s for s in _pages(qapp)[0].steps if isinstance(s, render.Text)]
    families = {s.font.family for s in steps}
    assert families == {"Inter", MONO}
    assert {s.text for s in steps if s.font.family == MONO} == {sample.invoice().number}
    assert render.MARGIN == 44


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


def test_the_dark_page_changes_colors_only(qapp, tmp_path):
    from cobro.core.looks import DARK, LIGHT

    fonts.load_bundled()
    v = document.build(sample.invoice(), sample.business())
    light = render.layout(v, resolve(Look()))
    dark = render.layout(v, resolve(Look(), dark=True))
    assert light[0].paper == LIGHT.paper and dark[0].paper == DARK.paper
    assert len(light) == len(dark) and len(light[0].steps) == len(dark[0].steps)
    for a, b in zip(light[0].steps, dark[0].steps, strict=True):  # same words in the same places
        assert type(a) is type(b) and getattr(a, "rect", None) == getattr(b, "rect", None)
        assert getattr(a, "text", None) == getattr(b, "text", None)
    ink = {s.color for s in dark[0].steps if isinstance(s, render.Text)}
    assert DARK.ink in ink and LIGHT.ink not in ink


def test_the_name_and_tagline_stay_together_beside_a_logo(qapp, tmp_path):
    """A name that fits on one line is measured as one line, so no empty line opens above the tagline,
    whatever the logo's shape; the logo is centred on the name block."""
    from PySide6.QtGui import QColor, QImage

    from cobro.doc.fonts import metrics

    fonts.load_bundled()
    for width in range(60, 400, 7):
        logo = tmp_path / f"logo{width}.png"
        img = QImage(width, 300, QImage.Format.Format_ARGB32)
        img.fill(QColor("#222222"))
        img.save(str(logo))
        for header in ("clean", "band"):
            look = Look(header=header, logo=logo.name)
            b = sample.business(look)
            b.name, b.tagline = "Juniper Lane Films & Post", "Director | Cinematographer"
            steps = render.layout(document.build(sample.invoice(), b), resolve(look), logo)[0].steps
            pic = next(s for s in steps if isinstance(s, render.Logo))
            name, tag = [s for s in steps if isinstance(s, render.Text)][:2]
            if name.font.size > 15:  # it fit on one line
                assert tag.rect.top() - name.rect.top() <= metrics(name.font).lineSpacing() + 6.5
            block = (name.rect.top(), tag.rect.bottom())
            if block[1] - block[0] > pic.rect.height():
                assert abs(pic.rect.center().y() - (block[0] + block[1]) / 2) < 1.5
