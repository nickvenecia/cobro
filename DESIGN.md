# Cobro design rules

The rules for how Cobro looks and reads. They are Listo's rules (the two apps are siblings), with the parts that are only about video swapped for invoices. Follow them for every screen, dialog and control.
If a change needs something these rules don't cover, add a rule here in the same commit.

All numbers and colors live in **`cobro/ui/tokens.py`**. The stylesheet (`cobro/ui/theme.py`) and
every widget import from there. **Never type a size, spacing, font size or color anywhere else.**
If you need a value that doesn't exist, add a token, give it a comment, and add it to the tables below.

---

## 1. Sizes

### Controls: one height for everything you click or type in

| Token | px | Used for |
|---|---|---|
| `CONTROL_H` | 34 | **Every** button, dropdown, text field and segmented control |
| `SMALL_H` | 24 | Chips on file cards, naming token buttons, icon-only buttons |
| `INDICATOR` | 16 | Standard icon box |
| `TOGGLE_ROW_H` · `TOGGLE_W`×`TOGGLE_H` | 32 · 36×20 | An on/off row and its switch |
| `BAR_H` | 6 | Progress bars |
| `TRACK_H` / `HANDLE` | 4 / 14 | Slider groove / handle |
| `SCROLL_W` / `SCROLL_MIN` | 10 / 30 | Scrollbar width / shortest handle |

- A button, a dropdown and a text field side by side must line up exactly. Never set a height on
  a single control; the stylesheet already sets it.
- Buttons size their width to their text (padding `0 SPACE_3`). Don't give buttons fixed widths.
- Dropdowns and text fields in the sidebar stretch to the full column width.

### Icons

| Token | px | Used for |
|---|---|---|
| `ICON_SM` | 14 | Icons inside small buttons (scissors, info, close) |
| `ICON` | 16 | Icons inside normal buttons and menus |
| `ICON_LG` | 24 | Reserved for larger placeholders |

All icons are line icons drawn as SVG in `theme._SVG` and made with `theme.icon(name, color)`.
Add new icons there; don't load image files for UI icons.

### Fixed layout sizes

`LIST_W`, `DETAILS_W`, `CARD_H`, `TEXT_BOX_H`, `TEXT_BOX_TALL`, `NUM_FIELD_W`, `SWATCH`, `LOGO_THUMB`,
`PAGE_GAP`, `PAGE_SHADOW`, `DIALOG_W`, `BUSINESS_DIALOG_H`, `WINDOW_SIZE`, `WINDOW_MIN`. Use these names, never the numbers.

---

## 2. Spacing: a 4-point grid

| Token | px | Use it for |
|---|---|---|
| `SPACE_1` | 4 | A label and its control; an icon and its text; lines inside one item |
| `SPACE_2` | 8 | Related items: buttons in a row, cards in the list, checkboxes in a stack |
| `SPACE_3` | 12 | Between sections inside a panel |
| `SPACE_4` | 16 | Padding of panels, bars and the main areas |
| `SPACE_5` | 24 | Padding of dialogs, empty states |

- Build layouts with the helpers in `cobro/ui/widgets.py`:
  `vbox(widget, margins, spacing)` / `hbox(...)` (spacing defaults to `SPACE_2`),
  `combo(...)` for dropdowns, and `Section("Title")` for a labelled group (Title Case label + its controls, `SPACE_1` apart).
- Margins are `SPACE_*` tokens or `0`. Nothing else.

---

## 3. Type

Font for the app itself: **Inter** (bundled in `cobro/assets/fonts`). One family only.
The invoice has its own fonts (see §9); they never appear in the app's controls.

| Token | px | Used for |
|---|---|---|
| `TEXT_XS` | 11 | Chips |
| `TEXT_SM` | 12 | Section labels (`MUTED`, semibold), secondary text: file details, hints, tooltips |
| `TEXT_MD` | 13 | Body text and every control (the default) |
| `TEXT_LG` | 14 | Emphasis: client names and amounts in the list, footer totals |
| `TEXT_XL` | 18 | Dialog titles, empty-state headlines |
| `TEXT_BRAND` | 21 | The "cobro." wordmark only |

