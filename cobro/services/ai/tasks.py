"""The AI jobs. Each returns suggested Changes; nothing is changed until you approve them in the app.

tidy_items  the line items of one invoice, said clearly: names in Title Case and spelled right, details short
            and plain. Nothing is made up and no line is added or removed
chat        a question or a request about one invoice's line items ("put the details in Spanish", "is anything
            spelled wrong?"): an answer, and any wording it asked for as suggestions

Only the line items' words (and how many of each) are sent: never amounts, the client, the project or your
profile. The AI's answer must fit a strict shape (only the name and the details, plain text, sane lengths) and
you review it all. Approved changes keep a copy of the invoice first (Library.snapshot).
"""

from __future__ import annotations

import threading
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

from cobro.core.model import Invoice
from cobro.services.ai.providers import AIError, Setup, ask, ask_json, read_json

LIMITS = {"description": 120, "details": 500}
LINES = {"description": 1, "details": 6}  # how many lines each may have
FIELD_LABELS = {"description": "Name", "details": "Details"}
MAX_ITEMS = 200  # line items described in one question


@dataclass
class Change:
    invoice_id: str
    line: int  # the line item's place on the invoice (0 is the first)
    field: str  # description or details
    old: str
    new: str

    @property
    def label(self) -> str:
        return FIELD_LABELS.get(self.field, self.field)


@dataclass
class Result:
    changes: list[Change]
    problems: list[str]  # what couldn't be done, in plain words


Progress = Callable[[int, int], None]


# ---------------------------------------------------------------- checking what comes back
def clean_text(value, limit: int, lines: int = 1) -> str:
    """Plain text of at most `limit` characters and `lines` lines (no control characters; spaces tidied)."""
    if not isinstance(value, (str, int, float)):
        return ""
    rows = []
    for row in str(value).replace("\r\n", "\n").split("\n"):
        s = "".join(" " if unicodedata.category(ch)[0] == "C" else ch for ch in row)
        s = " ".join(s.split())
        if s:
            rows.append(s)
    return "\n".join(rows[:lines] if lines > 1 else [" ".join(rows)])[:limit].strip()


def _change(inv: Invoice, n: int, field: str, new: str) -> Change | None:
    old = getattr(inv.items[n], field)
    if not new or new == old.strip():
        return None
    return Change(inv.id, n, field, old, new)


def items_text(inv: Invoice) -> str:
    """The invoice's line items as plain numbered lines (their words only: no amounts, no client)."""
    rows = []
    for n, it in enumerate(inv.items[:MAX_ITEMS]):
        if it.is_blank():
            continue
        details = " / ".join(x.strip() for x in it.details.splitlines() if x.strip())
        rows.append(f"{n}. name: {it.description.strip()} | details: {details} | qty: {it.qty.strip()}")
    return "\n".join(rows)


def _read_changes(inv: Invoice, rows) -> list[Change]:
    out: list[Change] = []
    for row in rows if isinstance(rows, list) else []:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("n"), int)
            or not 0 <= row["n"] < len(inv.items)
        ):
            continue
        if inv.items[row["n"]].is_blank():
            continue
        fields = {"description": row.get("name"), "details": row.get("details")}
        if "field" in row:  # the chat's shape: one field at a time
            fields = {
                {"name": "description", "details": "details"}.get(str(row.get("field")), ""): row.get("value")
            }
        for field, value in fields.items():
            if field not in LIMITS or value is None:
                continue  # nothing else can be changed (never an amount)
            new = clean_text(value, LIMITS[field], LINES[field])
            if field == "details" and inv.items[row["n"]].details.strip() and not new:
                continue  # never blank out details you wrote
            c = _change(inv, row["n"], field, new)
            if c and not any(x.line == c.line and x.field == c.field for x in out):
                out.append(c)
    return out


# ---------------------------------------------------------------- the jobs
WORDING = (
    "These are the line items of an invoice from a freelance filmmaker (directing, cinematography, editing, "
    "color grading and the like). Names are short, in Title Case, spelled right, like 'Production Day' or "
    "'Color Grade'. Details are one or two plain sentences or a short list saying what was done, in the same "
    "language as the invoice. Keep every fact (dates, hours, what's included); never invent anything, never "
    "mention money or prices."
)


def tidy_items(
    setup: Setup,
    inv: Invoice,
    progress: Progress = lambda _n, _t: None,
    cancel: threading.Event | None = None,
) -> Result:
    """The line items said clearly. Returns suggestions for their names and details."""
    listing = items_text(inv)
    if not listing:
        return Result([], ["This invoice has no line items to tidy yet."])
    progress(0, 1)
    try:
        got = ask_json(
            setup,
            "You tidy up the wording of invoice line items. "
            + WORDING
            + " If a line already reads well, give it back unchanged. "
            'Reply as [{"n": 0, "name": "...", "details": "..."}, ...] with one entry per line.',
            f"<items>\n{listing}\n</items>",
        )
    except AIError as e:
        return Result([], [str(e)])
    if cancel is not None and cancel.is_set():
        return Result([], [])
    progress(1, 1)
    return Result(_read_changes(inv, got), [])


def chat(setup: Setup, message: str, inv: Invoice | None) -> tuple[str, Result]:
    """A question or a request about the invoice's line items. Returns the answer, and the changes asked for
    (as suggestions to review)."""
    q = clean_text(message, 2000)
    if not q:
        raise AIError("Ask a question first.")
    listing = items_text(inv) if inv is not None else ""
    text = ask(
        setup,
        "You're the assistant inside Cobro, an invoice app for freelance filmmakers. "
        + (
            "Below are the line items of the invoice that's open, numbered: name | details | qty. "
            if listing
            else "No invoice is open, so there are no line items to look at. "
        )
        + "Answer briefly and plainly. "
        + WORDING
        + " When asked to change the wording, you may only change a line's name or its details. You can't "
        "change amounts, rates, dates, the client or anything else, and you can't add or remove lines: say so "
        'if asked. Always reply as JSON: {"reply": "what you say to the person", "changes": [{"n": 0, '
        '"field": "details", "value": "..."}]}, with an empty changes list when nothing should change.',
        (f"<items>\n{listing}\n</items>\n\n" if listing else "") + f"Message: {q}",
    )
    got = read_json(text)
    if not isinstance(got, dict):  # it just talked: that's the answer
        return text.strip(), Result([], [])
    reply = clean_text(got.get("reply") or "", 4000, 40)
    out = _read_changes(inv, got.get("changes")) if inv is not None else []
    return reply or ("Here's what I'd change." if out else "Done."), Result(out, [])


def apply(lib, changes: list[Change]) -> int:
    """Make the approved changes (a copy of each invoice is kept first: Library.snapshot). Returns how many.
    A line you edited while the AI was working keeps your edit."""
    by_invoice: dict[str, list[Change]] = {}
    for c in changes:
        by_invoice.setdefault(c.invoice_id, []).append(c)
    n = 0
    for inv_id, todo in by_invoice.items():
        inv = lib.invoices.get(inv_id)
        if inv is None:
            continue
        lib.snapshot("before-ai", [inv_id])
        changed = False
        for c in todo:
            if c.field not in LIMITS or not 0 <= c.line < len(inv.items):
                continue
            item = inv.items[c.line]
            if getattr(item, c.field) != c.old:  # you edited it (or moved lines) while the job ran
                continue
            new = clean_text(c.new, LIMITS[c.field], LINES[c.field])
            if not new:
                continue
            setattr(item, c.field, new)
            n += 1
            changed = True
        if changed:
            lib.save_invoice(inv)
    return n
