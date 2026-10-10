# Cobro: notes for Claude Code

Cross-platform (macOS / Windows / Linux) invoice maker. Listo's sibling: same structure, same design system,
same build and release pipeline (github.com/nickvenecia/listo).
Python 3.12 + PySide6 (Qt Widgets). Invoices are drawn with QPainter (one layout for preview, PDF, PNG, print).
Shipped as a PyInstaller app; GitHub Actions builds the downloads.
The owner is a filmmaker (director/DP/editor/colorist), not a full-time developer. Explain changes in plain words.

## Read these first
- **[DESIGN.md](DESIGN.md)**: how the app and the invoice page look and read. Sizes, spacing, type, colors, wording.
  All app values live in `cobro/ui/tokens.py`; paper colors in `cobro/core/looks.py`. Never type a size or color anywhere else.
- **[CONTRIBUTING.md](CONTRIBUTING.md)**: code rules. Layout, style (ruff), safety rules, tests, commits.
- Before finishing any change: `ruff format . && ruff check . && python -m pytest -q`.

## Layout
```
cobro/
  core/            Invoices. No Qt imports.
    model.py       Business (+ Look), Client, LineItem, Invoice dataclasses; from_dict() tolerates old/new files
    money.py       exact Decimal parsing / formatting, totals() (subtotal, discount, tax, deposit, balance)
    dates.py       "Oct 10, 2026", due dates, terms labels (English on every computer)
    numbering.py   PREFIX-YEAR-001 numbers, initials()
    looks.py       type styles, colors, headers, logo sizes, papers; resolve(Look) -> fonts + colors; paper INK/RULE
    document.py    build(invoice, business) -> InvoiceView: every string on the page; status_of() (overdue);
                   file_stem() (export file name); summary_text() (Copy as Text)
    store.py       Library: JSON files in data_dir() (businesses.json, clients.json, invoices/<id>.json,
                   settings.json), atomic writes, unreadable files set aside; new_invoice / duplicate / remember_client
    sample.py      the made-up Juniper Lane Films business + invoice (tests, smoke test, screenshots)
    update.py      Listo's updater, pointed at nickvenecia/cobro (asset names are a contract, see Releasing)
    paths.py, log.py, net.py (certifi SSL), fileutil.py (reveal in Finder/Explorer)
  doc/             Drawing the invoice. QtGui only, no widgets.
    fonts.py       loads assets/fonts; make(FontSpec, device) sizes fonts in points on ANY device (divides the dpi out)
    render.py      layout(view, resolved_look, logo) -> [Page of steps]; paint(painter, page). Pagination, footer
    export.py      to_pdf (QPdfWriter at 72 dpi), to_png, print_pages, image() for the preview; temp file + os.replace
  ui/
    tokens.py      THE design tokens (Listo's, with turquoise instead of marigold)
    theme.py       stylesheet built from tokens, SVG icons
    widgets.py     Listo's building blocks + TextBox (multi-line field)
    main_window.py the three panels, menus, saving (debounced), exporting, updates
    invoice_list.py   ① cards, filter, Unpaid / Paid totals, ⋯ tools menu, Update button
    details.py     ② every field; Look group edits the Business; import_logo() copies logos into data_dir()/logos
    preview.py     ③ pages as pictures sized to the panel; Save PDF… / Print… / ⋯; Show File, Mark as Sent
    business_dialog.py, dialogs.py (confirm, about), update_dialog.py, titlebar.py (Mac)
  app.py           QApplication, fonts, stylesheet, rounded popups, one window at a time, --smoke-test
  cli.py           `python -m cobro cli sample OUT.pdf|png [--style] [--color] [--header] [--items] [--logo]`
scripts/make_icon.py   draws cobro/assets/icon.png ("cobro." on Listo's dark tile)
scripts/make_fonts.py  cuts the bundled fonts from Google Fonts' OFL files (results are committed)
cobro.spec, packaging/, .github/workflows/build.yml   same as Listo
```

## Rules that matter
- **Never lose an invoice.** Every write is atomic (`store.write_json`); unreadable files are renamed aside, never deleted.
  Edits save SAVE_DELAY_MS after typing stops, on switching invoices, and on quit (`MainWindow.flush/shutdown`).
- **The preview is the export.** Never draw something in the preview that the PDF doesn't (or the other way round):
  everything goes through `render.layout` + `render.paint`.
- **Fonts in points everywhere.** Use `fonts.make(spec, painter.device())` and `fonts.metrics(spec)`; never
  `setPointSize` directly, or the PDF and the screen drift apart.
- Bundled fonts are fixed-weight TTFs (PDF embedding); add new ones through scripts/make_fonts.py and
  `looks.BUNDLED_FONTS`, plus their OFL file and a THIRD_PARTY_NOTICES line.
- Clients are remembered (`Library.remember_client`) only when an invoice is exported, printed, its status changes,
  or you switch away / quit, so half-typed names never pile up.
- Logos are copied into data_dir()/logos (big pictures scaled to LOGO_MAX_PX); the Look stores only the file name.
  A missing logo file just leaves the logo out.
- New model fields need defaults that mean "off"/empty: old files are read through `from_dict()`.
- Personal details never go in the code or the repo (it's public). Use core/sample.py's made-up business for examples.

## Commands
```bash
pip install -r requirements-dev.txt
python -m cobro                         # run the app
python -m cobro cli sample out.pdf      # a sample invoice without a window
python -m pytest -q
QT_QPA_PLATFORM=offscreen python tests/screenshot.py OUTDIR   # UI screenshots without a display
pyinstaller cobro.spec --noconfirm      # build the app into dist/
COBRO_DATA_DIR=/tmp/x python -m cobro   # run against a throwaway data folder
```

## Releasing
Bump `__version__` in `cobro/__init__.py`, turn CHANGELOG's top heading into that version, commit, then tag
`vX.Y.Z` (GitHub Desktop: History → right-click the commit → Create Tag…, then Push origin) or
`git tag vX.Y.Z && git push --tags`. CI builds every platform and publishes the Release (about 15-20 min).
CI attaches: Cobro-mac-apple-silicon.dmg, Cobro-mac-intel.dmg, Cobro-windows-setup.exe, Cobro-windows-portable.zip,
Cobro-linux-x64.AppImage, Cobro-linux-x64.tar.gz. **These names are a contract**: the README's download links
(releases/latest/download/<name>) and the in-app updater (update.asset_name) both depend on them, and the repo
must stay public. update.REPO = "nickvenecia/cobro".

## Ideas not done yet
- Email the PDF straight from Cobro (attach to a new mail)
- Reorder line items by dragging
- Recurring invoices / a monthly reminder for unpaid ones
- Estimates / quotes that turn into invoices
- Export a CSV of paid invoices for taxes
