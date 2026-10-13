"""A release's notes: this version's part of CHANGELOG.md, then the table of downloads.

    python scripts/release_notes.py 1.2.0 > notes.md

The build (.github/workflows/build.yml) runs it on every push and pull request, so a mistake shows up before
anything is merged: it stops with an error if CHANGELOG.md's top section isn't the version in
cobro/__init__.py, or if anything still sits under "Unreleased" (notes go straight under their version).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADING = re.compile(r"^## +(.+?)\s*$", re.MULTILINE)

DOWNLOADS = """## Download
| Your computer | File |
|---|---|
| Mac with Apple Silicon (M1 and newer) | `Cobro-mac-apple-silicon.dmg` |
| Intel Mac | `Cobro-mac-intel.dmg` |
| Windows (installer) | `Cobro-windows-setup.exe` |
| Windows (no install) | `Cobro-windows-portable.zip` |
| Linux (one file, double-click to run) | `Cobro-linux-x64.AppImage` |
| Linux (folder + install script) | `Cobro-linux-x64.tar.gz` |

Everything Cobro needs is inside, nothing else to install.
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
            f"(## {version}, the same number as in cobro/__init__.py)."
        )
    if not heads or heads[0][0] != version:
        top = heads[0][0] if heads else "nothing"
        raise NotesError(
            f"CHANGELOG.md starts with ## {top}, but cobro/__init__.py says {version}. "
            f"Add a ## {version} section at the top with what changed."
        )
    end = heads[1][1] if len(heads) > 1 else len(changelog)
    notes = changelog[heads[0][2] : end].strip()
    if not notes:
        raise NotesError(f"CHANGELOG.md's ## {version} section is empty. Say what changed.")
    return notes


def notes(changelog: str, version: str) -> str:
    return f"{section(changelog, version)}\n\n{DOWNLOADS}"


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    try:
        print(notes((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), argv[0]))
    except NotesError as e:
        print(f"::error file=CHANGELOG.md::{e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
