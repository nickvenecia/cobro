"""The choices for how an invoice looks: the paper's color, header, logo size and paper size.

Plain data (no Qt): the drawing code in doc/ turns a resolved look into fonts and colors.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from cobro.core.model import Look

# The paper is set in Inter, with IBM Plex Mono for the invoice number. Both ship inside Cobro
# (cobro/assets/fonts), so every invoice looks the same on every computer.
FONT = "Inter"  # the app and the paper
MONO = "IBM Plex Mono"  # codes: the invoice number
BUNDLED_FONTS = [FONT, MONO]
CUSTOM = "custom"


@dataclass(frozen=True)
class Swatch:
    label: str
    accent: str  # rules, the amount due, the header band


COLORS: dict[str, Swatch] = {
    "ink": Swatch("Ink Blue", "#284B63"),
    "turquoise": Swatch("Turquoise", "#11776E"),
    "marigold": Swatch("Amber", "#B8720B"),  # (its key stays: saved profiles use it)
    "oxblood": Swatch("Oxblood", "#7A2E2E"),
    "sage": Swatch("Sage", "#4C6A55"),
    "plum": Swatch("Plum", "#5B3A6B"),
    "graphite": Swatch("Graphite", "#2B2B2E"),
}

DEFAULT_COLOR = "turquoise"  # Cobro's own color, for a new profile
HEADERS = {"clean": "Clean", "band": "Color Band"}
LOGO_SIZES = {
    "small": ("Small", 36.0),
    "medium": ("Medium", 54.0),
    "large": ("Large", 78.0),
}  # height, pt
PAPERS = {
    "letter": ("Letter", (612.0, 792.0)),
    "a4": ("A4", (595.28, 841.89)),
}  # points

INK = "#1B1B1F"  # body text on paper
INK_SOFT = "#5E5E66"  # secondary text on paper
RULE = "#D9D9DE"  # hairlines on paper
PAPER = "#FFFFFF"


@dataclass(frozen=True)
class Palette:
    """The paper and the colors printed on it."""

    paper: str
    ink: str
    ink_soft: str
    rule: str


LIGHT = Palette(PAPER, INK, INK_SOFT, RULE)  # every PDF, PNG and printout
DARK = Palette("#1A1A1E", "#F2F0EB", "#B4AFA8", "#3A3A42")  # the invoice window's Dark Page only

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def valid_hex(c: str) -> bool:
    return bool(_HEX.match(c or ""))


@dataclass(frozen=True)
class Resolved:
    """Everything the drawing code needs, decided."""

    accent: str  # the accent, dark enough to read as text on white
    band: str  # the accent as picked (fills the header band)
    tint: str  # a pale wash of the accent (payment and terms boxes)
    on_accent: str  # text on the header band
    header: str
    logo_h: float
    name_with_logo: bool
    page: tuple[float, float]
    paper: str = PAPER
    ink: str = INK
    ink_soft: str = INK_SOFT
    rule: str = RULE
    dark: bool = False  # the preview's Dark Page (never exported)


def mix(a: str, b: str, t: float) -> str:
    """Blend two #RRGGBB colors: t=0 gives a, t=1 gives b."""
    ra, ga, ba = (int(a[i : i + 2], 16) for i in (1, 3, 5))
    rb, gb, bb = (int(b[i : i + 2], 16) for i in (1, 3, 5))
    return "#{:02X}{:02X}{:02X}".format(*(round(x + (y - x) * t) for x, y in ((ra, rb), (ga, gb), (ba, bb))))


def luminance(c: str) -> float:
    def ch(v: int) -> float:
        s = v / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (int(c[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def accent_of(look: Look) -> str:
    if look.color == CUSTOM and valid_hex(look.custom_color):
        return look.custom_color.upper()
    return COLORS.get(look.color, COLORS[DEFAULT_COLOR]).accent


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def readable_on(accent: str, paper: str = PAPER) -> str:
    """An accent that reads as text on the paper: a pale pick (a light yellow) is darkened on white,
    a deep one (ink blue) is lightened on the dark page."""
    toward = "#000000" if luminance(paper) > 0.5 else "#FFFFFF"
    c = accent
    for _ in range(14):
        if contrast(c, paper) >= 4.5:
            break
        c = mix(c, toward, 0.12)
    return c


def resolve(look: Look, dark: bool = False) -> Resolved:
    """Turn a Look into colors and sizes. `dark`: the invoice window's Dark Page (never exported).
    Anything unknown (from a newer or older Cobro) falls back to the default."""
    raw = accent_of(look)
    pal = DARK if dark else LIGHT
    on_accent = "#FFFFFF" if luminance(raw) < 0.45 else INK
    return Resolved(
        accent=readable_on(raw, pal.paper),
        band=raw,
        tint=mix(raw, pal.paper, 0.84 if dark else 0.92),
        on_accent=on_accent,
        header=look.header if look.header in HEADERS else "clean",
        logo_h=LOGO_SIZES.get(look.logo_size, LOGO_SIZES["medium"])[1],
        name_with_logo=look.name_with_logo,
        page=PAPERS.get(look.paper, PAPERS["letter"])[1],
        paper=pal.paper,
        ink=pal.ink,
        ink_soft=pal.ink_soft,
        rule=pal.rule,
        dark=dark,
    )
