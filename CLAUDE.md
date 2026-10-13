# Cobro: notes for working on the code

Cross-platform (macOS / Windows / Linux) invoice maker for freelance filmmakers.
Python 3.12 + PySide6 (Qt Widgets). Invoices are drawn with QPainter (one layout for the page window, PDF, PNG and
print). Shipped as a PyInstaller app; GitHub Actions builds the downloads.
The owner is a filmmaker (director/DP/editor/colorist), not a full-time developer. Explain changes in plain words.

## Read these first
- **[DESIGN.md](DESIGN.md)**: how the app and the invoice page look and read. Sizes, spacing, type, colors, wording.
  Every app value lives in `cobro/ui/style/tokens.py`; the paper's colors in `cobro/core/looks.py`. Never type a
  size or a color anywhere else.
- **[CONTRIBUTING.md](CONTRIBUTING.md)**: code rules. Layout, style (ruff), safety rules, tests, commits.
- **[SECURITY.md](SECURITY.md)**: what Cobro protects and how.
- Before finishing any change: `ruff format . && ruff check . && python -m pytest -q`, and
  `python -m cobro --smoke-test`. After a change to how something looks, take screenshots (below) in light and dark.
- Commit messages: a short plain summary, nothing added after it (no co-author or sign-off lines, no links).
  Commits are authored as Nick Venecia (this repo's git config).
- **Every pull request with a change users will notice bumps the version** (see Releasing), once per pull request,
  with its CHANGELOG notes under that version. Merging it publishes the release.

## The window
A glass sidebar on the left (where you are), a big table of invoices in the middle, and a glass panel on the right
that slides in when something is picked.
- **Sidebar**: the wordmark; Invoices (All Invoices, Drafts, Unpaid, Paid, with counts; its own small + makes a new
  invoice); the Update button when there is one; the profile card at the bottom (your profiles, Edit Profile…,
  Add a Profile…, New Client…, Send Feedback…, Check for Updates…, Settings…).
- **Toolbar**: the place's title and count; search, then the filter button (Divide By month / client / none;
  Show by status; From one profile; Year; Clear Filters); on the right the share button (Invoice…, Export as
  CSV…, Back Up…), the assistant's bubble, and the round + (New Invoice).
- **Table**: sorts by any column (newest first to start), bands by month (newest month on top) or client with their
  totals, each folding with a click; ⌘A, Shift and ⌘-click pick many; Delete deletes them after one alert.
  Underneath: Unpaid, Overdue (only when something is), Paid and Total of what's showing.
- **Right panel**: the invoice (`panels/invoice.py`): From && Bill To, Invoice, Project, Line Items, Adjustments,
  Payment && Terms, each folding away (remembered); Invoice… across the bottom opens the page. Or the assistant
  (`panels/assistant.py`), which stays while you move around. Esc or ✕ closes it; a new invoice left empty goes away.
- **The page** opens in its own window (`dialogs/preview.py`): Save PDF…, Print…, ⋯ (Save as PNG…, Copy as Text,
  Email Client…, Open Invoices Folder), Show File, Mark as Sent, and the moon for the Dark Page.
- **Settings** (⌘,) is one window with its own sidebar: General (Appearance, Accent Color, Updates), Profiles (the
  whole profile form in place), AI, Account, Keyboard Shortcuts, Your Data (Show Folder, Back Up…).
- The Mac menu bar has every command: File, Edit, View, Profile, AI, Window, Help (hidden on Windows and Linux,
  where the same keys work).

