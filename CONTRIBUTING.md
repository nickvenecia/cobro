# Cobro code rules

How Cobro's code is organized and the rules every change follows. The look of the app has its
own rulebook: **[DESIGN.md](DESIGN.md)**. Read both before changing anything.

---

## 1. Where things go

```
cobro/
  core/        Everything about invoices: data, money, dates, numbering, the paper's look, saving, undo,
               the updater. No Qt imports, ever.
  doc/         Drawing the invoice (QtGui only, no widgets): fonts, layout, PDF/PNG/print.
  services/    Anything outside the app: the keychain, accounts, feedback, AI providers and jobs. No Qt.
  ui/          Everything you see. Qt Widgets. Talks to core/, doc/ and services/, never the other way round.
    style/       tokens.py (every number and color), theme.py (stylesheet, icons, fonts)
    components/  the shared building blocks (widgets, panels, glass, title bar, background worker)
    window/      the main window, split into parts (menus, editing, pages, transfer, services, ai, sidebar,
                 tables, filters)
    panels/      the right-hand panels (the invoice, the assistant)
    dialogs/     Settings, the page window, profile, client, alerts, AI setup and review, updates…
  app.py       Starts the window (fonts, stylesheet, light/dark, one window at a time, --smoke-test)
  cli.py       Same drawing without a window: `python -m cobro cli ...`
tests/         One test file per area (test_money.py, test_store.py, test_render.py, test_window.py, test_ai.py,
               test_security.py, test_release.py…); conftest.py gives every test its own empty data folder
               and an empty keychain in memory; screenshot.py takes every screen in dark, light and yellow
scripts/       make_icon.py, make_fonts.py, release_notes.py
packaging/     Installer files per OS
```

- Imports are absolute (`from cobro.core import money`). One module per job. No circular imports.
- `core/` and `services/` must work headless and be testable without Qt.
- Per-user files (invoices, logos, logs) go under `core.paths.data_dir()`.
  Never write next to the app, and never into a fixed name in the shared temp folder.
- Exported files go where the person picks (default Documents/Cobro), written to a temp file beside the
  target and moved into place.

---

## 2. Style

- Python 3.12. `from __future__ import annotations` at the top of every module.
- **Ruff** formats and lints. Before every commit:
  ```bash
  ruff format . && ruff check . && python -m pytest -q
  ```
  CI fails if any of the three fails. Settings are in `pyproject.toml` (line length 110).
- Type hints on every function signature. Prefer `X | None` and built-in generics (`list[str]`).
- Names: `snake_case` functions/variables, `PascalCase` classes, `UPPER_CASE` constants,
  `_leading_underscore` for anything private to a module.
- Every module starts with a one-line docstring saying what it's for. Public functions get a
  docstring when the name doesn't say everything.
- Comments explain **why**, not what. Link to the bug or quirk when a line looks odd.
- No dead code, no commented-out code, no `print()` in the app (use the logger).

---

## 3. Safety rules (never break these)

**The user's files**
1. **Never lose an invoice.** All saving goes through `store.write_json`: a temp file in the same folder,
   then `os.replace`. A file that can't be read is renamed aside (`.unreadable-<time>`), never deleted.
2. Exports (PDF, PNG) are the same: temp file beside the target, then `os.replace`. A failed export
   never leaves a broken file or replaces a good one.
3. Logos are read and drawn again by Cobro (`profile.import_logo`: a PNG no bigger than LOGO_MAX_PX, files over
   LOGO_MAX_BYTES refused) and kept in the data folder, named by their content; the original is never touched. A
   logo's name is only ever used through `paths.logo_path`, so it can't point outside the logos folder.
4. Files from Cobro 1.x open as they were, and nothing in them is dropped when they're saved again. New model
   fields need defaults that mean "off" or "empty". If a change touches saved files, test it against an old one.

**Running other programs**
5. Always pass arguments as a **list**. Never `shell=True`, never build a command string.
6. Every `subprocess` call gets `**fileutil.popen_kwargs()` (no console windows on Windows).
7. Never wait on a program's output with a pipe nobody reads (a full pipe freezes it).
8. The only programs Cobro starts are the system's own (open / explorer / xdg-open to show a file, and
   the updater's helper script).

