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

All icons are line icons drawn as SVG in `theme._SVG` and made with `theme.icon(name, "MUTED")` (a color by
its token name, so the icon redraws itself when Cobro switches between light and dark).
Add new icons there; don't load image files for UI icons.

### Fixed layout sizes

`LIST_W`, `DETAILS_W`, `CARD_H`, `TEXT_BOX_H`, `TEXT_BOX_TALL`, `NUM_FIELD_W`, `SWATCH`, `LOGO_THUMB`,
`PAGE_GAP`, `PAGE_SHADOW`, `DIALOG_W`, `PROFILE_DIALOG_H`, `WINDOW_SIZE`, `WINDOW_MIN`. Use these names, never the numbers.

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

## 5. Color (light and dark)

Cobro is light or dark, as the computer is set, and switches along with it while it's open
(`app.apply_scheme`). `tokens.py` has two palettes with the same names: `DARK` (Listo's) and `LIGHT`
(the same jobs on white; turquoise and the status colors are deeper there so they still read).
Read a color through `tokens.C` (`C.TEXT`, `C.ACCENT`) at the moment you draw it, never keep one in a
variable of your own, and check every change in both (§10).

| Token | Use |
|---|---|
| `BG` | Window background |
| `PANEL` | Sidebar, footer, dialogs |
| `CARD` / `CARD_HOVER` / `CARD_SELECTED` | Invoice cards (normal / hover / selected), text fields |
| `RAISED` (+ `_HOVER`, `_PRESS`) | Buttons, popups |
| `HOVER` | Behind an icon-only button you point at |
| `WELL` | Sunken areas: the preview behind the paper |
| `BORDER` / `BORDER_STRONG` / `BORDER_HOVER` / `BORDER_CHECK` | Hairlines and progress tracks, control borders, hover, empty checkbox |
| `TEXT` / `MUTED` / `FAINT` | Main text / secondary text / hints, labels, disabled |
| `ACCENT` (+ `_HOVER`, `_PRESS`) | Turquoise (Listo's is marigold). Selection, the one primary action, focus |
| `ON_ACCENT` | Text and icons on turquoise |
| `ACCENT_OFF` / `ACCENT_OFF_TEXT` | A disabled primary button |
| `ACCENT_TINT` / `ACCENT_EDGE` | Turquoise wash and outline (the Sent chip, the selected card) |
| `GOOD` / `WARN` / `BAD` | Paid / needs a look / overdue |
| `PAPER` / `SHADOW` | The invoice paper and its shadow in the preview |
| `BAD_TINT` / `BAD_EDGE` | Danger button hover / the Overdue chip |

- Turquoise means "selected" or "do this". **One** Primary button per view (Save PDF…, Save, Add Your Profile…).
- Status color comes from data, not code: set `setProperty("tone", "draft" | "sent" | "overdue" | "paid")`
  and call `widgets.repolish(w)`. The stylesheet maps tone to color.
- Never call `setStyleSheet()` on a single widget. Add a rule to the stylesheet in `theme._rules()`
  under an object name instead.
- Rich text can't follow the stylesheet: the wordmark is `widgets.Wordmark`, which colors its dot again
  after a switch. An icon on its own (not on a button) is `widgets.IconLabel`.

---

## 6. Components

Use an object name to pick a style (`btn.setObjectName("Ghost")`). These are the only variants:

| Kind | Object name | When |
|---|---|---|
| Primary button | `Primary` | The single main action in a view (Save PDF…, Save) |
| Normal button | *(none)* | Everything else (Print…, Choose Logo…, Cancel) |
| Secondary button | `Secondary` | Quiet buttons that still need a frame (Update to …) |
| Quiet button | `Ghost` | Show File, Mark as Sent, Use Profile Defaults, Remove (the logo, in the profile) |
| Danger button | `Danger` | Destructive confirmations only (Delete Invoice, Delete Profile…, Delete Client…) |
| Icon-only button | `IconBtn` (QToolButton) | New invoice (+), ⋯ menus (a line item has one too), the Dark Page moon. **Must** have a tooltip |
| Status chip | `Chip` (QLabel) | Draft / Sent / Overdue / Paid on an invoice card |
| Dropdown | `widgets.combo(items, current)` | **Every** pick-one setting, however few choices. Put extra detail in the item's tooltip |
| On/off setting | `widgets.ToggleRow` | Every on/off setting: one full-width row, label left, switch right, whole row clickable |
| Section | `widgets.Section` | Every labelled group in the details panel and dialogs |
| Multi-line text | `widgets.TextBox` | Addresses, line-item details, payment text, terms (`TEXT_BOX_H` or `TEXT_BOX_TALL`) |
| Date | `details.date_field()` | Every date (calendar popup, "Oct 10, 2026") |
| Fold-away group | `widgets.Disclosure` | Every group in the Details panel and the profile dialog: a chevron header that, folded, says what's inside |
| Your own things | `details.picker()` + an `Edit…` button | From (your profiles) and Bill To (your clients): the dropdown picks, Edit… beside it opens the details |
| Line item | `details.ItemEditor` | A header row (what it is, its amount, ⋯) that folds its fields away. One open at a time |
| Long one-line text | `widgets.ElidedLabel` | Text that may not fit (a line item's name): cut short with "…", the full text in its tooltip |

Choosing a control:
- Pick one setting → **dropdown**, always, even with only 2–3 choices. Status, From, Bill To, Payment Terms, Number Style, Type,
  Color, Header, Paper and Logo Size are all dropdowns. Build them with `widgets.combo` / `set_combo`.
- The result of a choice is shown once, in the live preview, not repeated under every option.
- Actions that belong to a dropdown (Add a Profile…, New Client…, Pick a Color…, Fonts on This
  Computer…) go **inside** that dropdown, below a separator.
- A dropdown of your own things that have details of their own (profiles, clients) also gets an **Edit…** button
  right beside it. That's where people look for it; an "Edit" hidden inside the list went unfound.
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
┌ ① Invoices (LIST_W) ··· + ┬ ② Details (DETAILS_W) ──────┬ ③ Preview ························ ☾ ┐
│ filter dropdown           │ ▾ From && Bill To           │                                      │
│ invoice cards             │   From    [profile ▾] Edit… │      the invoice, page by page,      │
│   client · amount         │   Bill To [client ▾]  Edit… │      on the WELL, as wide as         │
│   number · date · chip    │ ▾ Invoice                   │      the panel allows: white paper,  │
│                           │   Status · Paid On          │      or the Dark Page (☾)            │
│                           │   Invoice No. · Issued      │                                      │
│                           │   Payment Terms             │                                      │
│                           │ ▾ Project                   │                                      │
│                           │ ▾ Line Items                │                                      │
│                           │   › Production  $1,500  ⋯   │                                      │
│                           │   + Add Line Item           │                                      │
│                           │ ▸ Adjustments · 1 set       │                                      │
│                           │ ▸ Payment && Terms          │                                      │
├ Unpaid · Paid in 2026 · ⋯ │ ▸ Look · Modern · Ink Blue  ├ Saved … · Show File · ⋯ · Print… · [ Save PDF… ]
└───────────────────────────┴─────────────────────────────┴──────────────────────────────────────┘
```
The window reads as three steps, left to right, in the order you work: **① pick or start an invoice →
② fill it in → ③ check it and send it out.** Every panel starts with a `widgets.StepHeader` (turquoise
number + Title Case name, `HEADER_H` tall) so the three line up. The preview takes the rest of the width.

- **Nothing to save by hand.** Edits are saved a moment after you stop typing (`SAVE_DELAY_MS`) and when you
  switch invoices or quit. The only "save" is the PDF.
- **Fill it in once.** Your **profile** (name, logo, addresses, payment text, terms, numbering; a `Business`
  in the code) is entered once, in the Profile dialog, and picked under From. Keep one per name you invoice
  from. Your **clients** are saved once, in the Client dialog (New Client… under Bill To), and picked under
  Bill To. Drafts follow a client's edits; sent and paid invoices keep what they said. Typing never saves
  a client by itself.
- **Numbers count up on their own**, per profile: PREFIX-YEAR-001, or one count per client
  (PREFIX-CODE-YEAR-001, or CODE-YEAR-001), picked under the profile's Number Style. A draft's number follows
  its client until you type your own; sent and paid invoices never change number.
- **The details panel reads like the invoice**, top to bottom, and **every part folds away**
  (`widgets.Disclosure`), each remembered. A folded header says what's inside ("· JLF-2026-001 · Draft",
  "· 3 items · $2,700.00", "· Modern · Ink Blue"), so nothing that changes the invoice hides silently.
  Basic groups start open; Adjustments, Payment && Terms and Look start folded.
- **A long list stays tidy.** Line items fold to one row each (name, amount, ⋯) and only one is open at a
  time. Duplicate, Move Up, Move Down and Remove live in the item's ⋯ menu.
- **Look is live.** Fonts, color, header and paper belong to the profile and change the preview the
  moment you pick them. The Look group says which invoices it applies to. The logo is part of the profile.
- **Only show what applies.** Paid On only for paid invoices; logo size and "Show Name Next to Logo" only
  with a logo; the two font dropdowns only for Custom Fonts; Use Profile Defaults only when the text differs;
  Edit… beside Bill To only once a client is picked; a client's Code only when a profile counts per client.
- **Optional steps are buttons, not interruptions.** After saving a PDF, the bottom bar offers Show File and
  (for a draft) Mark as Sent. Saving never opens anything in your way.
- **Removing goes through a menu or a confirmation, never a single click** (Listo's rule). Remove a line item
  from its ⋯ menu; Delete Invoice, Delete Profile and Delete Client ask first, with Cancel as the default.
- **Menus hold commands, the panels hold settings.** File / Profile / Help live in the Mac menu bar; on
  Windows and Linux the bar is hidden and the shortcuts still work. The same tools sit under ⋯ in the
  invoice list's bottom bar on every system.
- **Scrolling never changes a value**: the wheel over a dropdown, a date or a slider scrolls the panel
  (`app._RoundPopups`). **Menus open on click, never on hover**.
- **The Dark Page is for your eyes only.** The moon in the preview's header shows the same page, laid out
  exactly the same, in light-on-dark colors (`looks.DARK`), remembered. PDF, PNG and print always use white
  paper (`MainWindow.pages()` is light unless the preview asks). Logos get a small white card on the Dark Page,
  since most are made for white paper.
- **Light or dark, as the computer is set.** The whole window follows the system's Light / Dark setting,
  and switches with it while Cobro is open (by hand, or on its own at sunset). The Dark Page is separate:
  it's about the invoice, not the window, and keeps its own moon in either.
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
- Ink is `INK`, secondary text `INK_SOFT`, hairlines `RULE` (core/looks.py `LIGHT`; the preview's Dark Page
  swaps in `DARK`). The accent appears only on the amount due, the balance and (with Color Band) the header.
  An accent is darkened (or, on the Dark Page, lightened) until it reads on the paper.
- The business name sits on one line when it fits, measured exactly as it's drawn and with `NAME_SLACK` to
  spare (text measures a hair differently on each computer); only a name too long even at the smallest size
  wraps. The logo and the name block are centred on each other.
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
5. Screenshots look right, in dark and in light: `QT_QPA_PLATFORM=offscreen python tests/screenshot.py OUTDIR`
   (it takes each one twice; the light ones end in `-light`).
