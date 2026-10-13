# Cobro design rules

The rules for how Cobro looks and reads. Follow them for every screen, dialog and control.
If a change needs something these rules don't cover, add a rule here in the same commit.

All numbers and colors live in **`cobro/ui/style/tokens.py`**. The stylesheet (`cobro/ui/style/theme.py`) and
every widget read from there. **Never type a size, spacing, font size or color anywhere else.**
If you need a value that doesn't exist, add a token, give it a comment, and add it to the tables below.
The paper (the invoice itself) has its own colors and sizes in `cobro/core/looks.py` and `cobro/doc/render.py` (§9).

---

## 1. Sizes

### Controls: one height for everything you click or type in

| Token | px | Used for |
|---|---|---|
| `CONTROL_H` | 34 | **Every** button, dropdown, text field, round icon button and segmented control |
| `SMALL_H` | 24 | Small icon buttons inside a row or card (a line item's ⋯), the shortest table column |
| `INDICATOR` | 16 | Standard icon box |
| `TOGGLE_ROW_H` · `TOGGLE_W`×`TOGGLE_H` | 32 · 36×20 | An on/off row and its switch |
| `BAR_H` | 6 | Progress bars |
| `TRACK_H` / `HANDLE` | 4 / 14 | Slider groove (and the assistant's progress bar) / handle |
| `SCROLL_W` / `SCROLL_MIN` | 10 / 30 | Scrollbar width / shortest handle |

- A button, a dropdown and a text field side by side must line up exactly. Never set a height on a single control;
  the stylesheet already sets it.
- Buttons size their width to their text (padding `0 SPACE_3`). Don't give buttons fixed widths.

### Icons

| Token | px | Used for |
|---|---|---|
| `ICON_SM` | 14 | Icons inside small buttons, chips and rows |
| `ICON` | 16 | Icons inside normal buttons and menus |
| `ICON_LG` | 20 | The assistant's bubble in the toolbar (it fills its circle) |

All icons are line icons on a 24×24 grid, stroke 2, drawn as SVG in `theme._SVG` and made with
`theme.icon(name, color)` (buttons) or `theme.menu_icon(name)` (menus), or `widgets.IconLabel(name, tone)` for an
icon that isn't a button. They follow light, dark and the accent by themselves; never draw an icon once with a color
and keep the picture, and never load image files for UI icons. An icon on the accent (the round +) is drawn in
`ON_ACCENT`, which is dark on a light accent. `tests/test_icons.py` checks every name the code uses exists.

### Fixed layout sizes

`SIDEBAR_W` (232), `INSPECTOR_W` (420, never under `INSPECTOR_MIN` 360), `TOOLBAR_H` (64), `SEARCH_W`,
`TABLE_ROW_H` (34), `COL_W` (every table column), `NAME_MIN`, `GIVE_WAY` (the columns that step aside on a narrow
window), `NAV_H`, `PROFILE_CARD_H`, `AVATAR`, `TEXT_BOX_H`, `TEXT_BOX_TALL`, `NUM_FIELD_W`, `QTY_FIELD_W`,
`LOGO_THUMB`, `PAGE_GAP`, `PAGE_SHADOW`, `DIALOG_W` (and `DIALOG_W_WIDE`, `DIALOG_W_XWIDE`), `PROFILE_DIALOG_H`,
`PAGE_DIALOG_SIZE`, `ALERT_W`, `ALERT_ICON`, `REVIEW_W`, `REVIEW_COL_W`, `START_TILE_W`, `START_BADGE`, `NOTES_H`,
`NOTES_LINE`, `CLIENT_GIVE_WAY`, `GRIP_W`, `GRIP_GAP`, `GRIP_DOT`, `LIFT_STEP_MS`, `LIFT_EASE`, `LIFT_SHADOW_STEPS`, `TOAST_MAX_W`,
`TOAST_RISE`, `TOAST_LIFT`, `WINDOW_SIZE`, `WINDOW_MIN`. Timings too: `DOCK_MS`, `FADE_MS`, `SAVE_DELAY_MS`,
`TABLE_DELAY_MS`, `DRAW_DELAY_MS`, `TOAST_MS` (and `TOAST_MS_PER_CHAR`, `TOAST_IN_MS`, `TOAST_OUT_MS`),
`UPDATE_CHECK_DELAY_MS`, `UPDATE_WAIT_MS`, `QUIT_WAIT_MS`. Use these names, never the numbers.

**Fonts:** one family, Inter (`looks.FONT`, shared with the paper), loaded once in `app.py`. Every size is a
`TEXT_*` token and every weight a `WEIGHT_*` token; make a font with `theme.font(size, weight)`, never `QFont()` or
`setBold`.

---

## 2. Spacing: a 4-point grid

| Token | px | Use it for |
|---|---|---|
| `SPACE_1` | 4 | A label and its control; an icon and its text; lines inside one item |
| `SPACE_2` | 8 | Related items: buttons in a row, line items in a list |
| `SPACE_3` | 12 | Between sections inside a panel |
| `SPACE_4` | 16 | Padding of panels, bars and the main areas |
| `SPACE_5` | 24 | Padding of dialogs, empty states |

- Build layouts with the helpers in `cobro/ui/components/widgets.py`: `vbox(widget, margins, spacing)` /
  `hbox(...)` (spacing defaults to `SPACE_2`), `combo(...)` for dropdowns, and `Section("Title")` for a labelled
  group (Title Case label + its controls, `SPACE_1` apart).
- Margins are `SPACE_*` tokens or `0`. Nothing else. The glass panels sit `GLASS_GAP` (10) from the window's edge
  and from each other.

---

## 3. Type

| Token | px | Used for |
|---|---|---|
| `TEXT_XS` | 11 | Chips |
| `TEXT_SM` | 12 | Section labels (semibold), secondary text: hints, tooltips, the amount on a folded line item |
| `TEXT_MD` | 13 | Body text and every control (the default) |
| `TEXT_LG` | 14 | Emphasis: the profile card's name, alert titles, totals under the table |
| `TEXT_XL` | 18 | Dialog titles, empty-state headlines |
| `TEXT_BRAND` | 21 | The "cobro." wordmark only |

Weights: `WEIGHT_REGULAR` 400 for text, `WEIGHT_MEDIUM` 500 for controls, `WEIGHT_SEMIBOLD` 600 for titles,
labels and the primary button, `WEIGHT_BOLD` 700 for the wordmark and page titles.

---

## 4. Corners

| Token | px | Used for |
|---|---|---|
| `RADIUS_XS` | 4 | Small inner corners |
| `RADIUS_SM` | 6 | Chips, small buttons |
| `RADIUS` | 8 | Fields, dropdowns, segmented controls (text buttons are capsules, icon buttons circles) |
| `RADIUS_LG` | 12 | Cards on the glass, line item boxes, alerts |
| `GLASS_R` | 18 | The glass panels (sidebar, right panel, Settings' sidebar) |

**Every list of choices looks the same as the sidebar and Settings**: menus and dropdown lists. The list's corners are `LIST_R` (= `GLASS_R`), rows sit `LIST_INSET` (10) inside it with corners
`LIST_ROW_R` (8, concentric), `LIST_ROW_H` (30) tall, `LIST_GAP` (2) apart. Hover is `CARD_HOVER`; the highlighted or
picked row is `ACCENT_TINT` with its words and icon in `ACCENT_HOVER`. Never give a list its own sizes.
`app._RoundPopups` makes every menu and dropdown window see-through, opens it just below its button with
`MENU_GAP` of air (lined up with the button's right edge in the right half of the window), and gives dropdowns
`widgets.ComboItemDelegate`. Don't create popups that bypass it.

---

## 5. Color (dark and light)

Cobro follows the computer's light or dark setting, switching live, or keeps the one picked in Settings › General
› Appearance (settings "appearance": system / light / dark). Every color token has a dark and a light value
(`tokens.DARK`, `tokens.LIGHT`); `tokens.use()` swaps them and `theme.apply()` rebuilds the stylesheet. So: read
colors as `tokens.X` when drawing, never copy one into a constant at import time. Both are read before the first
window opens, so Cobro never flashes in the wrong colors.

**The accent is yours to pick** (Settings › General › Accent Color: `widgets.AccentPicker`, settings "accent";
empty means Cobro's own turquoise, `#3CC8B4` on dark, `#0F8574` on light). `tokens.ACCENTS` lists the choices:
Turquoise, Blue, Purple, Pink, Orange, Yellow, Green, Graphite (never red: red means overdue or delete).
`tokens.accent_set()` builds every accent shade from one color, with dark words on the accent wherever white
wouldn't read. The accent never touches the paper: an invoice looks the same on every computer.

**The glass is one even tone**: no gradient anywhere, only a thin bright rim along its top edge (`GLASS_EDGE`),
one hairline round it (`GLASS_STROKE`) and a soft shadow under it (`GLASS_SHADOW`).

**The light look is the Mac's**: the main area, dialogs and Settings' pages are pure white; the sidebar, the right
panel and Settings' sidebar are a soft gray glass; cards on that glass are white (`BLOCK`); lines and shadows are
neutral gray.

| Token | Use |
|---|---|
| `BG` / `PANEL` | Window background, dialogs |
| `GLASS` / `GLASS_EDGE` / `GLASS_STROKE` / `GLASS_SHADOW` | The glass panels |
| `BLOCK` / `FILL` / `WELL` | Cards on the glass / something soft on the white page / the page window behind the paper |
| `CARD` / `CARD_HOVER` / `CARD_SELECTED` / `ROW_HOVER` | Rows: normal / hover / picked / a table row under the mouse |
| `FIELD` / `FIELD_BORDER` | Text fields, dropdowns, line item boxes |
| `RAISED` (+ `_HOVER`, `_PRESS`) | Buttons, popups |
| `BORDER` / `BORDER_STRONG` / `BORDER_HOVER` / `BORDER_CHECK` | Hairlines, control borders, hover, empty checkbox |
| `TEXT` / `MUTED` / `FAINT` | Main text / secondary text / hints, labels, disabled |
| `ACCENT` (+ `_HOVER`, `_PRESS`) | Selection, the one primary action, focus |
| `ON_ACCENT` | Words and icons on the accent |
| `ACCENT_OFF` / `ACCENT_OFF_TEXT` | A disabled primary button |
| `ACCENT_TINT` / `ACCENT_EDGE` | Accent wash and outline (a picked list row, the filter while it's on) |
| `CHIP` / `CHIP_HOVER` | "+ Add" capsules (Add Line Item, + Discount) |
| `DIVIDER` / `DIVIDER_HOVER` / `DIVIDER_TEXT` | The table's month or client bands |
| `GOOD` / `WARN` / `BAD` (+ `BAD_TINT`, `BAD_EDGE`) | Paid / sent and waiting / overdue, delete |
| `PAPER` / `SHADOW` | The paper and its shadow in the page window |
| `TOAST` / `TOAST_TEXT` / `TOAST_EDGE` / `TOAST_SHADOW` | A toast: a lighter card in dark, a dark card on the white page in light, so it's never missed |
| `TOAST_DONE` / `TOAST_PROBLEM` (+ `_FILL`, `_EDGE`) | Its icon when something worked (Paid's green); when it didn't (amber icon on an amber-tinted toast) |

- The accent means "selected" or "do this". **One** Primary button per view (Save PDF…, Save, Invoice…).
- **Status reads at a glance**: Draft `MUTED`, Sent `WARN`, Overdue `BAD`, Paid `GOOD`
  (`window/common.STATUS_COLORS`), the same in the table, the sidebar's Unpaid count and the totals.
- Never call `setStyleSheet()` on a single widget. Add a rule to `theme`'s stylesheet under an object name.

---

## 6. Components

Use an object name to pick a style (`btn.setObjectName("Ghost")`). These are the only variants. Every text button
is a capsule `CONTROL_H` tall; every icon button is a circle:

| Kind | Object name | When |
|---|---|---|
| Primary button | `Primary` | The single main action in a view (Save PDF…, Save, Invoice…, Add Your Profile…) |
| Normal button | *(none)* | Everything else (Print…, Edit…, Cancel, Show File, Load Models) |
| Quiet button | `Ghost` | Small helpers inside a card (Use Profile Defaults, Make These the Defaults) |
| Add button | `AddChip` (`widgets.add_chip`) | "+ Add Line Item", "+ Discount", "+ Details", "+ Connect an AI" |
| Danger button | `Danger` | Destructive actions in a form (Delete Profile…, Delete Client…): the normal shape, red words |
| Alert's yes | `DangerFill` | Only the destructive button of an Alert (Delete) |
| Link | `LinkBtn` | Inline text links (Get a Key ↗, Forgot your password?) |
| Round icon button | `#Circle`, `#CirclePrimary` (the +) | Every icon button in the toolbar or a panel header (✕, ⋯, filter, share, the bubble, the moon). **Must** have a tooltip |
| Small icon button | `widgets.icon_button()` (`#IconBtn`) | Icon buttons inside a row or card (a line item's ⋯, an adjustment's ×) |
| Left panel | `panels.LeftPanel` (+ `NavRow`) | Every list of places on the left (the sidebar, Settings). A row with rows under it (All Invoices, All Clients) has an arrow that folds them; the rows under it (`NavRow.as_child()`, `#NavSub`) drop their icon so their names start where its icon is. The picked row is tinted, its name in the accent |
| Right panel | `panels.SidePanel` | Every panel on the right (the invoice, a client, the assistant); `header_icon()` for its own round buttons |
| Panel header | `widgets.PanelHeader` + `add_close()` | Title at the left; round ⋯ (or ⚙), then the round ✕ at the far right |
| Profile card | `sidebar.ProfileCard` | The bottom of the sidebar: initials in a circle and the profile's name; click for its menu |
| Table | `tables.Table` (`QTreeWidget#Table`): `InvoiceTable`, `ClientTable` | `TABLE_ROW_H` rows, sortable columns, one rounded highlight per row (a delegate paints it), columns that step aside on a narrow window. The invoices also have bands that fold and pick many; the clients sort A to Z and are picked one at a time |
| Filter | `filters.FilterButton` | Right after the search: just the icon, the accent while a filter hides something |
| Dropdown | `widgets.combo(items, current)` | **Every** pick-one setting, however few choices. Extra detail in the item's tooltip |
| On/off setting | `widgets.ToggleRow` | Every on/off setting: one full-width row, label left, switch right, whole row clickable |
| Section | `widgets.Section` | Every labelled group in the panels and dialogs |
| Multi-line text | `widgets.TextBox` | Addresses, line-item details, payment text, terms |
| How many | `widgets.qty_field()` | A line item's Qty: typed (2.5 is fine), arrow keys count up and down |
| Money | `widgets.MoneyField` | Rates, discount, deposit |
| Date | `widgets.date_field()` | Every date (calendar popup, "Tue, Oct 13, 2026") |
| Fold-away group | `widgets.Disclosure` | Every group in the invoice and client panels and the profile: folded, it says what's inside |
| Big name | `widgets.TitleEdit` (`#BigName`) | A client's name as their panel's title: edited in place, wraps onto a second line instead of being cut off |
| A client's invoice | `client.InvoiceLine` (`#InvoiceLine`) | One of their invoices in their panel: number, date and project, its status in its color (`#LineStatus`), its amount; click to open it |
| Your own things | `widgets.picker()` + an `Edit…` button | From (your profiles) and Bill To (your clients) |
| Line item | `invoice.LineEditor` | A header row (grip, what it is, its amount, ⋯) that folds its fields away. One open at a time |
| Drag to reorder | `lift.Grip` + `lift.StackLift` | The six dots on a line item (only with two or more): the item lifts onto a raised card with a soft shadow and an accent edge, the others ease apart (`LIFT_EASE` every `LIFT_STEP_MS`) to show its slot, the panel scrolls near its edges, Esc puts it back |
| Long one-line text | `widgets.ElidedLabel` | Text that may not fit: cut short with "…", the full text in its tooltip |
| Alert | `dialogs.common.Alert` (`confirm`, `notice`) | Every "are you sure", and every error that needs more than a toast |
| Toast | `widgets.Toast`, through `MainWindow.toast(text, tone)` | A few words saying what just happened, never a question: centred over the page just above the totals, it rises and fades in, the pointer resting on it keeps it, and it never takes a click (what's under it still works). `tone`: "done" (a green check: Copied, Saved, Deleted), "problem" (amber: it didn't work, and the words say what to do), or "" for news (an info sign: Nothing to undo) |
| Wrapping row | `widgets.FlowLayout` | A row of + buttons that wraps onto a second line in a narrow panel |
| Empty page | `empty.EmptyPage` | Where the table would be with nothing in it: only its start tiles, centred (no headline; the page title says where you are). Search and the filter hide while it shows |
| Start tile | `empty.StartTile` (`#StartTile`) | Every way to begin on an empty page (Add Your Profile…, New Invoice with the place's sidebar icon, Clear Filters): a raised `RADIUS_LG` tile, its icon in a small tinted circle, a name and a few words, all centred |
| What's new | `update.Notes` (`#WhatsNew`) | The update window's notes, read from the release (this version's CHANGELOG): a soft `FILL` box only as tall as its words (up to `NOTES_H`, then it scrolls); each section a small label, each change an accent dot and its words at `NOTES_LINE` line height. Release text is escaped, never read as HTML; only https links open |
| Dialog buttons | `widgets.button_row()` | The bottom row of every dialog: right-aligned, the main one last |

Choosing a control:
- Pick one setting → **dropdown**, always, even with only 2–3 choices. Status, From, Bill To, Payment Terms, Number
  Style, Paper Color, Header, Paper Size and Logo Size are all dropdowns.
- Actions that belong to a dropdown (Add a Profile…, New Client…) go **inside** that dropdown, below a separator.
- A dropdown of your own things that have details of their own (profiles, clients) also gets an **Edit…** button
  right beside it.
- Menus open from icon buttons (⋯) on a click, never on hover; the menu arrow is hidden.

---

## 7. Words

Cobro talks like a helpful person, not like software.

- **No explaining on screen.** No hint sentences under fields, no paragraphs in empty states or dialogs. If a label
  needs explaining, change the label; if it still does, a short tooltip.
- **Fewer words.** Labels and section titles are 1–4 words. Plain language: "How to Pay", not "Remittance
  instructions"; "Mark as Sent", not "Update status".
- **Title Case for labels**: section and group names, buttons, menu items, dropdown choices, dialog titles ("Show
  Delivery Date", "Mark as Sent", "Payment Terms"). Small words stay lowercase inside a label (a, an, the, and, or,
  of, to, in, on, at, for, by, with, as, per); acronyms and file things stay as they are (PDF, PNG, CSV, A4). No
  ALL-CAPS labels in the app (the paper's small capital labels are part of the paper's design, §9).
- **Sentences stay sentences**: tooltips, placeholders, error messages and toasts.
- Buttons are verbs ("Save PDF…", "Show File"). Use "…" when the button opens a window or a file picker.
- Errors say what happened and what to do: "Cobro can't read logo.gif. Use a PNG, JPG or SVG file."
- Promise safety where it matters: "PDFs you already saved stay where they are."
- No exclamation marks except a greeting ("Hi! What can I help with?"), no emoji, no jargon.
- No company or personal brand names in the app, the About box or the installers (the developer's name is fine in
  the copyright line).

---

## 8. Layout of the main window

```
╭ sidebar (glass) ─╮ ┌ toolbar ─────────────────────────────────────────────────┐ ╭ right panel (glass) ─╮
│ cobro.           │ │ All Invoices 4    [ Search            ] (≡)   (⇪) (☺) (+) │ │ Invoice       (⋯) (✕)│
│                  │ ├──────────────────────────────────────────────────────────┤ │ ▾ From & Bill To     │
│ Invoices      +  │ │ Invoice   Client          Issued   Due    Status  Amount │ │ ▾ Invoice            │
│ ⌄ All Invoices 4 │ │ ▾ October 2026                                 $5,400.00 │ │ ▾ Project            │
│     Drafts     1 │ │   JLF-001 Northwind Media Oct 13   Oct 28  Draft  $2,700 │ │ ▾ Line Items         │
│     Unpaid     2 │ │   JLF-002 Desert Sun …    Oct 8    Oct 23  Sent   $2,700 │ │   › Production  ⋯    │
│     Paid       1 │ │ ▾ September 2026                               $1,500.00 │ │   + Add Line Item    │
│ Clients       +  │ │   JLF-003 Mesa Coffee Co. Sep 3    Sep 18  Overdue $1,500│ │ ▸ Adjustments        │
│ › All Clients  3 │ │                                                          │ │ ▸ Payment & Terms    │
│ (JL) Juniper …   │ │            Unpaid $4,200 · Overdue $1,500 · Paid · Total │ │ [     Invoice…     ] │
╰──────────────────╯ └──────────────────────────────────────────────────────────┘ ╰──────────────────────╯
```

- **Left: where you are.** The sidebar's places filter the table: All Invoices, with Drafts, Unpaid (sent and
  overdue; its count turns amber while invoices wait and red once one is overdue) and Paid under it; then All
  Clients, with each client under it (click one to open it). The arrow beside All Invoices or All Clients folds
  what's under it (folded, All Invoices' count takes Unpaid's color), a click on a heading folds the whole
  section, and every fold is remembered. Each section heading has its own + (New Invoice, New Client).
- **Middle: everything at once.** One table, sortable by every column. Bands by month (the newest on top) or by
  client, each with its total, fold with a click (remembered). Columns step aside on a narrow window
  (`GIVE_WAY`) so client names keep `NAME_MIN`. The totals underneath add up what's showing. In All Clients the
  table is your clients (Attention, Email, how many invoices, what's unpaid in Sent's or Overdue's color, what
  you've billed in all; `CLIENT_GIVE_WAY` on a narrow window); the filter, share and totals step aside there.
- **Right: the one you picked.** It slides in over `DOCK_MS` (and the table slides with it); Esc, ✕ or a click on
  empty space puts it away. The invoice panel reads like the invoice, top to bottom, and **every part folds away**
  (`widgets.Disclosure`), each remembered; a folded header says what's inside ("JLF-2026-001 · Draft", "3 items ·
  $2,700.00"). Basic groups start open; Adjustments and Payment && Terms start folded. A client's panel has their
  name as its title (`TitleEdit`), then Contact, Invoice Numbers (only when a profile counts per client) and
  their Invoices (what's unpaid and billed, then each one; click to open it), and New Invoice across the bottom.
- **The toolbar, right to left**: the round + (New Invoice; New Client in All Clients) at the far right, then the assistant's bubble, then
  share (Invoice…, Export as CSV…, Back Up…). The filter sits right after the search. Nothing else.
- **Nothing to save by hand.** Edits save themselves a moment after you stop typing (`SAVE_DELAY_MS`), when you
  switch invoices and when you quit. The only "save" is the PDF.
- **An empty place shows the ways to start**, as tiles (`EmptyPage`): Add Your Profile… the first time, then New
  Invoice (with the place's icon), New Client in All Clients, or Clear Filters when a filter hides everything.
- **A new invoice you leave empty isn't kept** (Esc, or opening something else), and leaves no undo step.
- **Fill it in once.** Your **profile** (name, logo, addresses, payment text, terms, numbering, the paper's look; a
  `Business` in the code) lives in Settings › Profiles and is picked under From. Your **clients** are saved once
  (New Client in All Clients, or New Client… under Bill To) and picked under Bill To; change one in their panel
  (or Edit… beside Bill To) and drafts follow. Typing under Bill To never saves a client by itself, and a new
  client in All Clients is kept only once it has a name no other client has.
- **Numbers count up on their own**, per profile: PREFIX-YEAR-001, or one count per client (PREFIX-CODE-YEAR-001,
  or CODE-YEAR-001). A draft's number follows its client until you type your own; sent and paid invoices never
  change number.
- **A long list stays tidy.** Line items fold to one row each (grip, name, amount, ⋯), one open at a time. Drag one
  by its grip to reorder (it folds while it travels); Duplicate, Move Up, Move Down and Remove live in its ⋯ menu.
  The invoice table has no grip: invoices are always in the order you sort them by.
- **Only show what applies.** Paid On only for paid invoices; Discount, Deposit Paid and Sales Tax only when the
  invoice has them (+ Discount adds one, × takes an empty one off); a line item's details once it has some
  (+ Details); Overdue under the table only when something is; Use Profile Defaults only when the text differs;
  Edit… beside Bill To only once a client is picked; a client's Code only when a profile counts per client.
- **Removing goes through a menu or an alert, never a single click.** The Alert is narrow (`ALERT_W`), the app icon
  at the top, a bold question, one short line, Cancel and the action side by side. Return does it, Esc cancels.
- **Undo / Redo** (⌘Z / ⇧⌘Z; Ctrl+Y too on Windows) cover every change to invoices, clients and profiles; in a text
  box they undo the typing instead.
- **Scrolling never changes a value**: the wheel over a dropdown or a date scrolls the panel.
- **The page opens in its own window**, never in the way of editing: Save PDF…, Print…, ⋯, and after saving Show
  File, Email Client and (for a draft) Mark as Sent. The moon shows the **Dark Page**: the same layout in
  light-on-dark colors (`looks.DARK`), remembered, for your eyes only; PDF, PNG and print are always white paper.
- **Settings (⌘,)** is one window with its own glass sidebar, each section edited right there; changes apply as you
  make them, Esc closes it. General · Profiles · AI · Account · Keyboard Shortcuts · Your Data.
- **The assistant** is the right-hand panel too: the bubble or ⌘J slides it in and it stays while you move around;
  clicking an invoice shows the invoice instead, and the bubble brings the chat back. It works on the invoice you
  last opened, and every change it suggests waits in the Review window.
- **One identity everywhere.** The app icon is "c." on the dark tile, the full stop in turquoise
  (`scripts/make_icon.py`); the wordmark is "cobro." with the full stop in the accent; on the Mac the title bar is
  Cobro's own (`components/titlebar.py`).

---

## 9. The paper

The paper is the product. It follows its own small set of rules (all in `doc/render.py` and `core/looks.py`):

- Sizes are in **points** on the paper (Letter 612 × 792, A4 595 × 842), `MARGIN` 44 all round. Everything is
  laid out once and painted on any device, so the page window, PDF, PNG and print always match.
- Reading order: who it's from (logo, name, tagline) with **the amount due** large on the right in the paper's
  accent → the strip of four facts (Invoice / Issued / Terms / Due) → Bill To / From / Project → the line items →
  totals → How to Pay and Terms → a footer on every page (the closing note, "Page N of M", the contact line).
- **Inter** throughout; **IBM Plex Mono** for the invoice number (a code). Older type styles saved in a profile
  are kept in the file but no longer change the page.
- Small labels are capitals with letter spacing (`LABEL_SPACING`); everything else is sentence case.
- Ink is `INK`, secondary text `INK_SOFT`, hairlines `RULE` (`looks.LIGHT`; the Dark Page swaps in `looks.DARK`).
  **The paper has its own accent**, picked per profile (Paper Color, `looks.COLORS`; a new profile starts in
  Turquoise), shown only on the amount due, the balance and (with Color Band) the header. An accent is darkened
  (or, on the Dark Page, lightened) until it reads on the paper. The app's accent never changes a page.
- The business name sits on one line when it fits, measured exactly as it's drawn and with `NAME_SLACK` to spare;
  only a name too long even at the smallest size wraps. The logo and the name block are centred on each other.
  Logos are scaled to print size first (`LOGO_DPI`), so PDFs stay small; on the Dark Page a logo gets a small white
  card, since most are made for white paper.
- Long invoices flow onto more pages: the table header repeats, totals and the payment/terms boxes stay together.
- The bundled fonts are fixed-weight files (a PDF embeds one weight at a time), so PDFs embed exactly what's on
  screen. Exports are written to a temp file beside the target and moved into place when complete.

---

## 10. Checklist before you commit a UI change

1. No raw numbers or colors outside `tokens.py`. This should print nothing:
   `grep -rnE '[^{_A-Z0-9][0-9]{2,}px|#[0-9A-Fa-f]{6}|rgba' cobro/ui | grep -v tokens.py`
   (1px hairline borders and the icons' SVG drawings are the allowed literals.)
2. New controls are `CONTROL_H` tall (or `SMALL_H` for small icon buttons) and line up with their neighbours.
3. Every icon-only button has a tooltip.
4. Labels are short and in Title Case; sentences (tooltips, placeholders, messages) are plain sentences.
5. Screenshots look right in dark, in light and with a light accent:
   `QT_QPA_PLATFORM=offscreen python tests/screenshot.py OUTDIR` (the light ones end in `-light`, the light-accent
   ones in `-yellow`).
