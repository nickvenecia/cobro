"""Invoice numbers: PREFIX-YEAR-001, counting up per prefix and year.

A profile can also count per client: the client's short code goes in the middle (RM-NRTH-2026-001),
or replaces the profile's letters (NRTH-2026-001). Each head (RM, RM-NRTH, NRTH) has its own count.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

_SMALL = {"and", "of", "the", "a", "an", "&", "de", "la", "el", "los", "las", "y"}


def initials(name: str) -> str:
    """ "Rosa Marquez" -> "RM"; "Mesquite Productions" -> "MP"; one word -> its first 3 letters."""
    words = [w for w in re.findall(r"[A-Za-z0-9]+", name) if w.lower() not in _SMALL]
    if not words:
        return "INV"
    if len(words) == 1:
        return words[0][:3].upper()
    return "".join(w[0] for w in words[:3]).upper()


def client_code(name: str) -> str:
    """ "Northwind Media" -> "NRTH": the first letter, then the consonants, four at most."""
    letters = re.sub(r"[^A-Za-z0-9]", "", name).upper()
    if not letters:
        return ""
    return (letters[0] + "".join(ch for ch in letters[1:] if ch not in "AEIOU"))[:4]


def clean_code(code: str) -> str:
    """A client code: letters and digits only, eight at most."""
    return re.sub(r"[^A-Za-z0-9]", "", code).upper()[:8]


def head(prefix: str, code: str, style: str) -> str:
    """What comes before the year: RM ("year"), RM-NRTH ("client") or NRTH ("client_only").
    Without a client code it's always the profile's own letters."""
    prefix, code = clean_prefix(prefix), clean_code(code)
    if code and style == "client":
        return f"{prefix}-{code}"
    if code and style == "client_only":
        return code
    return prefix


def clean_prefix(prefix: str) -> str:
    """Letters, digits and dashes only, so numbers stay safe in file names."""
    p = re.sub(r"[^A-Za-z0-9-]", "", prefix).strip("-").upper()
    return p or "INV"


def next_number(prefix: str, existing: Iterable[str], year: int) -> str:
    """The next free number for this prefix and year: RM-2026-001, then RM-2026-002…"""
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
