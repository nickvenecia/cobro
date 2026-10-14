# Saldo: notes for working on the code

Cross-platform (macOS / Windows / Linux) invoice maker for freelance filmmakers.
Python 3.12 + PySide6 (Qt Widgets). Invoices are drawn with QPainter (one layout for the page window, PDF, PNG and
print). Shipped as a PyInstaller app; GitHub Actions builds the downloads.
The owner is a filmmaker (director/DP/editor/colorist), not a full-time developer. Explain changes in plain words.

## Read these first
- **[DESIGN.md](DESIGN.md)**: how the app and the invoice page look and read. Sizes, spacing, type, colors, wording.
  Every app value lives in `saldo/ui/style/tokens.py`; the paper's colors in `saldo/core/looks.py`. Never type a
  size or a color anywhere else.
- **[CONTRIBUTING.md](CONTRIBUTING.md)**: code rules. Layout, style (ruff), safety rules, tests, commits.
- **[SECURITY.md](SECURITY.md)**: what Saldo protects and how.
- Before finishing any change: `ruff format . && ruff check . && python -m pytest -q`, and
  `python -m saldo --smoke-test`. After a change to how something looks, take screenshots (below) in light and dark.
- Commit messages: a short plain summary, nothing added after it (no co-author or sign-off lines, no links).
  Commits are authored as Nick Venecia (this repo's git config).
- **Every pull request with a change users will notice bumps the version** (see Releasing), once per pull request,
  with its CHANGELOG notes under that version. Merging it publishes the release.

## The window
A glass sidebar on the left (where you are), a big table of invoices (or clients) in the middle, and a glass panel
on the right that slides in when something is picked.
- **Sidebar**: the wordmark; Invoices (All Invoices, with Drafts, Unpaid and Paid folding under it; counts; its own
  small + makes a new invoice); Clients (All Clients, with each client folding under it; its + makes a new client);
  the Update button when there is one; the profile card at the bottom (your profiles, Edit Profile…, Add a
  Profile…, Send Feedback…, Check for Updates…, Settings…). Folds are remembered (`sidebar_folded`).
- **Toolbar**: the place's title and count; search, then the filter button (Divide By month / client / none;
  Show by status; From one profile; Year; Clear Filters); on the right the share button (Invoice…, Export as
  CSV…, Back Up…), the assistant's bubble, and the round + (New Invoice; New Client in All Clients, where the
  filter, share and totals step aside).
