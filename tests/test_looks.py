"""Look choices (core/looks.py)."""

from __future__ import annotations

from dataclasses import asdict

from saldo.core import looks
from saldo.core.model import Look


def test_an_older_look_still_opens_and_keeps_what_it_said():
    """Files from Saldo 1.x carry type styles and fonts. They open, print in Inter, and are saved back as
    they were (nothing in them is lost)."""
    old = {
        "type_style": "screenplay",
        "heading_font": "Courier Prime",
        "body_font": "Courier Prime",
        "heading_caps": True,
        "color": "oxblood",
        "custom_color": "#284B63",
        "header": "band",
        "logo": "",
        "logo_size": "large",
        "name_with_logo": True,
        "paper": "a4",
    }
    look = Look.from_dict(old)
    assert asdict(look) == old
    r = looks.resolve(look)
    assert r.band == looks.COLORS["oxblood"].accent and r.header == "band" and r.page == looks.PAPERS["a4"][1]


def test_a_new_profile_starts_turquoise_and_an_old_one_without_a_color_stays_ink():
    assert Look().color == looks.DEFAULT_COLOR == "turquoise"
    assert Look.from_dict({"header": "clean"}).color == "ink"  # what older versions used
    assert Look.from_dict(None).color == "ink"


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
    assert r.band == looks.COLORS[looks.DEFAULT_COLOR].accent
    assert r.header == "clean" and r.page == (612.0, 792.0)


def test_bundled_fonts_ship_with_the_app():
    from pathlib import Path

    folder = Path(__file__).resolve().parents[1] / "saldo" / "assets" / "fonts"
    names = {p.stem.split("-")[0] for p in folder.glob("*.[ot]tf")}
    licenses = {p.name for p in folder.glob("OFL-*.txt")}
    assert licenses == {"OFL-Inter.txt", "OFL-ibmplexmono.txt"}
    for fam in looks.BUNDLED_FONTS:
        assert fam.replace(" ", "") in names, fam
