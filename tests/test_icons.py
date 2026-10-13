"""Every icon the code names exists (a missing one only shows up as a crash when its button is drawn)."""

from __future__ import annotations

import re
from pathlib import Path

from saldo.ui.style import theme

ROOT = Path(__file__).resolve().parent.parent / "saldo"
CALLS = re.compile(
    r'(?:icon|menu_icon|IconLabel|circle_button|icon_button|header_icon|set_icon|menu_action)\(\s*"([a-z0-9-]+)"'
)
SECOND = re.compile(r'footer_button\(\s*"[^"]*",\s*"([a-z0-9-]+)"')  # the icon comes after the words


def test_every_named_icon_exists():
    names = set()
    for f in ROOT.rglob("*.py"):
        text = f.read_text()
        names |= set(CALLS.findall(text)) | set(SECOND.findall(text))
    missing = sorted(n for n in names if n not in theme._SVG)
    assert not missing, missing


def test_settings_and_sidebar_icons_exist():
    from saldo.ui.dialogs.settings import PANES
    from saldo.ui.window.common import PLACES

    names = {icon for _k, _l, icon in PANES} | {icon for _label, icon in PLACES.values()}
    assert names and all(n in theme._SVG for n in names), names
