"""A release's notes: this version's part of CHANGELOG.md, then the table of downloads.

    python scripts/release_notes.py 2.0.0 > notes.md     (or v2.0.0)

The build (.github/workflows/build.yml) runs it on every push and pull request, so a mistake shows up before
anything is merged: it stops with an error if CHANGELOG.md's top section isn't the version in
saldo/__init__.py, or if anything still sits under "Unreleased" (notes go straight under their version).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"
HEADING = re.compile(r"^## +(.+?)\s*$", re.MULTILINE)

DOWNLOADS = """## Download
| Your computer | File |
|---|---|
| Mac with Apple Silicon (M1 and newer) | `Saldo-mac-apple-silicon.dmg` |
| Intel Mac | `Saldo-mac-intel.dmg` |
| Windows (installer) | `Saldo-windows-setup.exe` |
| Windows (no install) | `Saldo-windows-portable.zip` |
| Linux (one file, double-click to run) | `Saldo-linux-x64.AppImage` |
| Linux (folder + install script) | `Saldo-linux-x64.tar.gz` |

Everything Saldo needs is inside, nothing else to install. (The `Cobro-…` files are the same app, for copies of \
Cobro, its old name, updating themselves.)
**First launch on Mac:** if macOS says it can't check the app, open **System Settings → Privacy & Security** and \
click **Open Anyway**.
**First launch on Windows:** if SmartScreen appears, click **More info → Run anyway**.
"""


class NotesError(ValueError):
    pass


def section(changelog: str, version: str) -> str:
    """The notes under `## version`, which must be the top section; nothing may be left under Unreleased."""
    heads = [(m.group(1), m.start(), m.end()) for m in HEADING.finditer(changelog)]
    if any(h.casefold().startswith("unreleased") for h, _s, _e in heads):
        raise NotesError(
            'CHANGELOG.md has an "Unreleased" section. Put those notes under the new version instead '
            f"(## {version}, the same number as in saldo/__init__.py)."
        )
    if not heads or heads[0][0] != version:
        top = heads[0][0] if heads else "nothing"
        raise NotesError(
            f"CHANGELOG.md starts with ## {top}, but saldo/__init__.py says {version}. "
            f"Add a ## {version} section at the top with what changed."
        )
    end = heads[1][1] if len(heads) > 1 else len(changelog)
    notes = changelog[heads[0][2] : end].strip()
    if not notes:
        raise NotesError(f"CHANGELOG.md's ## {version} section is empty. Say what changed.")
    return notes


def changes(changelog: str, version: str) -> str:
    """This version's entries (checked: see section), for the update window to show."""
    return section(changelog, version.lstrip("vV"))


def notes(changelog: str, version: str) -> str:
    """The whole release text. The update window shows the What's New part (core/update.whats_new leaves the
    downloads out), so the changelog's plain words are what people read before updating."""
    return f"## What's New\n\n{changes(changelog, version)}\n\n{DOWNLOADS}"


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    try:
        print(notes(CHANGELOG.read_text(encoding="utf-8"), argv[0]))
    except NotesError as e:
        print(f"::error file=CHANGELOG.md::{e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
