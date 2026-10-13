"""Moving in from Cobro, the app's old name (core/from_cobro.py, services/secrets.carry_over): every file and
key comes along the first time Saldo opens, Cobro's own are never touched, and Cobro.app becomes Saldo.app."""

from __future__ import annotations

import json
import os
import plistlib
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from saldo.core import from_cobro, paths, sample, update
from saldo.core.store import Library
from saldo.services import secrets


def _cobro_folder(folder: Path) -> Path:
    """A data folder as Cobro left it: a profile, clients, invoices, settings, a logo and its log."""
    sample.fill(Library(folder).load())
    (folder / "settings.json").write_text(
        json.dumps({"accent": "blue", "divide": "client"}), encoding="utf-8"
    )
    (folder / "logos").mkdir()
    (folder / "logos" / "a1b2.png").write_bytes(b"\x89PNG logo")
    (folder / "logs").mkdir()
    (folder / "logs" / "cobro.log").write_text("Cobro 2.0.0 starting", encoding="utf-8")
    return folder


def _files(folder: Path) -> dict[str, bytes]:
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob("*") if p.is_file()}


def test_everything_cobro_kept_comes_along_and_its_folder_is_left_as_it_was(tmp_path: Path):
    old = _cobro_folder(tmp_path / "Cobro")
    new = tmp_path / "Saldo"
    (new / "logs").mkdir(parents=True)
    (new / "logs" / "saldo.log").write_text("Saldo 2.1.0 starting", encoding="utf-8")  # opened a moment ago
    before = _files(old)

    assert from_cobro.copy_folder(old, new)

    assert _files(old) == before  # nothing in Cobro's folder moved or changed
    after = _files(new)
    for name, data in before.items():
        if not name.startswith("logs/"):
            assert after[name] == data, name
    assert after["logs/saldo.log"] == b"Saldo 2.1.0 starting"  # Saldo's own log stays
    assert not list(new.glob(".from-cobro-*"))
    was, now = Library(old).load(), Library(new).load()
    assert sorted(now.invoices) == sorted(was.invoices) and sorted(now.clients) == sorted(was.clients)
    b = next(iter(now.businesses.values()))
    assert now.next_number(b) == was.next_number(next(iter(was.businesses.values())))  # numbering carries on
    assert now.settings["accent"] == "blue"


def test_only_the_first_time(tmp_path: Path):
    old = _cobro_folder(tmp_path / "Cobro")
    new = tmp_path / "Saldo"
    new.mkdir()
    (new / "businesses.json").write_text("[]", encoding="utf-8")  # Saldo has files of its own
    assert not from_cobro.copy_folder(old, new)
    assert sorted(p.name for p in new.iterdir()) == ["businesses.json"]


def test_nothing_to_bring_over(tmp_path: Path):
    new = tmp_path / "Saldo"
    assert not from_cobro.copy_folder(tmp_path / "Cobro", new)  # no Cobro on this computer
    (tmp_path / "Cobro" / "logs").mkdir(parents=True)  # Cobro opened once, nothing made
    assert not from_cobro.copy_folder(tmp_path / "Cobro", new)
    assert not new.exists()


def test_a_copy_cut_short_changes_nothing_and_is_tried_again(tmp_path: Path, monkeypatch):
    old = _cobro_folder(tmp_path / "Cobro")
    new = tmp_path / "Saldo"
    before = _files(old)

    def full_disk(src, dst, **_kw):
        Path(dst).mkdir(parents=True)
        shutil.copy2(Path(src) / "businesses.json", Path(dst) / "businesses.json")
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(from_cobro.shutil, "copytree", full_disk)
    with pytest.raises(OSError):
        from_cobro.copy_folder(old, new)
    assert not from_cobro.has_data(new) and not list(new.iterdir())
    assert _files(old) == before

    monkeypatch.undo()
    assert from_cobro.copy_folder(old, new)  # the next start
    assert from_cobro.has_data(new)


def test_cobros_program_stays_behind(tmp_path: Path):
    """Cobro's Linux install script put the program inside the data folder: only your files come along."""
    old = _cobro_folder(tmp_path / "cobro")
    (old / "_internal").mkdir()
    (old / "_internal" / "libQt6Core.so").write_bytes(b"lib")
    for name in ("Cobro", "install.sh", "cobro.desktop", "icon.png"):
        (old / name).write_bytes(b"program")
    new = tmp_path / "saldo"
    assert from_cobro.copy_folder(old, new)
    assert not any((new / n).exists() for n in from_cobro.PROGRAM)
    assert (new / "logos" / "a1b2.png").exists() and (new / "invoices").is_dir()


def test_only_into_saldos_own_folder(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "home" / "share"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "home" / "local"))
    monkeypatch.delenv("SALDO_DATA_DIR", raising=False)
    _cobro_folder(paths.standard_data_dir("Cobro"))
    assert not from_cobro.carry_over()  # the tests' own folder (like SALDO_DATA_DIR): never filled from Cobro

    paths.use_data_dir(None)
    assert paths.data_dir() == paths.standard_data_dir()
    assert from_cobro.carry_over()
    assert from_cobro.has_data(paths.standard_data_dir())
    assert not from_cobro.carry_over()  # once


