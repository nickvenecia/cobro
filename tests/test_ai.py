"""The AI layer, with a pretend provider (no internet, no keys spent): providers, keys, the jobs and the window.

What matters most: only line items' words are ever sent (never amounts, the client or the project), only a
line's name and details can change, nothing changes before you approve it, and a copy is kept first."""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

from cobro.core import sample, web
from cobro.core.model import LineItem
from cobro.core.store import Library
from cobro.services import secrets
from cobro.services.ai import providers, tasks
from cobro.services.ai.providers import AIError, Setup


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def provider(monkeypatch, keychain):
    """A pretend provider: records each request, answers with whatever `replies` holds next."""
    seen, replies = [], []

    def open_(req, timeout, **_k):
        seen.append(req)
        return FakeResponse(json.dumps(replies.pop(0)).encode())

    monkeypatch.setattr(web, "open_no_redirect", open_)
    providers.save_key("anthropic", "sk-ant-secret")
    providers.save_key("kimi", "sk-kimi-secret")
    return seen, replies


def anthropic_reply(text):
    return {"content": [{"type": "text", "text": text}]}


def openai_reply(text):
    return {"choices": [{"message": {"content": text}}]}


def an_invoice():
    inv = sample.invoice()
    inv.items = [
        LineItem("production day", "shoot day, directing + camera", "2", "1500"),
        LineItem("Color Grade", "", "1", "800"),
        LineItem(),  # an empty line is never sent
    ]
    return inv


# ---------------------------------------------------------------- keys
def test_keys_live_in_the_keychain_not_settings(keychain):
    providers.save_key("openai", "  sk-123  ")
    assert keychain.store[("Cobro", "ai:openai")] == "sk-123"
    settings = {}
    Setup("openai", "gpt-x").to_settings(settings)
    assert "sk-123" not in json.dumps(settings)
    providers.save_key("openai", "")
    assert providers.key_for("openai") == ""


def test_no_keychain_means_no_saving(monkeypatch):
    def none():
        raise secrets.SecretsUnavailable("no keychain")

    monkeypatch.setattr(secrets, "_keyring", none)
    with pytest.raises(secrets.SecretsUnavailable):
        secrets.put("ai:openai", "sk")
    assert secrets.get("ai:openai") == ""


# ---------------------------------------------------------------- providers
def test_every_provider_has_an_address_and_kind():
    for p in providers.PROVIDERS.values():
        assert p.kind in ("anthropic", "openai")
        assert p.key == "custom" or p.base_url.startswith("https://")
    assert {
        "anthropic",
        "openai",
        "gemini",
        "kimi",
        "kimi-cn",
        "openrouter",
        "deepseek",
        "mistral",
        "xai",
        "groq",
    } < set(providers.PROVIDERS)


def test_addresses_must_be_https_except_this_computer():
    assert providers.check_address("https://api.example.com/v1/") == "https://api.example.com/v1"
    assert providers.check_address("http://localhost:11434/v1")
    assert providers.check_address("http://127.0.0.1:1234/v1")
    for bad in ("http://api.example.com/v1", "ftp://x", "file:///etc", "javascript:x"):
        with pytest.raises(AIError):
            providers.check_address(bad)
    for bad in ("https://[x", "https://user@evil.com/v1", "https://api.example.com:99999/v1"):
        with pytest.raises(AIError):
            providers.check_address(bad)


def test_anthropic_request_shape_and_answer(provider):
    seen, replies = provider
    replies.append(anthropic_reply("Hi"))
    assert providers.ask(Setup("anthropic", "model-x"), "sys", "hello") == "Hi"
    req = seen[0]
    assert req.full_url == "https://api.anthropic.com/v1/messages"
    assert req.get_header("X-api-key") == "sk-ant-secret" and req.get_header("Anthropic-version")
    body = json.loads(req.data)
    assert (
        body["model"] == "model-x" and body["system"] == "sys" and body["messages"][0]["content"] == "hello"
    )


def test_kimi_speaks_openai(provider):
    seen, replies = provider
    replies.append(openai_reply("Hola"))
    assert providers.ask(Setup("kimi", "kimi-x"), "sys", "hello") == "Hola"
    assert seen[0].full_url == "https://api.moonshot.ai/v1/chat/completions"
    assert seen[0].get_header("Authorization") == "Bearer sk-kimi-secret"


def test_models_come_from_the_provider(provider):
    _seen, replies = provider
    replies.append(
        {"data": [{"id": "models/gemini-a"}, {"id": "text-embedding-3"}, {"id": "whisper-1"}, {"id": "b"}]}
    )
    assert providers.list_models(Setup("kimi")) == ["gemini-a", "b"]


def test_errors_are_plain_and_never_show_the_key(monkeypatch, keychain):
    providers.save_key("openai", "sk-very-secret")

    def refuse(req, timeout, **_k):
        body = io.BytesIO(json.dumps({"error": {"message": "Incorrect API key sk-very-secret"}}).encode())
        raise urllib.error.HTTPError(req.full_url, 401, "no", {}, body)

    monkeypatch.setattr(web, "open_no_redirect", refuse)
    with pytest.raises(AIError) as e:
        providers.ask(Setup("openai", "m"), "s", "u")
    assert "sk-very-secret" not in str(e.value) and "key" in str(e.value).lower()


