"""Moving in from Cobro, this app's old name: everything comes along the first time Saldo opens.

- carry_over(): Cobro kept its files in its own data folder ("Cobro" on Mac and Windows, "cobro" on Linux).
  The first time Saldo opens, all of it is copied into Saldo's folder, so every invoice, client, profile,
  number and setting is there. The old folder is only read: nothing in it is moved, changed or deleted.
- rename_plan(): an older Cobro's updater puts the new version where Cobro was, named Cobro.app. Saldo then
  renames itself Saldo.app (a helper does it once Saldo has quit, and opens it again).
- leftovers(): Saldo.app installed by hand next to the old Cobro.app. The old one can go to the Trash
  instead of sitting beside the new one.

When nobody is on Cobro any more, this file and the few lines that call it can go.
"""

from __future__ import annotations

import os
import plistlib
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from xml.parsers.expat import ExpatError

from saldo.core import update
from saldo.core.log import get_logger
from saldo.core.paths import data_dir, standard_data_dir

log = get_logger(__name__)

OLD_NAME = "Cobro"
OLD_APP = "Cobro.app"
NEW_APP = "Saldo.app"
KEEP_NAME = "--keep-name"  # the rename didn't work: open as Cobro.app and don't try again
# Cobro's own, and Saldo's (the copy an older Cobro's updater installed as Cobro.app)
BUNDLE_IDS = ("com.badfilmmaker.cobro", "com.badfilmmaker.saldo")
DATA = (
    "businesses.json",
    "clients.json",
    "invoices",
    "settings.json",
)  # a folder with any of these is in use
# Cobro's Linux install.sh put the program inside the data folder: the program stays behind
PROGRAM = ("_internal", "Cobro", "install.sh", "cobro.desktop", "icon.png")
_INCOMING = ".from-cobro-"


def old_data_dir() -> Path:
    return standard_data_dir(OLD_NAME)


def has_data(folder: Path) -> bool:
    return any((folder / name).exists() for name in DATA)


def carry_over() -> bool:
    """Copy Cobro's data folder into Saldo's, the first time: when Saldo's holds none of your files yet (the log
    it just started doesn't count) and Cobro's does. Never into a test or trial folder (SALDO_DATA_DIR).
    True if it copied. Raises OSError if the copy failed: Saldo's folder is then as it was, and the next start
    tries again."""
    new = data_dir()
    if new != standard_data_dir():
        return False
    return copy_folder(old_data_dir(), new)


def copy_folder(old: Path, new: Path) -> bool:
    if not old.is_dir() or not has_data(old) or has_data(new):
        return False
    new.mkdir(parents=True, exist_ok=True)
    for stale in new.glob(_INCOMING + "*"):  # a copy cut short by a crash last time (only ever our own)
        shutil.rmtree(stale, ignore_errors=True)
    # The whole copy is made first, beside Saldo's files (the same disk), then each part is moved into place in
    # one step: a copy cut short by a full disk leaves Saldo's folder as it was.
    incoming = Path(tempfile.mkdtemp(prefix=_INCOMING, dir=new))
    try:
        copy = incoming / "copy"
        shutil.copytree(old, copy, ignore=_leave_program(old), ignore_dangling_symlinks=True)
        for part in sorted(copy.iterdir(), key=lambda p: p.name in DATA):  # your files last: then it's done
            if not (new / part.name).exists():  # Saldo's own (its log) stays
                part.rename(new / part.name)
    finally:
        shutil.rmtree(incoming, ignore_errors=True)  # whatever is left of the copy made above
    log.info("brought everything over from %s", old)
    return True


def _leave_program(root: Path) -> Callable[[str, list[str]], list[str]]:
    def ignore(folder: str, names: list[str]) -> list[str]:
        return [n for n in names if n in PROGRAM] if Path(folder) == root else []

    return ignore


# ---------------------------------------------------------------------------- the Mac app
def rename_plan(argv: list[str], pid: int | None = None) -> update.Plan | None:
    """Saldo running as …/Cobro.app: a helper renames it Saldo.app once Saldo has quit, then opens it. If a
    Saldo.app is already there, that one opens (and puts this copy away, see leftovers()). None when there's
    nothing to rename."""
    if KEEP_NAME in argv or update.install_kind() != "mac-app":
        return None
    app = update.app_bundle()
    if app is None or app.name != OLD_APP or not os.access(app.parent, os.W_OK):
        return None
    new = app.with_name(NEW_APP)
    q = update._q
    lines = [
        f"if [ -e {q(new)} ]; then open {q(new)}",
        f"elif mv {q(app)} {q(new)}; then open {q(new)}",
        f"else open {q(app)} --args {KEEP_NAME}; fi",
    ]
    return update._posix_script(update.new_work_folder(), pid or os.getpid(), lines)


def leftovers() -> list[Path]:
    """The old Cobro.app on this Mac (next to Saldo.app, or in Applications), when Saldo runs as Saldo.app."""
    if update.install_kind() != "mac-app":
        return []
    me = update.app_bundle()
    if me is None or me.name == OLD_APP:
        return []
    places = {me.parent / OLD_APP, Path("/Applications") / OLD_APP, Path.home() / "Applications" / OLD_APP}
    return sorted(p for p in places if p != me and is_ours(p))


def is_ours(app: Path) -> bool:
    """A Cobro.app this app made (its bundle id says so), never another app that happens to share the name."""
    try:
        with (app / "Contents" / "Info.plist").open("rb") as f:
            info = plistlib.load(f)
    except (OSError, ValueError, ExpatError):
        return False
    return isinstance(info, dict) and info.get("CFBundleIdentifier") in BUNDLE_IDS