- **Empty page**: with nothing to show, the table gives way to start tiles (`components/empty.py`): Add Your
  Profile…, New Invoice (the place's icon), New Client or Clear Filters; search and the filter hide.
- **Table**: sorts by any column (newest first to start), bands by month (newest month on top) or client with their
  totals, each folding with a click; ⌘A, Shift and ⌘-click pick many; Delete deletes them after one alert.
  Underneath: Unpaid, Overdue (only when something is), Paid and Total of what's showing. All Clients' table
  (`ClientTable`): name, attention, email, how many invoices, unpaid, billed; picked one at a time.
- **Right panel**: the invoice (`panels/invoice.py`): From && Bill To, Invoice, Project, Line Items (drag one by its
  grip to reorder), Adjustments, Payment && Terms, each folding away (remembered); Invoice… across the bottom opens
  the page. Or a client (`panels/client.py`): their name as the title, Contact, Invoice Numbers (only when a
  profile counts per client), their Invoices (click to open), New Invoice across the bottom (Save Client while it's
  a new one). Or the assistant (`panels/assistant.py`), which stays while you move around. Esc or ✕ closes it; a
  new invoice left empty goes away, and a new client is kept only once it has a name.
- **The page** opens in its own window (`dialogs/preview.py`): Save PDF…, Print…, ⋯ (Save as PNG…, Copy as Text,
  Email Client…, Open Invoices Folder), Show File, Mark as Sent, and the moon for the Dark Page.
- **Settings** (⌘,) is one window with its own sidebar: General (Appearance, Accent Color, Updates), Profiles (the
  whole profile form in place), AI, Account, Keyboard Shortcuts, Your Data (Show Folder, Back Up…).
- The Mac menu bar has every command: File, Edit, View, Profile, AI, Window, Help (hidden on Windows and Linux,
  where the same keys work).

## Layout
```
saldo/
  core/            Invoices. No Qt imports.
    model.py       Business (a "profile" in the app, + Look), Client, LineItem, Invoice; from_dict() tolerates
                   old and new files
    billing.py     an invoice's totals() (subtotal, discount, tax, total, deposit, balance), due(), terms labels
    money.py, dates.py   the shared helpers (the same files in every app; keep them that way): exact decimals
                   (a typo too big to be real counts as 0), "Oct 10, 2026" on every computer
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
    update.py      the updater, pointed at nickvenecia/saldo (asset names are a contract, see Releasing);
                   whats_new() reads a release's notes for the update window
    web.py         the one way to reach an address (no redirects with a key on board)
    from_cobro.py  moving in from Cobro (the app's old name): carry_over() copies its data folder the first time
                   Saldo opens (never moves or changes it); rename_plan() turns Cobro.app into Saldo.app;
                   leftovers() finds the old Cobro.app (app.py puts it in the Trash)
    paths.py (data_dir, standard_data_dir, logo_path), log.py, net.py (certifi SSL), fileutil.py (reveal, zip_folder)
  doc/             Drawing the invoice. QtGui only, no widgets.
    fonts.py       loads assets/fonts; make(FontSpec, device) sizes fonts in points on ANY device (divides the dpi out)
    render.py      layout(view, resolved_look, logo) -> [Page of steps]; paint(painter, page). Pagination, footer;
                   logos scaled to print size (LOGO_DPI) so PDFs stay small
    export.py      to_pdf (QPdfWriter at 72 dpi), to_png, print_pages, image() for the page window
  services/        Anything outside the app. No Qt.
    secrets.py     the system keychain (keyring) for AI keys and the sign-in; never a file; carry_over() copies
                   keys saved under the old name (Cobro) the first time
    account.py     accounts (not switched on yet); feedback.py Send Feedback (an outbox until sending is on)
    ai/            providers.py (every provider, live model lists, ask), tasks.py (Tidy Up Line Items, chat, apply)
  ui/
    style/         tokens.py (every number and color, DARK and LIGHT, the accent choices), theme.py (the
                   stylesheet, the SVG icons in _SVG, fonts)
    components/    widgets.py (Disclosure, Section, fields, DateField + CalendarPopup (every date, picked, never
                   typed)…, Toast: MainWindow.toast(text, tone) with "done" /
                   "problem" / "" for news), panels.py (LeftPanel, SidePanel), glass.py (backdrop, Dock),
                   titlebar.py (Mac), worker.py (background jobs), empty.py (EmptyPage, StartTile), lift.py
                   (drag to reorder)
    window/        main_window.py and its parts: menus.py, editing.py, pages.py (the page window, exports),
                   transfer.py (CSV, Back Up), services.py (settings, account, feedback, updates, light/dark),
                   ai.py, sidebar.py, tables.py, filters.py, common.py (places, status words and colors)
    panels/        base.py (DetailsBase), invoice.py (+ LineEditor), client.py (+ InvoiceLine), assistant.py
    dialogs/       common.py (Alert, confirm, notice, about), settings.py, profile.py (+ import_logo), client.py,
                   preview.py (the page window), shortcuts.py, feedback.py, account.py, ai_setup.py,
                   ai_review.py, update.py
  app.py           QApplication, fonts, stylesheet (set_appearance: system / light / dark + accent), rounded
                   popups, plain-text labels, one window at a time, --smoke-test
  cli.py           `python -m saldo cli sample OUT.pdf|png [--color] [--header] [--items] [--logo]`
scripts/make_icon.py      draws saldo/assets/icon.png ("s." on the dark tile, the full stop in the accent)
scripts/make_fonts.py     cuts Inter's fixed weights from Google Fonts' OFL files (results are committed)
scripts/release_notes.py  a version's CHANGELOG notes + the downloads (the release uses it; CI checks it)
saldo.spec, packaging/, .github/workflows/build.yml, .github/dependabot.yml   building and releasing
.github/workflows/cobro-release.yml   copies a release to nickvenecia/cobro, for Cobro 2.0.0's updater (run by hand)
```

## Rules that matter
- **Never lose an invoice.** Every write is atomic (`store.write_json`); unreadable files are renamed aside, never
  deleted. Edits save SAVE_DELAY_MS after typing stops, on switching invoices, and on quit
  (`MainWindow.flush/shutdown`). Files written by Saldo 1.x (type styles and all) open as they were and are saved
  back with everything they held; `tests/test_window.py` opens a 1.0-style data folder to prove it.
- **The app used to be called Cobro.** The first time Saldo opens, everything in Cobro's data folder (Mac and
  Windows "Cobro", Linux "cobro") is copied into Saldo's, and the AI key and sign-in are copied in the keychain
  (`from_cobro.carry_over`, `secrets.carry_over`). Cobro's folder and keychain entries are only ever read. A copy
  cut short changes nothing and is tried again next time; `tests/test_from_cobro.py` proves it. The old name
  appears only in that code, the updater compatibility (below) and the notes about them (README, CHANGELOG).
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
- Clients are saved only on purpose (`Library.save_client`): in their panel in All Clients (a new one once it has
  a name no other client has), or through the client dialog from Bill To. Typing under Bill To never adds one.
  Invoices keep their own copy: drafts follow a client's edits, sent and paid invoices keep what they said.
  Deleting a client leaves every invoice as it was. `Library.invoices_by_client()` finds a client's invoices (by
  id, or else by name).
- A draft's number follows its profile, client and year while Saldo picked it (`Invoice.auto_number`,
  `Library.renumber`). Typing a number, or the invoice being sent or paid, freezes it.
- Another app may hand Saldo a draft by writing an invoice file into `invoices/` in this format, so the data
  folder's place, the file names and the fields stay as they are (new fields only with defaults).
