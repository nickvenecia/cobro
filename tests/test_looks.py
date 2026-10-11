"""Look choices (core/looks.py)."""

from __future__ import annotations

from cobro.core import looks
from cobro.core.model import Look


def test_styles_pick_their_fonts():
    r = looks.resolve(Look(type_style="screenplay"))
    assert (r.heading, r.body, r.caps) == ("Courier Prime", "Courier Prime", True)


def test_custom_fonts_fall_back_when_missing():
    look = Look(type_style="custom", heading_font="Not A Real Font", body_font="Inter")
    r = looks.resolve(look, available={"Inter", "Archivo Expanded"})
    assert r.heading == "Archivo Expanded" and r.body == "Inter"


def test_a_pale_custom_color_still_reads_on_paper():
    look = Look(color="custom", custom_color="#F5E663")  # pale yellow
    r = looks.resolve(look)
    assert (1.05 / (looks.luminance(r.accent) + 0.05)) >= 4.5
    assert r.band == "#F5E663"
    assert r.on_accent == looks.INK  # dark text on a light band


def test_the_dark_page_lightens_a_deep_accent():
    r = looks.resolve(Look(color="ink"), dark=True)
    assert looks.contrast(r.accent, looks.DARK.paper) >= 4.5
    assert (r.paper, r.ink) == (looks.DARK.paper, looks.DARK.ink) and r.dark
    assert looks.resolve(Look()).paper == looks.PAPER  # light unless asked


def test_bad_values_fall_back():
    r = looks.resolve(Look(color="nope", header="nope", paper="nope", logo_size="nope"))
    assert r.accent == looks.COLORS["ink"].accent
    assert r.header == "clean" and r.page == (612.0, 792.0)


def test_bundled_fonts_ship_with_the_app():
    from pathlib import Path

    folder = Path(__file__).resolve().parents[1] / "cobro" / "assets" / "fonts"
    names = {p.stem.split("-")[0] for p in folder.glob("*.[ot]tf")}
    for fam, _ in looks.BUNDLED_FONTS:
        assert fam.replace(" ", "") in names, fam
