"""Making, copying, deleting and editing invoices, clients and profiles.

A part of MainWindow (see main_window.py); it uses the window's widgets and the library."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt

from saldo.core.log import get_logger
from saldo.core.model import Business, Client, Invoice, now_iso
from saldo.ui.dialogs.client import ClientDialog
from saldo.ui.dialogs.common import confirm
from saldo.ui.dialogs.profile import ProfileDialog

log = get_logger(__name__)


def _blank(inv: Invoice) -> dict:
    """What a new invoice holds, to tell whether you've changed it."""
    d = inv.to_dict()
    d.pop("updated", None)
    return d


class EditingMixin:
    # ------------------------------------------------------------------ new, duplicate, delete
    def new_invoice(self) -> None:
        b = self.business()
        if b is None:
            self.edit_business(True)
            return
        self.flush()
        inv = self.lib.new_invoice(b)
        if self.view_key not in ("all", "drafts"):
            self.go("drafts")
        self.search.clear()
        self.view_menu.clear()  # a filter could hide the new invoice
        self.refresh()
        self.open(inv.id)
        self.panel.client.setFocus()
        self._fresh = (inv.id, _blank(inv))

    def _drop_fresh(self, keep: str = "") -> None:
        """A new invoice you left without filling anything in (Esc, or opening something else) isn't kept."""
        fresh, self._fresh = self._fresh, None
        if fresh is None:
            return
        inv_id, before = fresh
        if inv_id == keep:
            self._fresh = fresh
            return
        inv = self.lib.invoices.get(inv_id)
        if inv is None or _blank(inv) != before:
            return
        self._dirty.discard(inv_id)
        self.lib.delete_invoice(inv_id)
        self.panel.inv = None
        self.dock.set_open(False)
        self.refresh()

    def _duplicate_current(self) -> None:
        if self.panel.inv is not None and self.dock.opened:
            self.duplicate(self.panel.inv.id)

    def duplicate(self, inv_id: str) -> None:
        self.flush()
        src = self.lib.invoices.get(inv_id)
        if src is None:
            return
        copy = self.lib.duplicate(src)
        self.refresh()
        self.open(copy.id)
        self.toast(f"Made {copy.number} from {src.number}.", "done")

    def delete_invoices(self, ids: list[str]) -> None:
        """Delete one invoice or many (⌘A, Shift or ⌘-click, then Delete), after an alert that names them."""
        picked = [self.lib.invoices[i] for i in ids if i in self.lib.invoices]
        if not picked:
            return
        self.flush()
        if len(picked) == 1:
            inv = picked[0]
            who = f" for {inv.client.name.strip()}" if inv.client.name.strip() else ""
            title = f"Delete {inv.number}?"
            text = f"The invoice{who} goes from Saldo. PDFs you already saved stay where they are."
            action = "Delete"
        else:
            names = [i.number for i in picked]
            listed = ", ".join(names[:3]) + (f" and {len(names) - 3} more" if len(names) > 3 else "")
            title = f"Delete {len(picked)} invoices?"
            text = f"{listed}. PDFs you already saved stay where they are."
            action = f"Delete {len(picked)}"
        if not confirm(self, title, text, action):
            return
        for inv in picked:
            self._dirty.discard(inv.id)
            self.lib.delete_invoice(inv.id)
            log.info("deleted invoice %s", inv.number)
        if self.panel.inv is not None and self.panel.inv.id in {i.id for i in picked}:
            self.panel.inv = None
        self.go(self.view_key)
        self.toast("Deleted it." if len(picked) == 1 else f"Deleted {len(picked)} invoices.", "done")

    # ------------------------------------------------------------------ edits
    def _invoice_edited(self, inv: Invoice) -> None:
        inv.updated = now_iso()
        self._dirty.add(inv.id)
        self._save_timer.start()
        self._table_timer.start()
        self._draw_timer.start()

    def flush(self) -> None:
        """Write anything edited, now."""
        try:
            cp = self.client_panel
            if self._dirty_client and cp.c is not None and cp.can_save():
                self.lib.save_client(cp.c)  # drafts billed to them follow
                if cp.fresh:  # kept now: it gets its row, and can have invoices
                    cp.kept()
                    self._table_timer.start()
            self._dirty_client = False
            if self._dirty_businesses:
                self.lib.save_businesses()
                self._dirty_businesses = False
            for inv_id in list(self._dirty):
                inv = self.lib.invoices.get(inv_id)
                if inv is not None:
                    self.lib.save_invoice(inv)
                self._dirty.discard(inv_id)
        except OSError:
            log.warning("couldn't save", exc_info=True)
            self.toast("Couldn't save. Check that there's free space on this computer.", "problem")
        if self.history is not None:
            self.history.mark()

    def _groups_changed(self, key: str, state: dict) -> None:
        groups = self.lib.settings.get("groups", {})
        groups = groups if isinstance(groups, dict) else {}
        groups[key] = state
        self.lib.settings["groups"] = groups

    # ------------------------------------------------------------------ clients
    def new_client(self) -> None:
        """A new client in All Clients, on the right: kept once it has a name (until then, nothing's saved)."""
        if not self.on_clients():
            self.go("clients")
        self.flush()
        t = self.client_table  # nothing picked in the table: this one isn't there yet
        t._quiet = True
        t.clearSelection()
        t.setCurrentItem(None)
        t._quiet = False
        self.sidebar.select("clients")
        self.client_panel.load(Client(), fresh=True)
        self.inspector.setCurrentWidget(self.client_panel)
        self.dock.set_open(True)
        self.client_panel.name.setFocus()

    def open_client(self, client_id: str) -> None:
        """Open a saved client on the right (moving to All Clients if needed)."""
        c = self.lib.clients.get(client_id)
        if c is None:
            self.toast("That's been deleted.")
            return
        cp = self.client_panel
        if cp.c is not None and cp.c.id == c.id and self.dock.opened and self.inspector.currentWidget() is cp:
            return
        self.flush()
        self._drop_fresh()
        if not self.on_clients():
            self._set_place("clients")
            self.refresh()
        elif c.id not in {r.data(0, Qt.ItemDataRole.UserRole) for r in self.client_table.showing_rows()}:
            self.search.clear()
        self.client_table.select_id(c.id)
        cp.load(c)
        self.inspector.setCurrentWidget(cp)
        self.sidebar.select(f"client:{c.id}" if f"client:{c.id}" in self.sidebar.rows else "clients")
        self.dock.set_open(True)

    def save_new_client(self) -> None:
        """Save Client, under a new client: kept now (and in the table and the sidebar), then New Invoice."""
        cp = self.client_panel
        if cp.c is None or not cp.can_save():
            return
        self._dirty_client = True
        self.flush()
        cp.saved()
        self.refresh()
        self.toast(f"Saved {cp.c.name}.", "done")

    def _client_edited(self, _c: Client) -> None:
        self._dirty_client = True
        self._save_timer.start()
        self._table_timer.start()
        self._draw_timer.start()  # an open page billed to them (a draft) follows

    def delete_client(self, client_id: str) -> None:
        """Take a client off your list, after an alert. Every invoice keeps its own copy of them."""
        cp = self.client_panel
        if cp.c is not None and cp.c.id == client_id and cp.fresh:  # never kept: nothing to delete
            self.deselect()
            return
        self.flush()
        c = self.lib.clients.get(client_id)
        if c is None:
            return
        if not confirm(
            self,
            f"Delete {c.name}?",
            f"{c.name} will be taken off your clients. Invoices you already made keep their details.",
            "Delete Client",
        ):
            return
        self.lib.delete_client(client_id)
        log.info("deleted a client")
        if cp.c is not None and cp.c.id == client_id and self.inspector.currentWidget() is cp:
            self._inspector_empty()
        self.refresh()
        self.toast(f"Deleted {c.name}. Invoices you already made keep their details.", "done")

    def new_invoice_for(self, client_id: str) -> None:
        """New Invoice for a client (their panel, or a right-click): a new invoice billed to them."""
        c = self.lib.clients.get(client_id)
        if c is None:
            return
        self.new_invoice()
        if self.panel.inv is None or self.inspector.currentWidget() is not self.panel:
            return  # no profile yet: the profile came first
        self.panel.use_client(c)
        self.flush()
        self._fresh = (self.panel.inv.id, _blank(self.panel.inv))  # still goes if you leave it untouched

    def edit_client(self, new: bool) -> None:
        """New Client… or Edit… under Bill To: the saved client goes on the open invoice, and drafts billed
        to them follow the change (sent and paid invoices keep what they said)."""
        inv = self.panel.inv if self.dock.opened else None
        current = None
        saved = None
        if not new and inv is not None:
            saved = self.lib.match_client(inv.client)
            current = replace(inv.client, id=saved.id) if saved else inv.client
        per_client = any(b.number_style != "year" for b in self.lib.businesses.values())
        d = ClientDialog(current, self.lib, saved is not None, per_client, parent=self)
        if d.exec() != ClientDialog.DialogCode.Accepted:
            return
        self.flush()
        if d.deleted:
            self.lib.delete_client(d.client.id)
            log.info("deleted a client")
            self.toast(f"Deleted {d.client.name}. Invoices you already made keep their details.", "done")
            if inv is not None:
                self.panel.refresh_clients()
        else:
            client = self.lib.save_client(d.client)
            if inv is not None:
                self.panel.use_client(client)  # saves through changed
            else:
                self.toast(f"Saved {client.name}. Pick them under Bill To.", "done")
        self.refresh()

    # ------------------------------------------------------------------ profiles
    def _on_invoice(self) -> bool:
        return self.panel.inv is not None and self.dock.opened

    def edit_business(self, add: bool) -> None:
        """Your profile, in Settings › Profiles (a new one when `add`, or the one the open invoice uses)."""
        first = not self.lib.businesses
        start = None
        if not add:
            b = self.panel.current_business() if self._on_invoice() else self.business()
            start = b.id if b is not None else None
        self.open_settings("profiles", profile=start, add_profile=add, for_invoice=add and self._on_invoice())
        if first and self.lib.businesses:
            self.new_invoice()
        elif self.panel.inv is not None:
            self.panel.refresh_businesses()

    def profile_start(self, b_id: str | None) -> tuple[Business | None, Business, bool]:
        """For the profile editor: (the saved profile or None for a new one, what the form starts with,
        whether it can be deleted)."""
        current = self.lib.businesses.get(b_id) if b_id else None
        can_delete = (
            current is not None
            and len(self.lib.businesses) > 1
            and not any(i.business_id == current.id for i in self.lib.invoices.values())
        )
        return current, current or Business(), can_delete

    def profile_saved(self, d: ProfileDialog, current: Business | None, for_invoice: bool = False) -> str:
        """The profile editor saved (or deleted): keep it, and show it everywhere. Returns the profile's id."""
        self.flush()
        if d.deleted and current is not None:
            self.lib.delete_business(current.id)
            self.refresh()
            return ""
        b = d.business
        if current is None:
            self.lib.add_business(b)
            log.info("added a profile")
        else:
            self.lib.businesses[b.id] = b
            self.lib.save_businesses()
        self.lib.settings["business"] = b.id
        if self._on_invoice():
            inv = self.panel.inv
            if for_invoice and current is None:
                inv.business_id = b.id
            if inv.business_id == b.id:
                if self.lib.renumber(inv):  # new letters or number style: an untouched draft follows
                    self._dirty.add(inv.id)
                self.flush()
                self.panel.load(inv)
        self.refresh()
        self.redraw()
        return b.id

    def use_business(self, b_id: str) -> None:
        """Work as another of your profiles (new invoices start from it)."""
        if b_id in self.lib.businesses:
            self.lib.settings["business"] = b_id
            self.lib.save_settings()
            self.refresh()

    def _defaults_saved(self, b: Business) -> None:
        self._dirty_businesses = True
        self.flush()
        self.toast(f"New invoices from {b.name} will start with this payment text and terms.", "done")
