"""The AI helpers in the window: the assistant, its job, the Review window and applying what you approve.

The assistant works on the invoice you last opened (its line items' wording only).
A part of MainWindow (see main_window.py); it uses the window's widgets and the library."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog

from saldo.core.model import Invoice
from saldo.services.ai import tasks
from saldo.services.ai.providers import Setup
from saldo.ui.components.worker import Worker
from saldo.ui.dialogs.ai_review import ReviewDialog
from saldo.ui.panels.assistant import JOBS, AssistantPanel

RUNS = {"tidy": tasks.tidy_items}


class AIMixin:
    assistant: AssistantPanel

    def _build_assistant(self) -> AssistantPanel:
        """The assistant panel (made once, with the window; it shares the right-hand glass with the invoice)."""
        a = AssistantPanel()
        a.job_wanted.connect(lambda key: self.ai_job(key))
        a.setup_wanted.connect(self.open_ai_setup)
        a.close_wanted.connect(self.close_assistant)
        a.changes_found.connect(lambda result: self._ai_review("Suggested Changes", result))
        a.ask_job = self._ai_question
        return a

    def ai_setup(self) -> Setup:
        return Setup.from_settings(self.lib.settings)

    def open_ai_setup(self) -> None:
        self.open_settings("ai")

    def assistant_showing(self) -> bool:
        return self.inspector.currentWidget() is self.assistant and self.dock.opened

    def toggle_assistant(self) -> None:
        if self.assistant_showing():
            self.close_assistant()
        else:
            self.open_ai_assistant()

    def close_assistant(self) -> None:
        self.dock.set_open(False)

    def open_ai_assistant(self, job: str = "") -> None:
        self.flush()
        self._drop_fresh(keep=self.panel.inv.id if self.panel.inv is not None else "")
        self._ai_state()
        self.inspector.setCurrentWidget(self.assistant)
        self.dock.set_open(True)
        if job:
            self.ai_job(job)
        else:
            self.assistant.question.setFocus()

    def _ai_invoice(self) -> Invoice | None:
        """The invoice the assistant works on: the one you last opened (if it's still there)."""
        inv = self.panel.inv
        return inv if inv is not None and inv.id in self.lib.invoices else None

    def _ai_question(self):
        """What a question needs, gathered now on the window's thread: (question) -> answer, to run later."""
        setup = self.ai_setup()
        inv = self._ai_invoice()
        copy = Invoice.from_dict(inv.to_dict()) if inv is not None else None
        return lambda q: tasks.chat(setup, q, copy)

    def _ai_scope(self) -> str:
        inv = self._ai_invoice()
        if inv is None:
            return "Open an invoice to work on its line items."
        n = sum(1 for it in inv.items if not it.is_blank())
        return f"On {inv.number or 'this invoice'}: {n} line item{'s' if n != 1 else ''}."

    def _ai_state(self) -> None:
        self.assistant.show_setup(self.ai_setup(), self._ai_scope())
        if self._ai_invoice() is None:
            for b in self.assistant.job_buttons.values():
                b.setEnabled(False)

    def ai_job(self, key: str) -> None:
        setup = self.ai_setup()
        if not setup.ready():
            self.open_ai_setup()
            setup = self.ai_setup()
            if not setup.ready():
                return
        if not self.assistant_showing():
            self.open_ai_assistant()
        inv = self._ai_invoice()
        if self.assistant.running() or inv is None:
            return
        self.flush()
        copy = Invoice.from_dict(inv.to_dict())  # the job reads its own copy while you keep working
        run = RUNS[key]
        title = dict((k, label) for k, label, _t in JOBS)[key]
        w = Worker(lambda progress, cancel: run(setup, copy, progress, cancel), self)
        w.done.connect(lambda result: self._ai_review(title, result))
        w.failed.connect(lambda e: self.assistant.say("Saldo", e))
        self.assistant.start(w, f"{title}…")

    def _ai_review(self, title: str, result: tasks.Result) -> None:
        if not result.changes:
            msg = result.problems[0] if result.problems else "Everything already reads well."
            self.assistant.say("Saldo", f"{title}: {msg}")
            return
        inv = self.lib.invoices.get(result.changes[0].invoice_id)
        names = (
            {n: it.description.strip() or f"Line {n + 1}" for n, it in enumerate(inv.items)} if inv else {}
        )
        d = ReviewDialog(title, result, names, self)
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        self.flush()
        n = tasks.apply(self.lib, d.chosen())
        if self.panel.inv is not None and self.panel.inv.id in self.lib.invoices:
            self.panel.load(self.panel.inv)
            self._draw_timer.start()
        self.refresh()
        self.toast(f"Updated {n} line item{'s' if n != 1 else ''}. Undo (⌘Z) takes it back.", "done")