Weights: `WEIGHT_REGULAR` 400 for text, `WEIGHT_MEDIUM` 500 for controls,
`WEIGHT_SEMIBOLD` 600 for titles, labels and the primary button, `WEIGHT_BOLD` 700 for the wordmark and dialog titles.

---

## 4. Corners

| Token | px | Used for |
|---|---|---|
| `RADIUS_XS` | 4 | Small inner corners |
| `RADIUS_SM` | 6 | Chips, menu and list rows, small buttons |
| `RADIUS` | 8 | Buttons, fields, dropdowns, segmented controls |
| `RADIUS_LG` | 12 | Invoice cards, line-item boxes, popups and menus |
| `RADIUS_XL` | 16 | Reserved |

Menus and dropdown lists are **always rounded**, with transparent corners, and so is the highlighted
row inside them. `app._RoundPopups` handles this for every `QMenu` and dropdown automatically: it makes
the popup window see-through and gives every dropdown `widgets.ComboItemDelegate` (rounded highlight,
`CONTROL_H - SPACE_2` rows, thin separator lines). Don't create popups that bypass it.

---

## 5. Color (dark theme)

| Token | Use |
|---|---|
| `BG` | Window background |
| `PANEL` | Sidebar, footer, dialogs |
| `CARD` / `CARD_HOVER` / `CARD_SELECTED` | Invoice cards (normal / hover / selected), text fields |
| `RAISED` (+ `_HOVER`, `_PRESS`) | Buttons, popups |
| `WELL` | Sunken areas: the preview behind the paper |
| `BORDER` / `BORDER_STRONG` / `BORDER_HOVER` / `BORDER_CHECK` | Hairlines, control borders, hover, empty checkbox |
| `TEXT` / `MUTED` / `FAINT` | Main text / secondary text / hints, labels, disabled |
| `ACCENT` (+ `_HOVER`, `_PRESS`) | Turquoise (Listo's is marigold). Selection, the one primary action, focus |
| `ON_ACCENT` | Text and icons on turquoise |
| `ACCENT_OFF` / `ACCENT_OFF_TEXT` | A disabled primary button |
| `ACCENT_TINT` / `ACCENT_EDGE` | Turquoise wash and outline (the Sent chip, the selected card) |
| `GOOD` / `WARN` / `BAD` | Paid / needs a look / overdue |
| `PAPER` / `SHADOW` | The invoice paper and its shadow in the preview |
| `BAD_TINT` / `BAD_EDGE` | Danger button hover / the Overdue chip |

- Turquoise means "selected" or "do this". **One** Primary button per view (Save PDF…, Save, Add Your Business…).
- Status color comes from data, not code: set `setProperty("tone", "draft" | "sent" | "overdue" | "paid")`
  and call `widgets.repolish(w)`. The stylesheet maps tone to color.
- Never call `setStyleSheet()` on a single widget. Add a rule to `theme.STYLESHEET`
  under an object name instead.

---

## 6. Components

Use an object name to pick a style (`btn.setObjectName("Ghost")`). These are the only variants:

| Kind | Object name | When |
|---|---|---|
| Primary button | `Primary` | The single main action in a view (Save PDF…, Save) |
| Normal button | *(none)* | Everything else (Print…, Choose Logo…, Cancel) |
| Secondary button | `Secondary` | Quiet buttons that still need a frame (Update to …) |
| Quiet button | `Ghost` | Show File, Mark as Sent, Use Business Defaults |
| Danger button | `Danger` | Destructive confirmations only (Delete Invoice, Delete Business…) |
| Icon-only button | `IconBtn` (QToolButton) | New invoice (+), ⋯ menus, remove line item (×). **Must** have a tooltip |
| Status chip | `Chip` (QLabel) | Draft / Sent / Overdue / Paid on an invoice card |
| Dropdown | `widgets.combo(items, current)` | **Every** pick-one setting, however few choices. Put extra detail in the item's tooltip |
| On/off setting | `widgets.ToggleRow` | Every on/off setting: one full-width row, label left, switch right, whole row clickable |
| Section | `widgets.Section` | Every labelled group in the details panel and dialogs |
| Multi-line text | `widgets.TextBox` | Addresses, line-item details, payment text, terms (`TEXT_BOX_H` or `TEXT_BOX_TALL`) |
| Date | `details.date_field()` | Every date (calendar popup, "Oct 10, 2026") |
| Fold-away group | `widgets.Disclosure` | Adjustments, Payment && Terms, Look: a chevron header with a summary |

Choosing a control:
- Pick one setting → **dropdown**, always, even with only 2–3 choices. Status, From, Payment Terms, Type,
  Color, Header, Paper and Logo Size are all dropdowns. Build them with `widgets.combo` / `set_combo`.
- The result of a choice is shown once, in the live preview, not repeated under every option.
- Actions that belong to a dropdown (Edit This Business…, Add a Business…, Pick a Color…, Fonts on This
  Computer…) go **inside** that dropdown, below a separator.
- Menus open from icon buttons (⋯) with `InstantPopup`; the menu arrow is hidden.

---

## 7. Words

Cobro talks like a helpful person, not like software.

- **Fewer words.** Labels and section titles are 1–4 words ("Name taken", not "If that name is already taken"). If something needs explaining, put it in a tooltip, not on screen.
- Plain language: "How to Pay", not "Remittance instructions". "Mark as Sent", not "Update status".
- **Title Case for labels**: section and group names, buttons, checkboxes, tabs, menu items, dropdown
  choices, dialog titles and card states ("Show Delivery Date", "Mark as Sent", "Payment Terms").
  Small words stay lowercase inside a label (a, an, the, and, or, of, to, in, on, at, for, by, with, as, per);
  acronyms and file things stay as they are (PDF, PNG, A4). No ALL-CAPS labels in the app (the invoice's small
  capital labels are part of the paper's design, §9).
- **Sentences stay sentences**: tooltips, hints, placeholders, error messages and toasts
  ("Applies to every invoice from Juniper Lane Films.").
- Buttons are verbs ("Save PDF…", "Show File"). Use "…" when the button opens a dialog or file picker.
- Errors say what happened and what to do, without jargon: "Cobro can't read logo.gif. Use a PNG, JPG or SVG file."
- Promise safety where it matters: "PDFs you already saved stay where they are."
- No exclamation marks, no emoji in the UI.

---

## 8. Layout of the main window

```
┌ ① Invoices (LIST_W) ·· + ┬ ② Details (DETAILS_W) ┬ ③ Preview ───────────────────────────┐
│ filter dropdown           │ Status · Paid On       │                                       │
│ invoice cards             │ From                   │      the invoice, page by page,       │
│   client · amount         │ Bill To                │      on the dark WELL, as wide as     │
│   number · date · chip    │ Invoice No. · Issued   │      the panel allows                 │
│                           │ Payment Terms          │                                       │
│                           │ Project                │                                       │
│                           │ Line Items             │                                       │
│                           │ ▸ Adjustments          │                                       │
│                           │ ▸ Payment && Terms     │                                       │
├ Unpaid · Paid in 2026 · ⋯ │ ▸ Look                 ├ Saved … · Show File · ⋯ · Print… · [ Save PDF… ]
└───────────────────────────┴────────────────────────┴───────────────────────────────────────┘
```
The window reads as three steps, left to right, in the order you work: **① pick or start an invoice →
② fill it in → ③ check it and send it out.** Every panel starts with a `widgets.StepHeader` (turquoise
number + Title Case name, `HEADER_H` tall) so the three line up. The preview takes the rest of the width.

- **Nothing to save by hand.** Edits are saved a moment after you stop typing (`SAVE_DELAY_MS`) and when you
  switch invoices or quit. The only "save" is the PDF.
- **Fill it in once.** The business (name, addresses, payment text, terms, look) is entered once, in the
  Business dialog, and starts every new invoice. Clients are remembered by name and offered as you type.
  Invoice numbers count up on their own (PREFIX-YEAR-001).
- **The details panel reads like the invoice**, top to bottom. Basic first; Adjustments, Payment && Terms and
  Look fold away (`widgets.Disclosure`), each remembered, each header saying what's set ("· 1 set", "· Edited",
  "· Modern · Ink Blue").
- **Look is live.** Fonts, color, header, paper and logo belong to the business and change the preview the
  moment you pick them. The Look group says which invoices it applies to.
- **Only show what applies.** Paid On only for paid invoices; logo size and "Show Name Next to Logo" only
  with a logo; the two font dropdowns only for Custom Fonts; Use Business Defaults only when the text differs.
- **Optional steps are buttons, not interruptions.** After saving a PDF, the bottom bar offers Show File and
  (for a draft) Mark as Sent. Saving never opens anything in your way.
- **Actions that remove things always ask** (Delete Invoice, Delete Business). Cancel is the default.
- **Menus hold commands, the panels hold settings.** File / Business / Help live in the Mac menu bar; on
  Windows and Linux the bar is hidden and the shortcuts still work. The same tools sit under ⋯ in the
  invoice list's bottom bar on every system.
- **Scrolling never changes a value** (`app._RoundPopups`), and **menus open on click, never on hover**.
- **One identity everywhere.** The app icon is the "cobro." wordmark on Listo's dark tile
  (`scripts/make_icon.py`); on the Mac the title bar is ours (`ui/titlebar.py`).

---

## 9. The invoice page

The paper is the product. It follows its own small set of rules (all in `doc/render.py`):

- Sizes are in **points** on the paper (Letter 612 × 792, A4 595 × 842), `MARGIN` 48 all round.
  Everything is laid out once and painted on any device, so the preview, PDF, PNG and print always match.
- Reading order: who it's from and **how much is due** (the biggest number on the page, in the accent) →
  the strip (Invoice / Issued / Terms / Due) → Bill To / From / Project → line items → totals → How to Pay
  and Terms → a footer on every page.
- Small labels on the paper are capitals with letter-spacing (`LABEL_SPACING`); everything else is sentence case.
- Ink is `INK`, secondary text `INK_SOFT`, hairlines `RULE` (core/looks.py). The accent appears only on the
  amount due, the balance and (with Color Band) the header. A pale accent is darkened until it reads on white.
- Type styles pair a heading face with a body face and a numbers face. Every bundled font is OFL and fixed-weight
  (`scripts/make_fonts.py`), so PDFs embed exactly what's on screen. Fonts from the computer are allowed too.
- Long invoices flow onto more pages: the table header repeats, totals and the payment/terms boxes are kept
  together, and every page gets "Page N of M".
- Exports are written to a temp file beside the target and moved into place when complete.

---

## 10. Checklist before you commit a UI change

1. No raw numbers or colors outside `tokens.py`. This should print nothing:
   `grep -nE '[^{_A-Z0-9][0-9]{2,}px|#[0-9A-Fa-f]{6}|rgba' cobro/ui/*.py | grep -v tokens.py`
   (1px hairline borders are the one allowed literal.)
2. New controls are `CONTROL_H` tall (or `SMALL_H` for icon buttons) and line up with their neighbours.
3. Every icon-only button has a tooltip.
4. Labels are short and in Title Case; sentences (tooltips, hints, messages) are plain sentences.
5. Screenshots look right: `QT_QPA_PLATFORM=offscreen python tests/screenshot.py OUTDIR`.