## Layout
```
cobro/
  core/            Invoices. No Qt imports.
    model.py       Business (a "profile" in the app, + Look), Client, LineItem, Invoice; from_dict() tolerates
                   old and new files
    money.py       exact Decimal parsing / formatting, totals() (subtotal, discount, tax, deposit, balance)
    dates.py       "Oct 10, 2026", due dates, terms labels (English on every computer)
    numbering.py   PREFIX-YEAR-001 numbers (or one count per client: PREFIX-CODE-YEAR-001 / CODE-YEAR-001)
    looks.py       the paper: colors (default turquoise), headers, logo sizes, paper sizes, FONT (Inter) and MONO
                   (IBM Plex Mono, for the invoice number); resolve(Look, dark=) -> Resolved; LIGHT (every export)
                   and DARK (the page window's Dark Page only)
    document.py    build(invoice, business) -> InvoiceView: every string on the page; status_of() (overdue);
                   file_stem() (export file name); summary_text() (Copy as Text)
    store.py       Library: JSON files in data_dir() (businesses.json, clients.json, invoices/<id>.json,
                   settings.json), atomic writes, unreadable files set aside; new_invoice / duplicate;
                   save_client / delete_client (drafts follow a client's edits); next_number / renumber;
                   snapshot() (a copy in backups/ before an AI's changes)
    history.py     undo / redo of invoices, clients and profiles
    spreadsheet.py Export as CSV (plain numbers; nothing a spreadsheet would run as a formula)
    sample.py      the made-up Juniper Lane Films profile, clients and invoices (tests, smoke test, screenshots)
    update.py      the updater, pointed at nickvenecia/cobro (asset names are a contract, see Releasing)
    web.py         the one way to reach an address (no redirects with a key on board)
    paths.py (data_dir, logo_path), log.py, net.py (certifi SSL), fileutil.py (reveal, zip_folder)
  doc/             Drawing the invoice. QtGui only, no widgets.
    fonts.py       loads assets/fonts; make(FontSpec, device) sizes fonts in points on ANY device (divides the dpi out)
    render.py      layout(view, resolved_look, logo) -> [Page of steps]; paint(painter, page). Pagination, footer;
                   logos scaled to print size (LOGO_DPI) so PDFs stay small
    export.py      to_pdf (QPdfWriter at 72 dpi), to_png, print_pages, image() for the page window
  services/        Anything outside the app. No Qt.
    secrets.py     the system keychain (keyring) for AI keys and the sign-in; never a file
    account.py     accounts (not switched on yet); feedback.py Send Feedback (an outbox until sending is on)
    ai/            providers.py (every provider, live model lists, ask), tasks.py (Tidy Up Line Items, chat, apply)
  ui/
    style/         tokens.py (every number and color, DARK and LIGHT, the accent choices), theme.py (the
                   stylesheet, the SVG icons in _SVG, fonts)
    components/    widgets.py, panels.py (LeftPanel, SidePanel), glass.py (backdrop, Dock), titlebar.py (Mac),
                   worker.py (background jobs)
    window/        main_window.py and its parts: menus.py, editing.py, pages.py (the page window, exports),
                   transfer.py (CSV, Back Up), services.py (settings, account, feedback, updates, light/dark),
                   ai.py, sidebar.py, tables.py, filters.py, common.py (places, status words and colors)
    panels/        base.py (DetailsBase), invoice.py (+ LineEditor), assistant.py
    dialogs/       common.py (Alert, confirm, notice, about), settings.py, profile.py (+ import_logo), client.py,
                   preview.py (the page window), shortcuts.py, feedback.py, account.py, ai_setup.py,
                   ai_review.py, update.py
  app.py           QApplication, fonts, stylesheet (set_appearance: system / light / dark + accent), rounded
                   popups, plain-text labels, one window at a time, --smoke-test
  cli.py           `python -m cobro cli sample OUT.pdf|png [--color] [--header] [--items] [--logo]`
scripts/make_icon.py      draws cobro/assets/icon.png ("c." on the dark tile, the full stop in the accent)
scripts/make_fonts.py     cuts Inter's fixed weights from Google Fonts' OFL files (results are committed)
scripts/release_notes.py  a version's CHANGELOG notes + the downloads (the release uses it; CI checks it)
cobro.spec, packaging/, .github/workflows/build.yml, .github/dependabot.yml   building and releasing
```

## Rules that matter
- **Never lose an invoice.** Every write is atomic (`store.write_json`); unreadable files are renamed aside, never
  deleted. Edits save SAVE_DELAY_MS after typing stops, on switching invoices, and on quit
  (`MainWindow.flush/shutdown`). Files written by Cobro 1.x (type styles and all) open as they were and are saved
  back with everything they held; `tests/test_window.py` opens a 1.0-style data folder to prove it.
- **The page window is the export.** Everything goes through `render.layout` + `render.paint`. The one difference
  allowed is the Dark Page: the same layout in `looks.DARK` colors, in the page window only. Exports call
  `MainWindow.page_list()` (light) and never pass dark.
- **Light or dark, as the computer is set** (or pinned in Settings › General), switching live
  (`app.set_appearance`; `colorSchemeChanged`; unknown stays dark). Read colors as `tokens.X` when you draw, never
  keep one; icons come from `theme.icon(name, color)` and recolor themselves. Every color has a DARK and a LIGHT
  value. The accent the person picks never changes the paper: the paper has its own color in the profile.
