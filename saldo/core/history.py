"""Undo and redo for what you keep in Saldo: invoices, clients and profiles.

The window calls mark() whenever things settle (after a save or a refresh). If anything changed since the last
mark, the state before it becomes one undo step. Undo puts that state back and saves it. A change that's taken
straight back (a new invoice dropped before you filled it in) leaves no step behind.

Window things (what's open, folded, the look) aren't undone; neither are app settings. No Qt here.
"""

from __future__ import annotations

from typing import Any

from saldo.core.model import Business, Client, Invoice

LIMIT = 100  # steps kept

State = dict[str, Any]


def state_of(lib) -> State:
    invoices = {}
    for inv_id, inv in lib.invoices.items():
        d = inv.to_dict()
        d.pop("updated", None)  # saving stamps the time; that alone isn't a change
        invoices[inv_id] = d
    return {
        "invoices": invoices,
        "clients": [c.to_dict() for c in lib.clients.values()],
        "businesses": [b.to_dict() for b in lib.businesses.values()],
    }


PARTS = [("invoices", "invoices"), ("clients", "clients"), ("businesses", "profiles")]  # (key, for a toast)


def describe(a: State, b: State) -> str:
    """What differs between two states, in a few words: "invoices", "invoices and clients"."""
    parts = [words for key, words in PARTS if a.get(key) != b.get(key)]
    if not parts:
        return "a change"
    if a["invoices"] != b["invoices"] and len(a["invoices"]) != len(b["invoices"]):
        n = abs(len(a["invoices"]) - len(b["invoices"]))
        parts[parts.index("invoices")] = f"{n} invoice{'s' if n != 1 else ''}"
    elif parts[0] == "invoices":
        changed = [k for k in a["invoices"] if a["invoices"][k] != b["invoices"].get(k)]
        if len(changed) == 1:
            parts[0] = a["invoices"][changed[0]].get("number") or "an invoice"
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


class History:
    def __init__(self, lib):
        self.lib = lib
        self.undos: list[State] = []
        self.redos: list[State] = []
        self.last = state_of(lib)

    def mark(self) -> bool:
        """Note where things stand. True if that made a new undo step."""
        now = state_of(self.lib)
        if now == self.last:
            return False
        if self.undos and self.undos[-1] == now:  # taken straight back: no step either way
            self.undos.pop()
            self.last = now
            return False
        self.undos.append(self.last)
        del self.undos[:-LIMIT]
        self.redos.clear()
        self.last = now
        return True

    def can_undo(self) -> bool:
        return bool(self.undos) or state_of(self.lib) != self.last

    def can_redo(self) -> bool:
        return bool(self.redos)

    def undo(self) -> str | None:
        """Go back one step; what changed back (for a toast), or None if there's nothing to undo."""
        self.mark()
        if not self.undos:
            return None
        before = self.undos.pop()
        self.redos.append(self.last)
        what = describe(self.last, before)
        self._put(before)
        return what

    def redo(self) -> str | None:
        if not self.redos:
            return None
        self.mark()  # (nothing new can have happened since an undo without clearing redos)
        if not self.redos:
            return None
        after = self.redos.pop()
        self.undos.append(self.last)
        what = describe(self.last, after)
        self._put(after)
        return what

    def _put(self, s: State) -> None:
        """Make the library this state, and save it (only the invoices that differ are written)."""
        lib = self.lib
        lib.clients = {d["id"]: Client.from_dict(d) for d in s["clients"]}
        lib.businesses = {d["id"]: Business.from_dict(d) for d in s["businesses"]}
        old = state_of(lib)["invoices"] if lib.invoices else {}
        for inv_id in list(lib.invoices):
            if inv_id not in s["invoices"]:
                lib.delete_invoice(inv_id)
        for inv_id, d in s["invoices"].items():
            if old.get(inv_id) != d:
                inv = Invoice.from_dict(d)
                lib.invoices[inv.id] = inv
                lib.save_invoice(inv)
        lib.save_clients()
        lib.save_businesses()
        self.last = state_of(lib)