def test_a_redirect_is_never_followed(monkeypatch, keychain):
    providers.save_key("openai", "sk")

    def moved(req, timeout, **_k):
        raise urllib.error.HTTPError(req.full_url, 302, "moved", {"Location": "https://evil.example"}, None)

    monkeypatch.setattr(web, "open_no_redirect", moved)
    with pytest.raises(AIError, match="redirects"):
        providers.list_models(Setup("openai"))


def test_a_local_model_is_reached_without_a_proxy(monkeypatch, keychain):
    seen = []

    def open_(req, timeout, direct=False):
        seen.append(direct)
        return FakeResponse(json.dumps({"data": [{"id": "llama"}]}).encode())

    monkeypatch.setattr(web, "open_no_redirect", open_)
    assert providers.list_models(Setup("custom", "", "http://localhost:11434/v1")) == ["llama"]
    assert seen == [True]


def test_json_answers_are_found_inside_chatter(provider):
    _seen, replies = provider
    replies.append(anthropic_reply('Sure! ```json\n[{"n": 0, "name": "X"}]\n``` hope that helps'))
    assert providers.ask_json(Setup("anthropic", "m"), "s", "u") == [{"n": 0, "name": "X"}]


def test_odd_answers_are_plain_errors(provider):
    _seen, replies = provider
    replies.append({"content": "not a list of parts"})
    with pytest.raises(AIError):
        providers.ask(Setup("anthropic", "m"), "s", "u")


# ---------------------------------------------------------------- the jobs
def test_tidy_suggests_only_changes_cleans_them_and_never_touches_money(provider):
    seen, replies = provider
    inv = an_invoice()
    answer = [
        {
            "n": 0,
            "name": "Production Day\u0007",
            "details": "Shoot day: directing and camera",
            "rate": "9999",
        },
        {"n": 1, "name": "Color Grade", "details": ""},  # unchanged, and no details made up
        {"n": 2, "name": "Invented Line"},  # the empty line: never filled in
        {"n": 7, "name": "Out of range"},
        "nonsense",
    ]
    replies.append(anthropic_reply(json.dumps(answer)))
    result = tasks.tidy_items(Setup("anthropic", "m"), inv)
    got = {(c.line, c.field): c.new for c in result.changes}
    assert got == {(0, "description"): "Production Day", (0, "details"): "Shoot day: directing and camera"}
    assert inv.items[0].description == "production day"  # nothing changed yet: it's only a suggestion
    sent = json.loads(seen[0].data)["messages"][0]["content"] + json.loads(seen[0].data)["system"]
    assert "production day" in sent and "1500" not in sent and "800" not in sent  # words only, no amounts
    assert inv.client.name not in sent and inv.project not in sent  # never the client or the project


def test_tidy_with_no_line_items_says_so(provider):
    inv = an_invoice()
    inv.items = [LineItem()]
    result = tasks.tidy_items(Setup("anthropic", "m"), inv)
    assert not result.changes and "no line items" in result.problems[0]


def test_chat_requests_become_changes_but_only_the_wording(provider):
    _seen, replies = provider
    inv = an_invoice()
    answer = {
        "reply": "Here they are in Spanish.",
        "changes": [
            {"n": 0, "field": "details", "value": "Día de rodaje: dirección y cámara"},
            {"n": 0, "field": "rate", "value": "1"},  # never an amount
            {"n": 1, "field": "qty", "value": "5"},
            {"n": 1, "field": "name", "value": "Etalonaje"},
        ],
    }
    replies.append(anthropic_reply(json.dumps(answer)))
    reply, result = tasks.chat(Setup("anthropic", "m"), "put them in Spanish", inv)
    assert reply == "Here they are in Spanish."
    assert {(c.line, c.field) for c in result.changes} == {(0, "details"), (1, "description")}


def test_chat_that_just_talks_is_an_answer(provider):
    _seen, replies = provider
    replies.append(anthropic_reply("Everything is spelled right."))
    reply, result = tasks.chat(Setup("anthropic", "m"), "any typos?", an_invoice())
    assert reply == "Everything is spelled right." and not result.changes


def test_applying_keeps_a_copy_first_and_your_edits_win(data_folder):
    lib = Library(data_folder)
    b = lib.add_business(sample.business())
    inv = lib.new_invoice(b)
    inv.items = [LineItem("production day", "", "1", "1500"), LineItem("edit", "", "1", "900")]
    lib.save_invoice(inv)
    changes = [
        tasks.Change(inv.id, 0, "description", "production day", "Production Day"),
        tasks.Change(inv.id, 1, "description", "edit", "Edit"),
    ]
    inv.items[1].description = "Edit (2 rounds)"  # you typed while the AI was working
    assert tasks.apply(lib, changes) == 1
    assert [i.description for i in inv.items] == ["Production Day", "Edit (2 rounds)"]
    assert inv.items[0].rate == "1500"
    copies = list((data_folder / "backups").glob(f"invoice-*-before-ai-{inv.id}.json"))
    assert (
        len(copies) == 1 and json.loads(copies[0].read_text())["items"][0]["description"] == "production day"
    )
    again = Library(data_folder).load().invoices[inv.id]
    assert again.items[0].description == "Production Day"


