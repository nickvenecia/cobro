"""`cobro cli ...`: the same drawing code without a window (used by tests and the build's smoke test).

python -m cobro cli sample OUT.pdf [--style screenplay] [--color oxblood] [--header band] [--items 3]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    return QGuiApplication.instance() or QGuiApplication(sys.argv[:1])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cobro cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample", help="draw the sample invoice into a PDF or PNG")
    s.add_argument("out", type=Path)
    s.add_argument("--style", default="modern")
    s.add_argument("--color", default="ink")
    s.add_argument("--header", default="clean")
    s.add_argument("--items", type=int, default=3)
    s.add_argument("--logo", type=Path, default=None)
    args = ap.parse_args(argv)

    _app()
    from .core import document, sample
    from .core.looks import resolve
    from .core.model import Look
    from .doc import export, fonts, render

    fonts.load_bundled()
    look = Look(type_style=args.style, color=args.color, header=args.header)
    biz = sample.business(look)
    view = document.build(sample.invoice(args.items), biz)
    pages = render.layout(view, resolve(look, fonts.installed_families()), args.logo)
    if args.out.suffix.lower() == ".png":
        export.to_png(pages, args.out)
    else:
        export.to_pdf(pages, args.out, title=f"Invoice {view.number}")
    print(f"wrote {args.out} ({len(pages)} page{'s' if len(pages) > 1 else ''})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