- Logos are redrawn by Saldo as PNGs no bigger than LOGO_MAX_PX before they're kept in data_dir()/logos, named by
  their content (`profile.import_logo`); the Look stores only the file name, read through `paths.logo_path`.
  A missing logo file just leaves the logo out.
- **AI**: only line items' words go to a provider (never amounts, clients, the project or the profile); only a
  line's name and details can change; every change waits in the Review window; `tasks.apply` keeps a copy first.
  Keys live in the keychain only.
- **Words are never cut off.** Text that might not fit wraps onto another line or ends in "…" with the whole text
  in its tooltip (`widgets.ElidedLabel`); fonts are wider on a Mac. `tests/cut_off.py` checks every screen
  (`test_no_words_are_cut_off_anywhere`); a new screen gets a line there.
- Only show what applies: Discount, Deposit and Sales Tax appear when an invoice has them (+ Discount adds one),
  a line item's details box once it has details, Work Dates and the Delivery Date once switched on.
- **Dates are picked in a calendar, never typed** (`widgets.date_field`). Work dates are two picked days saved as
  the text `dates.span` writes ("Sep 26–27, 2026", read back by `document.work_days`); older typed text is kept.
- **Act once the click is over.** A tile, a sidebar row or a line item a refresh can rebuild never opens a window or
  a menu inside its own click (CONTRIBUTING rule 19): the window can throw it away mid-click, which crashes Saldo.
- New model fields need defaults that mean "off"/empty: old files are read through `from_dict()`.
- Personal details never go in the code or the repo (it's public). Use core/sample.py's made-up business.

## Commands
```bash
pip install -r requirements-dev.txt
python -m saldo                         # run the app
python -m saldo --smoke-test            # start, make a sample invoice, save it as a PDF, quit
python -m saldo cli sample out.pdf      # a sample invoice without a window
python -m pytest -q
QT_QPA_PLATFORM=offscreen python tests/screenshot.py OUTDIR   # every screen in dark, light and a yellow accent
pyinstaller saldo.spec --noconfirm      # build the app into dist/
SALDO_DATA_DIR=/tmp/x python -m saldo   # run against a throwaway data folder
python scripts/make_icon.py             # redraw the app icon
```

## Releasing
**Merging is releasing.** Nobody tags or releases by hand.
- A pull request with a change users will notice (a fix, polish, a new feature) bumps `__version__` in
  `saldo/__init__.py`, once per pull request: the last number for fixes and polish (2.0.0 → 2.0.1), the middle
  one for a new feature (2.0.1 → 2.1.0), the first for a big change (a new window, a new way of working:
  2.1.0 → 3.0.0). A number that was released is never used again. Its notes go at the top of CHANGELOG.md under
  `## X.Y.Z`, that same number, never under "Unreleased". Changes users won't notice (tests, notes, code
  tidying) don't bump it.
- When it's merged, the push to main runs `.github/workflows/build.yml`: it sees that `vX.Y.Z` has no tag yet,
  builds and tests every platform, tags that exact commit and publishes the GitHub Release with the downloads
  and the CHANGELOG notes, all in that one run (about 15-20 min). A merge that doesn't bump the version builds
  and tests, and releases nothing. Pull requests never release.
- The workflow checks, on every pull request too, that CHANGELOG's top section is the version in
  `saldo/__init__.py` (`scripts/release_notes.py`). Two quick merges can't release the same version twice: the
  release job runs one at a time and only one run can make the tag. A tag pushed by hand still works, but only
  if it matches the version.
- The Release's text is `## What's New` with this version's CHANGELOG entries, then the downloads: the update
  window shows the What's New part, so the CHANGELOG's plain words are what people read before updating.
- CI attaches: Saldo-mac-apple-silicon.dmg, Saldo-mac-intel.dmg, Saldo-windows-setup.exe,
  Saldo-windows-portable.zip, Saldo-linux-x64.AppImage, Saldo-linux-x64.tar.gz. **These names are a contract**:
  the README's download links (releases/latest/download/<name>) and the in-app updater (update.asset_name) both
  depend on them, and the repo must stay public. update.REPO = "nickvenecia/saldo". The release checks all six
  are there before it publishes.
- **Copies for Cobro's updater.** Each download is also attached as Cobro-… (the app's old name), shaped the way
  Cobro's updater expects: Cobro.app in the .dmg (it renames itself Saldo.app on its first start), a Cobro folder
  with a Cobro.exe / Cobro beside Saldo's in the .zip and .tar.gz, the same installer (`saldo.iss` leaves a
  Cobro.exe where the app was installed as Cobro, until the next update). GitHub forwards the old repo name here,
  so Cobro 1.x updates straight from these. Cobro 2.0.0 also checks the download's address
  (github.com/nickvenecia/cobro/…), so it needs a repo of that name carrying the release:
  `.github/workflows/cobro-release.yml` says how and copies it there.

## Ideas not done yet
- Email the PDF straight from Saldo (attach to a new mail)
- Recurring invoices / a monthly reminder for unpaid ones
- Estimates / quotes that turn into invoices
- Accounts (Settings › Account is ready; the service isn't switched on)
