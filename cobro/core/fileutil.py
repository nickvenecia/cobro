"""Showing a file in Finder / Explorer / the Linux file manager."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from cobro.core.log import get_logger

log = get_logger(__name__)


def popen_kwargs() -> dict:
    """Keeps Windows from flashing a console window."""
    if sys.platform == "win32":
        return {"creationflags": 0x08000000}  # CREATE_NO_WINDOW
    return {}


def reveal(path: str | Path) -> None:
    """Open the folder with this file selected (Linux: just the folder)."""
    path = str(path)
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path])
        elif sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)], **popen_kwargs())
        else:
            target = path if os.path.isdir(path) else os.path.dirname(path)
            subprocess.Popen(["xdg-open", target])
    except OSError:
        log.warning("couldn't show %s", path, exc_info=True)