def test_the_ai_key_comes_along_and_the_old_entry_stays(keychain):
    keychain.store[("Cobro", "ai:openai")] = "sk-old"
    keychain.store[("Cobro", "ai:anthropic")] = "sk-ant-old"
    keychain.store[("Saldo", "ai:anthropic")] = "sk-ant-new"  # already set in Saldo: kept
    assert secrets.carry_over(["ai:openai", "ai:anthropic", "account:session"]) == 1
    assert secrets.get("ai:openai") == "sk-old"
    assert secrets.get("ai:anthropic") == "sk-ant-new"
    assert keychain.store[("Cobro", "ai:openai")] == "sk-old"  # never removed


def test_the_first_start_brings_files_and_keys(monkeypatch, keychain):
    from saldo import app
    from saldo.services.ai import providers

    keychain.store[("Cobro", providers.secret_name("openai"))] = "sk-old"
    monkeypatch.setattr(from_cobro, "carry_over", lambda: True)
    assert app._move_in_from_cobro() == ("Everything from Cobro is here.", "done")
    assert providers.key_for("openai") == "sk-old"

    def full_disk():
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(from_cobro, "carry_over", full_disk)
    text, tone = app._move_in_from_cobro()
    assert tone == "problem" and "safe" in text
    monkeypatch.setattr(from_cobro, "carry_over", lambda: False)
    assert app._move_in_from_cobro() is None  # nothing from Cobro (or done before): nothing to say


# ---------------------------------------------------------------------------- the Mac app
def _bundle(app: Path, bundle_id: str) -> Path:
    (app / "Contents" / "MacOS").mkdir(parents=True)
    with (app / "Contents" / "Info.plist").open("wb") as f:
        plistlib.dump({"CFBundleIdentifier": bundle_id, "CFBundleName": "Saldo"}, f)
    return app


def _on_a_mac(monkeypatch, me: Path) -> None:
    monkeypatch.setattr(update, "install_kind", lambda: "mac-app")
    monkeypatch.setattr(update, "app_bundle", lambda: me)


def _gone_pid() -> int:
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


@pytest.mark.skipif(sys.platform == "win32", reason="Mac helper")
def test_cobro_app_renames_itself_saldo_app(tmp_path: Path, monkeypatch):
    """An older Cobro's updater puts the new version where Cobro was, as Cobro.app: it becomes Saldo.app, and
    Saldo.app is what opens."""
    app = _bundle(tmp_path / "Applications" / "Cobro.app", "com.badfilmmaker.saldo")
    _on_a_mac(monkeypatch, app)
    bin_dir = tmp_path / "bin"  # `open`, standing in for the Mac's
    bin_dir.mkdir()
    opened = tmp_path / "opened"
    (bin_dir / "open").write_text(f'#!/bin/sh\necho "$@" > {shlex.quote(str(opened))}\n')
    (bin_dir / "open").chmod(0o755)

    plan = from_cobro.rename_plan([], pid=_gone_pid())
    assert plan is not None
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    subprocess.run(plan.command, check=True, timeout=30, env=env)
    new = app.with_name("Saldo.app")
    assert new.is_dir() and not app.exists()  # renamed, not copied: one app
    assert opened.read_text().strip() == str(new)


def test_cobro_app_is_left_alone_when_it_should_be(tmp_path: Path, monkeypatch):
    app = _bundle(tmp_path / "Applications" / "Cobro.app", "com.badfilmmaker.saldo")
    _on_a_mac(monkeypatch, app)
    assert from_cobro.rename_plan([from_cobro.KEEP_NAME]) is None  # the rename didn't work last time
    _on_a_mac(monkeypatch, tmp_path / "Applications" / "Saldo.app")
    assert from_cobro.rename_plan([]) is None  # already Saldo.app
    monkeypatch.setattr(update, "install_kind", lambda: "source")
    assert from_cobro.rename_plan([]) is None


def test_the_old_cobro_app_beside_saldo_app_is_found(tmp_path: Path, monkeypatch):
    apps = tmp_path / "Applications"
    me = _bundle(apps / "Saldo.app", "com.badfilmmaker.saldo")
    old = _bundle(apps / "Cobro.app", "com.badfilmmaker.cobro")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    _on_a_mac(monkeypatch, me)
    mine = [p for p in from_cobro.leftovers() if p.is_relative_to(tmp_path)]
    assert mine == [old]

    shutil.rmtree(old)
    _bundle(old, "com.example.cobro")  # another app that happens to be called Cobro: never touched
    assert not [p for p in from_cobro.leftovers() if p.is_relative_to(tmp_path)]
    (old / "Contents" / "Info.plist").write_bytes(b"<plist><dict><key>")  # unreadable: left alone too
    assert not from_cobro.is_ours(old)


def test_the_old_cobro_app_goes_to_the_trash_once(tmp_path: Path, monkeypatch):
    from PySide6.QtCore import QFile

    from saldo import app

    old = _bundle(tmp_path / "Applications" / "Cobro.app", "com.badfilmmaker.cobro")
    trashed = []
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(from_cobro, "leftovers", lambda: [old])
    monkeypatch.setattr(QFile, "moveToTrash", staticmethod(lambda p: trashed.append(p) or True))
    w = SimpleNamespace(lib=Library(paths.data_dir()))

    monkeypatch.setattr(app, "_reach", lambda name, message=b"": name.startswith("cobro-"))
    assert not app._put_away_cobro(w)  # Cobro is still open: not now
    assert not trashed and not w.lib.settings.get("cobro_app_put_away")

    monkeypatch.setattr(app, "_reach", lambda name, message=b"": False)
    assert app._put_away_cobro(w)
    assert trashed == [str(old)] and w.lib.settings["cobro_app_put_away"]
    assert not app._put_away_cobro(w)  # once: put back from the Trash, it stays
    assert trashed == [str(old)]