def test_clean_text_keeps_lines_for_details_only():
    assert tasks.clean_text("a\nb\u0000c  d", 100) == "a b c d"
    assert tasks.clean_text("one\n\ntwo\nthree", 100, 2) == "one\ntwo"
    assert tasks.clean_text({"x": 1}, 100) == "" and len(tasks.clean_text("x" * 500, 120)) == 120


# ---------------------------------------------------------------- the window
@pytest.fixture
def win(qapp, data_folder):
    from cobro.ui.window.main_window import MainWindow

    w = MainWindow(sample.fill(Library(data_folder).load()))
    w._restored = True
    w.show()
    yield w
    w.close()


def _wait(worker):
    from PySide6.QtWidgets import QApplication

    worker.wait(5000)
    QApplication.processEvents()
    QApplication.processEvents()


def _answer(monkeypatch, text):
    monkeypatch.setattr(
        web,
        "open_no_redirect",
        lambda req, timeout, **_k: FakeResponse(json.dumps(anthropic_reply(text)).encode()),
    )


def test_tidy_end_to_end_and_undo(win, monkeypatch):
    from cobro.ui.dialogs import ai_review

    providers.save_key("anthropic", "sk-test")
    Setup("anthropic", "test-model").to_settings(win.lib.settings)
    inv = win.lib.ordered()[0]
    win.open(inv.id)
    old = inv.items[0].description
    _answer(monkeypatch, json.dumps([{"n": 0, "name": old + " (Tidy)", "details": inv.items[0].details}]))
    picked = {}

    def approve(self):
        picked["n"] = len(self.chosen())
        return ai_review.ReviewDialog.DialogCode.Accepted

    monkeypatch.setattr(ai_review.ReviewDialog, "exec", approve)
    win.open_ai_assistant()
    assert win.assistant.job_buttons["tidy"].isEnabled() and inv.number in win.assistant.scope.text()
    win.ai_job("tidy")
    _wait(win.assistant.worker)
    assert picked["n"] == 1 and win.lib.invoices[inv.id].items[0].description == old + " (Tidy)"
    assert list((win.lib.root / "backups").glob("invoice-*.json"))
    win.setFocus()
    win.undo()  # one undo takes it back
    assert win.lib.invoices[inv.id].items[0].description == old


def test_jobs_need_setup_first(win, monkeypatch):
    asked = []
    monkeypatch.setattr(win, "open_settings", lambda pane="general", **_k: asked.append(pane))
    win.open(win.lib.ordered()[0].id)
    win.ai_job("tidy")
    assert asked == ["ai"]  # opened Settings › AI instead of running
    assert win.assistant.worker is None


def test_the_assistant_is_the_right_panel(win):
    win.toggle_assistant()
    assert win.assistant_showing() and win.dock.opened
    assert not win.assistant.job_buttons["tidy"].isEnabled()  # no invoice open yet
    win.go("unpaid")  # it stays while you move around
    assert win.assistant_showing()
    inv = win.lib.ordered()[0]
    win.open(inv.id)  # an invoice takes the panel
    assert win.inspector.currentWidget() is win.panel and not win.assistant_showing()
    win.toggle_assistant()  # and the chat comes back, working on that invoice
    assert win.assistant_showing() and inv.number in win.assistant.scope.text()
    win.toggle_assistant()
    assert not win.dock.opened


def test_ai_setup_saves_to_the_keychain_not_settings(win):
    from cobro.ui.dialogs.ai_setup import AISetupDialog

    d = AISetupDialog(win.lib, win)
    d.provider.setCurrentIndex(d.provider.findData("kimi"))
    d.key.setText("sk-kimi-abc")
    d.model.setEditText("kimi-model")
    d._save()
    assert providers.key_for("kimi") == "sk-kimi-abc"
    assert win.lib.settings["ai"] == {"provider": "kimi", "model": "kimi-model", "base_url": ""}
    assert "sk-kimi-abc" not in (win.lib.root / "settings.json").read_text()


def test_a_question_is_answered_as_plain_text(win, monkeypatch):
    providers.save_key("anthropic", "sk-test")
    Setup("anthropic", "test-model").to_settings(win.lib.settings)
    _answer(monkeypatch, "<b>Three</b> line items")
    win.open(win.lib.ordered()[0].id)
    win.open_ai_assistant()
    win.assistant.question.setText("how many line items?")
    win.assistant._ask()
    _wait(win.assistant.worker)
    assert "<b>Three</b> line items" in win.assistant.log.toPlainText()  # shown as typed, not as bold


def test_settings_has_an_ai_section(win):
    from cobro.ui.dialogs.settings import SettingsDialog

    d = SettingsDialog(win.lib, win, "ai")
    assert d.current_pane() == "ai" and d.windowTitle() == "AI"
    d.close()