- **Fonts in points everywhere.** Use `fonts.make(spec, painter.device())` and `fonts.metrics(spec)`; never
  `setPointSize` directly, or the PDF and the screen drift apart. The paper is Inter, with IBM Plex Mono for the
  invoice number. Older files' type styles are kept in the file but no longer change the page.
- Clients are saved only on purpose, through the client dialog (`Library.save_client`): typing never adds one.
  Invoices keep their own copy: drafts follow a client's edits, sent and paid invoices keep what they said.
  Deleting a client leaves every invoice as it was.
- A draft's number follows its profile, client and year while Cobro picked it (`Invoice.auto_number`,
  `Library.renumber`). Typing a number, or the invoice being sent or paid, freezes it.
- Another app may hand Cobro a draft by writing an invoice file into `invoices/` in this format, so the data
  folder's place, the file names and the fields stay as they are (new fields only with defaults).
- Logos are redrawn by Cobro as PNGs no bigger than LOGO_MAX_PX before they're kept in data_dir()/logos, named by
  their content (`profile.import_logo`); the Look stores only the file name, read through `paths.logo_path`.
  A missing logo file just leaves the logo out.
- **AI**: only line items' words go to a provider (never amounts, clients, the project or the profile); only a
  line's name and details can change; every change waits in the Review window; `tasks.apply` keeps a copy first.
  Keys live in the keychain only.
- Only show what applies: Discount, Deposit and Sales Tax appear when an invoice has them (+ Discount adds one),
  a line item's details box once it has details.
- New model fields need defaults that mean "off"/empty: old files are read through `from_dict()`.
- Personal details never go in the code or the repo (it's public). Use core/sample.py's made-up business.

## Commands
```bash
pip install -r requirements-dev.txt
python -m cobro                         # run the app
python -m cobro --smoke-test            # start, make a sample invoice, save it as a PDF, quit
python -m cobro cli sample out.pdf      # a sample invoice without a window
python -m pytest -q
QT_QPA_PLATFORM=offscreen python tests/screenshot.py OUTDIR   # every screen in dark, light and a yellow accent
pyinstaller cobro.spec --noconfirm      # build the app into dist/
COBRO_DATA_DIR=/tmp/x python -m cobro   # run against a throwaway data folder
python scripts/make_icon.py             # redraw the app icon
```

## Releasing
**Merging is releasing.** Nobody tags or releases by hand.
- A pull request with a change users will notice (a fix, polish, a new feature) bumps `__version__` in
  `cobro/__init__.py`, once per pull request: the last number for fixes and polish (1.2.0 → 1.2.1), the middle
  one for a new feature (1.2.1 → 1.3.0). Its notes go at the top of CHANGELOG.md under `## X.Y.Z`, that same
  number, never under "Unreleased". Changes users won't notice (tests, notes, code tidying) don't bump it.
- When it's merged, the push to main runs `.github/workflows/build.yml`: it sees that `vX.Y.Z` has no tag yet,
  builds and tests every platform, tags that exact commit and publishes the GitHub Release with the downloads
  and the CHANGELOG notes, all in that one run (about 15-20 min). A merge that doesn't bump the version builds
  and tests, and releases nothing. Pull requests never release.
- The workflow checks, on every pull request too, that CHANGELOG's top section is the version in
  `cobro/__init__.py` (`scripts/release_notes.py`). Two quick merges can't release the same version twice: the
  release job runs one at a time and only one run can make the tag. A tag pushed by hand still works, but only
  if it matches the version.
- CI attaches: Cobro-mac-apple-silicon.dmg, Cobro-mac-intel.dmg, Cobro-windows-setup.exe,
  Cobro-windows-portable.zip, Cobro-linux-x64.AppImage, Cobro-linux-x64.tar.gz. **These names are a contract**:
  the README's download links (releases/latest/download/<name>) and the in-app updater (update.asset_name) both
  depend on them, and the repo must stay public. update.REPO = "nickvenecia/cobro". The release checks all six
  are there before it publishes.

## Ideas not done yet
- Email the PDF straight from Cobro (attach to a new mail)
- Reorder line items by dragging (for now: ⋯ › Move Up / Move Down)
- Recurring invoices / a monthly reminder for unpaid ones
- Estimates / quotes that turn into invoices
- Accounts (Settings › Account is ready; the service isn't switched on)
