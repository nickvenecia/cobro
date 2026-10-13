"""The choices for how an invoice looks: type styles, colors, header, logo size and paper.

Plain data (no Qt): the drawing code in doc/ turns a resolved look into fonts and colors.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from cobro.core.model import Look

# Fonts that ship inside Cobro (cobro/assets/fonts), so every invoice looks the same on every computer.
# (family, what it's like). Any other font installed on the computer can be picked too.
BUNDLED_FONTS: list[tuple[str, str]] = [
    ("Archivo Expanded", "Wide, bold sans for names"),
    ("Archivo", "Sturdy sans"),
    ("Inter", "Neutral sans"),
    ("Hanken Grotesk", "Friendly sans"),
    ("Public Sans", "Plain, sturdy sans"),
    ("IBM Plex Mono", "Typewriter-like, lined-up numbers"),
    ("Courier Prime", "Screenplay typewriter"),
    ("Libre Caslon Text", "Classic book serif"),
    ("Libre Caslon Display", "Elegant serif, headings only"),
    ("DM Serif Display", "Bold display serif, headings only"),
    ("Bebas Neue", "Tall poster capitals, headings only"),
]
DISPLAY_ONLY = {"DM Serif Display", "Bebas Neue", "Libre Caslon Display"}  # too loud for running text
FALLBACK_FONT = "Inter"
FONT = "Inter"  # the app and the paper
MONO = "IBM Plex Mono"  # invoice numbers where they are data


@dataclass(frozen=True)
class TypeStyle:
    label: str
    heading: str
    body: str
    numbers: str
    caps: bool  # business name in capitals
    tip: str


TYPE_STYLES: dict[str, TypeStyle] = {
    "modern": TypeStyle(
        "Modern",
        "Archivo Expanded",
        "Hanken Grotesk",
        "IBM Plex Mono",
        True,
        "Wide bold name, clean text",
    ),
    "clean": TypeStyle("Clean", "Inter", "Inter", "Inter", False, "One neutral sans throughout"),
    "classic": TypeStyle(
        "Classic",
        "Libre Caslon Display",
        "Libre Caslon Text",
        "Libre Caslon Text",
        False,
        "Serif, like letterhead",
    ),
    "editorial": TypeStyle(
        "Editorial",
        "DM Serif Display",
        "Hanken Grotesk",
        "IBM Plex Mono",
        False,
        "Bold serif name, crisp text",
    ),
    "screenplay": TypeStyle(
        "Screenplay",
        "Courier Prime",
        "Courier Prime",
        "Courier Prime",
        True,
        "Typed like a script page",
    ),
    "poster": TypeStyle(
        "Poster",
        "Bebas Neue",
        "Archivo",
        "Archivo",
        True,
        "Tall capitals, like a one-sheet",
    ),
    "technical": TypeStyle(
        "Technical",
        "Public Sans",
        "Public Sans",
        "IBM Plex Mono",
        False,
        "Plain sans with typewriter numbers",
    ),
}
CUSTOM = "custom"


@dataclass(frozen=True)
class Swatch:
    label: str
    accent: str  # rules, the amount due, the header band


COLORS: dict[str, Swatch] = {
    "ink": Swatch("Ink Blue", "#284B63"),
    "turquoise": Swatch("Turquoise", "#11776E"),
    "marigold": Swatch("Marigold", "#B8720B"),
    "oxblood": Swatch("Oxblood", "#7A2E2E"),
    "sage": Swatch("Sage", "#4C6A55"),
    "plum": Swatch("Plum", "#5B3A6B"),
    "graphite": Swatch("Graphite", "#2B2B2E"),
}

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

INK = "#18212B"  # body text on paper
INK_SOFT = "#5A6572"  # secondary text on paper
RULE = "#D9DEE3"  # hairlines on paper
PAPER = "#FFFFFF"


@dataclass(frozen=True)
class Palette:
    """The paper and the colors printed on it."""

    paper: str
    ink: str
    ink_soft: str
    rule: str


LIGHT = Palette(PAPER, INK, INK_SOFT, RULE)  # every PDF, PNG and printout
DARK = Palette("#1C1D21", "#ECE9E4", "#9C978F", "#34363C")  # the preview's Dark Page only, easier on the eyes

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def valid_hex(c: str) -> bool:
    return bool(_HEX.match(c or ""))


@dataclass(frozen=True)
class Resolved:
    """Everything the drawing code needs, decided."""

    heading: str
    body: str
    numbers: str
    caps: bool
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
    return COLORS.get(look.color, COLORS["ink"]).accent


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


def resolve(look: Look, available: set[str] | None = None, dark: bool = False) -> Resolved:
    """Turn a Look into fonts and colors. `available`: font families this computer has
    (a picked font that's missing falls back to the style's own). `dark`: the preview's Dark Page."""
    style = TYPE_STYLES.get(look.type_style)
    if style is not None:
        heading, body, numbers, caps = (
            style.heading,
            style.body,
            style.numbers,
            style.caps,
        )
    else:  # custom
        base = TYPE_STYLES["modern"]
        heading = look.heading_font or base.heading
        body = look.body_font or base.body
        numbers = body
        caps = look.heading_caps
        if available is not None:
            heading = heading if heading in available else base.heading
            body = body if body in available else base.body
            numbers = body
    raw = accent_of(look)
    pal = DARK if dark else LIGHT
    on_accent = "#FFFFFF" if luminance(raw) < 0.45 else INK
    return Resolved(
        heading=heading,
        body=body,
        numbers=numbers,
        caps=caps,
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
