"""Make the fonts in cobro/assets/fonts (Inter, IBM Plex Mono) from Google Fonts' open-source files (SIL OFL).

    python scripts/make_fonts.py            # downloads into build/fonts-src, writes the .ttf files

Variable fonts are cut into plain fixed-weight files (Regular / SemiBold / Bold), because a PDF
embeds one weight at a time and some PDF readers draw variable fonts at their default weight only.
Only fonts whose license has no Reserved Font Name are cut this way (the OFL lets a changed font keep
its name only then); fonts with a reserved name are copied exactly as published, or not used.
The results are committed, so normal builds never run this. Needs `pip install fonttools`.
"""

from __future__ import annotations

import shutil
import sys
import urllib.request
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "cobro" / "assets" / "fonts"
SRC = ROOT / "build" / "fonts-src"
BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl/"

STYLE = {400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold", 800: "ExtraBold"}

# family name -> (source file in google/fonts, fixed axes, weights to cut)
VARIABLE = {
    "Inter": ("inter/Inter[opsz,wght].ttf", {"opsz": 14}, [400, 500, 600, 700]),
}
STATIC = {
    "IBMPlexMono-Regular.ttf": "ibmplexmono/IBMPlexMono-Regular.ttf",
}


def fetch(rel: str) -> Path:
    dest = SRC / rel
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = BASE + urllib.request.quote(rel)
        print("downloading", url)
        with urllib.request.urlopen(url, timeout=60) as r:
            dest.write_bytes(r.read())
    return dest


def rename(font: TTFont, family: str, style: str) -> None:
    """One family name for every weight, so apps list "Inter" once with its weights."""
    full = f"{family} {style}" if style != "Regular" else family
    ps = f"{family.replace(' ', '')}-{style}"
    names = font["name"]
    for rec in list(names.names):
        if rec.nameID in (1, 2, 3, 4, 6, 16, 17, 21, 22, 25):
            names.removeNames(nameID=rec.nameID)
    for nid, value in (
        (1, family),
        (2, style),
        (3, f"cobro;{ps}"),
        (4, full),
        (6, ps),
        (16, family),
        (17, style),
    ):
        names.setName(value, nid, 3, 1, 0x409)
        names.setName(value, nid, 1, 0, 0)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for family, (rel, fixed, weights) in VARIABLE.items():
        src = fetch(rel)
        for w in weights:
            vf = TTFont(src)
            loc = dict(fixed)
            loc["wght"] = w
            static = instancer.instantiateVariableFont(vf, loc, updateFontNames=False)
            style = STYLE[w]
            rename(static, family, style)
            static["OS/2"].usWeightClass = w
            static["OS/2"].usWidthClass = 7 if fixed.get("wdth") == 125 else 5
            # fsSelection: bit 0 italic, 5 bold, 6 regular
            sel = static["OS/2"].fsSelection & ~0b1100001
            sel |= (1 << 5) if w >= 700 else (1 << 6) if w == 400 else 0
            static["OS/2"].fsSelection = sel
            static["head"].macStyle = 1 if w >= 700 else 0
            path = OUT / f"{family.replace(' ', '')}-{style}.ttf"
            static.save(path)
            print("wrote", path.name)
    for name, rel in STATIC.items():
        shutil.copy(fetch(rel), OUT / name)  # used exactly as published (byte for byte)
        print("copied", name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
