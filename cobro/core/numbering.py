"""Invoice numbers: PREFIX-YEAR-001, counting up per prefix and year."""

from __future__ import annotations

import re
from collections.abc import Iterable

_SMALL = {"and", "of", "the", "a", "an", "&", "de", "la", "el", "los", "las", "y"}


def initials(name: str) -> str:
    """ "Nicholas Venecia" -> "NV"; "Dopamine Productions" -> "DP"; one word -> its first 3 letters."""
    words = [w for w in re.findall(r"[A-Za-z0-9]+", name) if w.lower() not in _SMALL]
    if not words:
        return "INV"
    if len(words) == 1:
        return words[0][:3].upper()
    return "".join(w[0] for w in words[:3]).upper()


def clean_prefix(prefix: str) -> str:
    """Letters, digits and dashes only, so numbers stay safe in file names."""
    p = re.sub(r"[^A-Za-z0-9-]", "", prefix).strip("-").upper()
    return p or "INV"


def next_number(prefix: str, existing: Iterable[str], year: int) -> str:
    """The next free number for this prefix and year: NV-2026-001, then NV-2026-002…"""
    prefix = clean_prefix(prefix)
    head = f"{prefix}-{year}-"
    highest = 0
    width = 3
    for n in existing:
        if n.upper().startswith(head.upper()):
            tail = n[len(head) :]
            if tail.isdigit():
                highest = max(highest, int(tail))
                width = max(width, len(tail))
    return f"{head}{highest + 1:0{width}d}"