**Network**
9. HTTPS only, with certificate checks on (`net.ssl_context()`; never `verify=False` or `CERT_NONE`).
10. The network is used only for updates (GitHub; checked against the **SHA-256 GitHub publishes** before they're
    used) and, when you use AI, your provider. AI requests go through `core/web.py` (never a redirect with a key on
    board; plain http only to a model on this computer) and carry only line items' words: never amounts,
    clients, the project or your profile. Invoices themselves are never sent anywhere.
11. Keys and the sign-in live only in the system keychain (`services/secrets.py`): never in a file, the
    settings, a log or an error. No keychain means no saving, never a file instead.
12. Pin build-time downloads to official sources with checksums (appimagetool in build_appimage.sh); GitHub
    Actions are pinned to exact commits and Python packages to exact versions (Dependabot proposes updates).

**Input from outside**
13. Treat file names, logo files, AI answers and anything from another process as untrusted. Names and AI
    answers are shown as plain text everywhere. AI answers must fit a strict shape (`services/ai/tasks.py`) and
    every change waits in the Review window; a copy of the invoice is kept first (`Library.snapshot`).
14. The single-instance socket only accepts the same user (`UserAccessOption`) and only ever raises the window.
15. Never `eval`/`exec`/`pickle` anything. Settings are JSON. CSV exports can't carry formulas
    (`spreadsheet.safe_cell`).
16. Never log or show secrets or full environment variables.

**Errors**
17. No silent `except: pass` around real work. Catch the narrowest exception you can; if you must
    swallow one, `log.warning(..., exc_info=True)` so it lands in the log file.
18. Messages shown to the user are plain English and say what to do next (see DESIGN.md §7).
    Technical details go to the log (`core/log.py`, `cobro.log` in the data folder).

---

## 4. Threads

- Long work (the update check and download, AI jobs and questions) runs on a `components/worker.Worker` (a QThread
  with progress / done / failed / stop) and talks to the window with **signals**. The window copies what a job
  needs before it starts, so you can keep working. Drawing a page takes milliseconds; keep it that way.

---

## 5. Speed

- The page window redraws DRAW_DELAY_MS after the last change, the table refreshes TABLE_DELAY_MS after, and saving
  waits SAVE_DELAY_MS, so typing never stutters.
- Font metrics are cached (`doc.fonts.metrics`); icons are cached (`theme.icon`); a delegate paints the table's rows
  (never a widget per row).

---

## 6. Tests

- Every change to `core/` or `doc/` comes with a test. Name it after the behavior:
  `test_a_broken_file_is_set_aside_not_lost`.
- Tests never touch real data: `tests/conftest.py` gives every test its own empty data folder and an empty
  keychain in memory, and closes the windows a test made. AI tests use a pretend provider (no internet, no keys).
- UI changes: check screenshots in dark, light and a light accent
  (`QT_QPA_PLATFORM=offscreen python tests/screenshot.py OUTDIR`).
- Before a release, the packaged app must pass `--smoke-test` (CI does this on every platform).

---

## 7. Commits and releases

- One topic per commit. Message: a short plain summary line in the present tense ("Add A4 paper"), nothing
  added after it (no co-author or sign-off lines, no links).
- **Merging is releasing.** A pull request with a change users will notice bumps `__version__` in
  `cobro/__init__.py` once: the last number for fixes and polish (2.0.0 → 2.0.1), the middle one for a new
  feature (2.0.1 → 2.1.0), the first for a big change (2.1.0 → 3.0.0). A released number is never used again.
  Its notes go at the top of `CHANGELOG.md` under `## X.Y.Z`, that same number, never under "Unreleased".
  Changes users won't notice don't bump it.
- Merging it to main builds every platform, tags the commit `vX.Y.Z` and publishes the Release with the
  downloads, in one run of `.github/workflows/build.yml`. Never tag or release by hand.
- Never commit `build/`, `dist/`, real invoices, personal details, or anything with a password or key in it.
  Signing secrets live only in GitHub → Settings → Secrets.
