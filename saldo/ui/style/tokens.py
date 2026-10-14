"""Design tokens: the ONLY place sizes, spacing, type, timing and colors are defined.

Every widget, layout and stylesheet rule uses these names. If something needs a value
that isn't here, add a token (and document it in DESIGN.md) instead of typing a number.
"""

from __future__ import annotations

# ---------------------------------------------------------------- spacing (4-pt grid)
SPACE_1 = 4  # tight: a label and its control, an icon and its text
SPACE_2 = 8  # related items: buttons in a row, cards in a list, options in a stack
SPACE_3 = 12  # between groups (sections) inside a panel
SPACE_4 = 16  # padding of panels, bars and the main areas
SPACE_5 = 24  # padding of dialogs and empty states

# ---------------------------------------------------------------- control sizes
CONTROL_H = 34  # EVERY button, dropdown, text field, segmented control and round icon button
SMALL_H = 24  # small round icon buttons inside rows and cards
SECTION_ADD = 20  # a sidebar section's plain + (a gray glyph, the Mac's size)
INDICATOR = 16  # a checkbox's box
TOGGLE_ROW_H = 32  # an on/off setting: label left, switch right
TOGGLE_W, TOGGLE_H = 36, 20  # the switch
TOGGLE_INSET = 3  # gap between the switch's track and its knob
ICON = 16  # icons in buttons and menus
ICON_SM = 14  # icons in small buttons
ICON_LG = 20  # a hero icon that must fill its circle (the assistant's bubble in the toolbar)
ICON_STROKE = 2.0  # the icon set's line width
BAR_H = 6  # progress bars
TRACK_H = 4  # slider groove
HANDLE = 14  # slider handle
SCROLL_W = 10  # scrollbar width
SCROLL_GUTTER = SCROLL_W  # space always kept for it (see widgets.FitScroll), so content never shifts
SCROLL_MIN = 30  # shortest scrollbar handle
SCROLL_INSET = 2  # a scrollbar's handle sits this far inside its track
SEG_INSET = 2  # gap between a segmented control's frame and its buttons
TEXT_BOX_H = 2 * CONTROL_H - SPACE_2  # a two-line text box (addresses, details)
TEXT_BOX_TALL = 4 * CONTROL_H - SPACE_3  # payment and terms text
NUM_FIELD_W = 96  # a rate
QTY_FIELD_W = 64  # a quantity
SWATCH = 22  # a color circle in Settings › Accent Color
SWATCH_RING = 2  # the ring around the chosen one (and the gap inside it)
COLOR_DOT = 12  # the color dot beside each choice in the Paper Color dropdown

# ---------------------------------------------------------------- corner radius
RADIUS_XS = 4  # checkbox box
RADIUS_SM = 6  # chips, small buttons
RADIUS = 8  # fields, dropdowns, segmented controls
RADIUS_LG = 12  # cards, alerts, line-item boxes
GLASS_R = 18  # a floating glass panel's corners

# ---------------------------------------------------------------- type scale (px)
TEXT_XS = 11  # chips, menu section headings
TEXT_SM = 12  # secondary text, section labels, tooltips
TEXT_MD = 13  # body text and every control (the default)
TEXT_LG = 14  # emphasis: names in lists, alert titles, totals
TEXT_XL = 18  # dialog titles, empty-state headline
TEXT_TITLE = 24  # the page's large title in the toolbar (All Invoices)
TEXT_BRAND = 21  # the "saldo." wordmark only
TEXT_TITLEBAR = 15  # the wordmark in the Mac title bar
TRACK_BRAND = -0.5  # letter spacing (px): the wordmark
TRACK_TITLEBAR = -0.3
TRACK_TITLE = -0.4  # page titles

WEIGHT_REGULAR = 400
WEIGHT_MEDIUM = 500  # controls
WEIGHT_SEMIBOLD = 600  # titles, labels, primary button
WEIGHT_BOLD = 700  # wordmark, page and dialog titles

# ---------------------------------------------------------------- layout
WINDOW_SIZE = (1600, 1000)  # the first size (until the window has filled the screen once)
WINDOW_MIN = (1280, 700)  # the toolbar, table and panel all still fit
GLASS_GAP = 10  # between the window's edge and its floating panels, and between panels
GLASS_SHADOW_STEPS = 16  # layers of a panel's shadow (soft, like the Mac's)
GLASS_SHADOW_SPREAD = 24  # how far it reaches: wide and faint, never a dark smudge
GLASS_SHADOW_DROP = 3  # how far below the panel it sits: barely
GLASS_EDGE_FADE = 60  # the hairline is brightest along the top, settling over this many px
SIDEBAR_W = 232  # the left panel: where you are
NAV_H = 30  # one row in the sidebar
NAV_GAP = 2  # between rows in the sidebar
NAV_INSET = SCROLL_GUTTER  # a sidebar row's gap from the glass edge (the scroll bar's room on the right)
NAV_R = GLASS_R - NAV_INSET  # its corners: concentric with the glass (the curves run parallel)
INSPECTOR_W = 420  # the right panel, where the picked invoice is edited
INSPECTOR_MIN = 360  # …on a smaller window
INSPECTOR_SHARE = 0.27  # of the window's width, between those two
TOOLBAR_H = 64  # the bar above the table: title, search, New; the right panel's header is as tall
HEADER_H = 52  # a panel header that isn't level with a toolbar (the page window)
TITLEBAR_H = 32  # Saldo's own Mac title bar (fitted to the real one once the window shows)
SEARCH_W = 440  # the search capsule asks for this much…
SEARCH_MIN = 160  # …and gives way down to this
TABLE_ROW_H = 34  # one invoice in the table
ROW_INSET = 2  # a table row's rounded highlight sits this far inside the row
ROW_R = 9  # its corners
SORT_ARROW = 10  # the sort arrow in a column title
CHEVRON = 9  # a divider's open/closed chevron
LINE_STROKE = 1.8  # drawn chevrons
NAME_MIN = 200  # the table's Client column never gets narrower; other columns step aside
# the invoice table's fixed column widths (Client takes the rest)
COL_W = {
    "number": 150,
    "project": 220,
    "issued": 116,
    "due": 116,
    "status": 96,
    "total": 120,
    "balance": 120,
    "contact": 180,  # the clients table: Attention…
    "email": 240,
    "count": 90,  # …how many invoices
}
GIVE_WAY = ("project", "due", "issued", "total")  # columns that step aside first on a narrow window
CLIENT_GIVE_WAY = ("email", "contact", "count")  # …and in the clients table
DIALOG_W = 480
DIALOG_W_WIDE = DIALOG_W + 2 * SPACE_5  # dialogs with a two-column form (client, profile)
DIALOG_W_XWIDE = DIALOG_W + 6 * SPACE_5  # the update window
ALERT_W = 300  # an alert (Delete …?), narrow like a Mac's
ALERT_ICON = 56  # the app icon at the top of it
SETTINGS_SIZE = (820, 620)  # the Settings window
SETTINGS_MIN = (680, 480)
SETTINGS_SIDE_W = 210  # its sidebar
PROFILE_DIALOG_H = 680  # the profile form: name, logo and contact show without scrolling
LOGO_THUMB = 40  # the logo preview in the profile form
LOGO_THUMB_MAX_W = 160
PAGE_DIALOG_SIZE = (1100, 1000)  # the invoice's own window
PAGE_DIALOG_INSET = 80  # it stays this far inside the main window
PAGE_DIALOG_MIN_H = 600
PAGE_GAP = 24  # space between pages in that window
PAGE_SHADOW = 18  # the paper's shadow there
NOTES_H = 320  # what's new, in the update window: as tall as its words, up to this (then it scrolls)
NOTES_LINE = 140  # what's new: the line height, in % of the font size
MENU_GAP = 6  # between a button and the menu it opens
CALENDAR_DAY = 40  # one day in the calendar a date opens, at least (a week is seven of these across)
# ---- every list of choices looks like the sidebar and Settings: menus, dropdown lists, pickers, suggestions.
# Rows sit LIST_INSET inside a list whose corners are LIST_R, so their corners (LIST_ROW_R) run parallel to it.
LIST_R = GLASS_R
LIST_INSET = NAV_INSET
LIST_ROW_R = NAV_R
LIST_ROW_H = NAV_H
LIST_GAP = NAV_GAP
AVATAR = 32  # your profile's initials, bottom of the sidebar
START_TILE_W = (
    184  # one way to start on an empty page (three fit beside the right panel on the smallest window)
)
START_BADGE = 40  # the circle behind a start tile's icon
GRIP_W = 20  # the six dots you drag a line item by
GRIP_GAP = 5  # between the grip's dots
GRIP_DOT = 1.2  # the radius of a dot in the grip
PROFILE_CARD_H = 48
ASSISTANT_ICON_BIG = 64  # and saying hi in an empty chat
REVIEW_COL_W = (
    170,
    64,
    240,
    0,
)  # the AI Review window's columns: Line, What, Now, Suggested (0: takes the room)
REVIEW_W = 900
TOAST_MAX_W = 520
TOAST_RISE = 10  # how far a toast rises as it comes in
TOAST_LIFT = SPACE_4  # its gap above the bottom of the page

# ---------------------------------------------------------------- timing (ms)
LIFT_STEP_MS = 16  # dragging a line item: how often the others move (about 60 a second)
LIFT_EASE = 0.3  # …and how far towards their new place each step (smaller is slower)
LIFT_SHADOW_STEPS = 6  # the lifted card's soft shadow
DOCK_MS = 240  # the right panel sliding in or out
FADE_MS = 150  # small things appearing or going (a sidebar section's +): a quick fade, never a pop
SAVE_DELAY_MS = 400  # save this long after the last keystroke
TABLE_DELAY_MS = 350  # refresh the table this long after an edit
DRAW_DELAY_MS = 90  # redraw an open invoice page this long after the last change
TOAST_MS = 3500  # how long a toast stays up
TOAST_MS_PER_CHAR = 60  # …or longer, for a long one: time to read it
TOAST_IN_MS = 220  # it rises and fades in…
TOAST_OUT_MS = 180  # …and fades away
UPDATE_CHECK_DELAY_MS = 1500  # the automatic update check, just after the window is up (every launch)
UPDATE_WAIT_MS = 1500  # a found update waits this long between looks while another window is open
QUIT_WAIT_MS = 1500  # how long quitting waits for a running web job, then goes anyway

# ---------------------------------------------------------------- colors: a dark and a light set
# Saldo follows the computer (or View › Appearance). Read colors as tokens.X when drawing, never copy them
# into a constant at import: use() swaps them.
DARK = {
    "BG": "#1E1E1E",  # window background: the Mac's dark charcoal, not black
    "PANEL": "#1E1E1E",  # dialogs, footers
    "CARD": "#1F1E20",  # cards, fields
    "CARD_HOVER": "#262527",
    "CARD_SELECTED": "#223232",  # a selected row (a hint of the accent)
    "RAISED": "#2B2A2C",  # buttons, popups, menus
    "RAISED_HOVER": "#343335",
    "RAISED_PRESS": "#272628",
    "BORDER": "#2D2C2E",  # hairlines, progress tracks
    "BORDER_STRONG": "#3B3A3D",
    "BORDER_HOVER": "#4D4B4F",
    "BORDER_CHECK": "#5C5A5F",  # unchecked checkbox outline
    "TEXT": "#F4F2F1",
    "MUTED": "#A8A5A6",  # secondary text
    "FAINT": "#737072",  # hints, disabled, section labels
    "WELL": "#0C0B0C",  # sunken areas: the page window behind the paper, release notes
    "ACCENT": "#3CC8B4",  # Southwest turquoise: selection, the one primary action, focus
    "ACCENT_HOVER": "#5DD6C4",
    "ACCENT_PRESS": "#2AA996",
    "ON_ACCENT": "#04211D",  # words and icons on the turquoise (white wouldn't read on it)
    "ACCENT_OFF": "#243D3B",  # a disabled primary button
    "ACCENT_OFF_TEXT": "#4E8E85",
    "ACCENT_TINT": "rgba(60, 200, 180, 0.15)",  # a turquoise wash
    "ACCENT_EDGE": "rgba(93, 214, 196, 0.55)",
    "CHIP": "rgba(60, 200, 180, 0.16)",  # a tinted capsule (+ Add Line Item)
    "CHIP_HOVER": "rgba(60, 200, 180, 0.26)",
    "DIVIDER": "#223834",  # a month or client band in the invoice table
    "DIVIDER_TEXT": "#94E1D6",  # its name and totals
    "DIVIDER_HOVER": "#24403C",  # a band under the mouse: a step brighter
    "GOOD": "#4CC362",  # Paid (shifted away from the turquoise so the two never blur)
    "WARN": "#E9B949",  # Sent, waiting to be paid
    "BAD": "#F0616D",  # Overdue, failed, delete
    "BAD_TINT": "#2A1A1D",  # danger button hover
    "BAD_EDGE": "#5A2A30",  # a failed outline
    "PAPER": "#FFFFFF",  # the paper (and logo thumbnails)
    "SHADOW": "rgba(0, 0, 0, 0.55)",  # the paper's shadow
    "ROW_HOVER": "rgba(255, 255, 255, 0.05)",  # a table row under the mouse
    "WINDOW_TOP": "#1E1E1E",  # the window's backdrop: one flat color behind the glass
    "WINDOW_BOTTOM": "#1E1E1E",
    "GLASS": "rgba(48, 47, 50, 0.92)",  # a floating panel (sidebar, right panel): one even tone
    "GLASS_STROKE": "rgba(255, 255, 255, 0.10)",  # its one hairline: faintly lighter than the panel
    "GLASS_EDGE": "rgba(255, 255, 255, 0.18)",  # …a little brighter along the top, where light catches it
    "GLASS_SHADOW": "rgba(0, 0, 0, 0.35)",  # soft and wide
    "TOAST": "#3A393C",  # a toast: a step lighter than the panels, so it stands out over anything
    "TOAST_TEXT": "#F4F2F1",
    "TOAST_EDGE": "rgba(255, 255, 255, 0.12)",
    "TOAST_SHADOW": "rgba(0, 0, 0, 0.60)",  # …lifted by a deeper shadow than the panels'
    "TOAST_DONE": "#4CC362",  # its icon: it worked (Paid's green)
    "TOAST_PROBLEM": "#E9B949",  # …it didn't (amber: red means overdue or delete)
    "TOAST_PROBLEM_FILL": "#4A3F25",  # a problem's toast is tinted amber, so it's never missed
    "TOAST_PROBLEM_EDGE": "rgba(233, 185, 73, 0.45)",
    "FIELD": "rgba(255, 255, 255, 0.07)",  # a text field or dropdown: lightly frosted
    "FIELD_BORDER": "rgba(255, 255, 255, 0.08)",
    "BLOCK": "rgba(255, 255, 255, 0.045)",  # a card inside a glass panel: a soft tint, no outline
    "FILL": "rgba(255, 255, 255, 0.045)",  # a soft fill on the page: a switch's track, a placeholder
}
LIGHT = {
    "BG": "#FFFFFF",
    "PANEL": "#FFFFFF",
    "CARD": "#FFFFFF",
    "CARD_HOVER": "#F2F2F4",
    "CARD_SELECTED": "#E7F3F1",
    "RAISED": "#FFFFFF",
    "RAISED_HOVER": "#F5F5F7",
    "RAISED_PRESS": "#E8E8EC",
    "BORDER": "#E5E5EA",
    "BORDER_STRONG": "#D8D8DD",
    "BORDER_HOVER": "#B8B8BF",
    "BORDER_CHECK": "#A2A2AA",
    "TEXT": "#1D1D1F",
    "MUTED": "#6E6E73",
    "FAINT": "#A1A1A6",
    "WELL": "#EDEDF0",
    "ACCENT": "#0F8574",  # a step deeper than on dark, so white words on it read
    "ACCENT_HOVER": "#279182",
    "ACCENT_PRESS": "#0D7163",
    "ON_ACCENT": "#FFFFFE",
    "ACCENT_OFF": "#CFE7E3",
    "ACCENT_OFF_TEXT": "#87C2BA",
    "ACCENT_TINT": "rgba(15, 133, 116, 0.09)",
    "ACCENT_EDGE": "rgba(15, 133, 116, 0.45)",
    "CHIP": "rgba(15, 133, 116, 0.10)",
    "CHIP_HOVER": "rgba(15, 133, 116, 0.18)",
    "DIVIDER": "#DBEDEA",
    "DIVIDER_TEXT": "#0D7163",
    "DIVIDER_HOVER": "#CAE4E0",
    "GOOD": "#1E9A35",
    "WARN": "#A97A06",
    "BAD": "#D3374A",
    "BAD_TINT": "#FBEAEC",
    "BAD_EDGE": "#EFB7BF",
    "PAPER": "#FFFFFF",
    "SHADOW": "rgba(0, 0, 0, 0.16)",
    "ROW_HOVER": "rgba(0, 0, 0, 0.04)",
    "WINDOW_TOP": "#FFFFFF",
    "WINDOW_BOTTOM": "#FFFFFF",
    "GLASS": "rgba(242, 242, 245, 0.94)",  # a soft gray glass on the white page
    "GLASS_STROKE": "rgba(0, 0, 0, 0.06)",  # a very faint gray hairline
    "GLASS_EDGE": "rgba(0, 0, 0, 0.04)",  # (fainter still along the top)
    "GLASS_SHADOW": "rgba(0, 0, 0, 0.08)",  # soft and wide
    "TOAST": "#2C2C2E",  # dark on the white page: easy to spot
    "TOAST_TEXT": "#FFFFFF",
    "TOAST_EDGE": "rgba(255, 255, 255, 0.10)",
    "TOAST_SHADOW": "rgba(0, 0, 0, 0.30)",
    "TOAST_DONE": "#4CC362",  # (the dark look's: these sit on the dark toast)
    "TOAST_PROBLEM": "#E9B949",
    "TOAST_PROBLEM_FILL": "#4A3F25",
    "TOAST_PROBLEM_EDGE": "rgba(233, 185, 73, 0.45)",
    "FIELD": "rgba(255, 255, 255, 1.0)",
    "FIELD_BORDER": "rgba(0, 0, 0, 0.10)",
    "BLOCK": "rgba(255, 255, 255, 0.85)",  # white cards on the gray glass
    "FILL": "rgba(0, 0, 0, 0.045)",  # light gray on white
}
# ---------------------------------------------------------------- the accent you pick (Settings › General)
# Saldo's own is turquoise, hand-set in DARK / LIGHT above (it isn't repeated in the list). The others are
# built from one color by accent_set(). Never red: red means overdue, failed or delete.
APP_ACCENT = "saldo"
ACCENTS = {  # key -> (name, on dark, on light)
    "saldo": ("Turquoise", "#3CC8B4", "#0F8574"),
    "blue": ("Blue", "#4A90F7", "#2F6FDB"),
    "purple": ("Purple", "#8069F7", "#6A52E8"),
    "pink": ("Pink", "#F25FA6", "#C9387F"),
    "orange": ("Orange", "#F5893A", "#C2600E"),
    "yellow": ("Yellow", "#EDBA3A", "#9C7104"),
    "green": ("Green", "#3DBE6E", "#1B8747"),
    "graphite": ("Graphite", "#9B999F", "#68666D"),
}
DARK_ON_ACCENT = "#141314"  # words on a light accent (yellow, green…), where white wouldn't read


def _rgb(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _hex(rgb) -> str:
    return "#" + "".join(f"{max(0, min(255, round(v))):02X}" for v in rgb)


def _mix(c: str, into: str, amount: float) -> str:
    """`amount` of color c mixed into `into`."""
    a, b = _rgb(c), _rgb(into)
    return _hex(x * amount + y * (1 - amount) for x, y in zip(a, b, strict=True))


def _rgba(c: str, alpha: float) -> str:
    r, g, b = _rgb(c)
    return f"rgba({r}, {g}, {b}, {alpha:g})"


def luminance(c: str) -> float:
    """Relative luminance (WCAG), 0 black … 1 white."""

    def ch(v: int) -> float:
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = _rgb(c)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def accent_set(base: str, scheme: str) -> dict[str, str]:
    """Every accent token for one color, in the dark or light look (the same steps as the hand-set turquoise)."""
    light = scheme == "light"
    on = "#FFFFFF" if contrast("#FFFFFF", base) >= 3 else DARK_ON_ACCENT
    if light:
        return {
            "ACCENT": base,
            "ACCENT_HOVER": _mix(base, "#FFFFFF", 0.9),
            "ACCENT_PRESS": _mix(base, "#000000", 0.85),
            "ON_ACCENT": "#FFFFFE" if on == "#FFFFFF" else on,
            "ACCENT_OFF": _mix(base, "#FFFFFF", 0.2),
            "ACCENT_OFF_TEXT": _mix(base, "#FFFFFF", 0.5),
            "ACCENT_TINT": _rgba(base, 0.09),
            "ACCENT_EDGE": _rgba(base, 0.45),
            "CARD_SELECTED": _mix(base, "#FFFFFF", 0.1),
            "DIVIDER": _mix(base, "#FFFFFF", 0.15),
            "DIVIDER_TEXT": _mix(base, "#000000", 0.85),
            "DIVIDER_HOVER": _mix(base, "#FFFFFF", 0.22),
            "CHIP": _rgba(base, 0.10),
            "CHIP_HOVER": _rgba(base, 0.18),
        }
    return {
        "ACCENT": base,
        "ACCENT_HOVER": _mix(base, "#FFFFFF", 0.85),
        "ACCENT_PRESS": _mix(base, "#000000", 0.88),
        "ON_ACCENT": on,
        "ACCENT_OFF": _mix(base, DARK["CARD"], 0.18),
        "ACCENT_OFF_TEXT": _mix(base, DARK["CARD"], 0.45),
        "ACCENT_TINT": _rgba(base, 0.15),
        "ACCENT_EDGE": _rgba(_mix(base, "#FFFFFF", 0.85), 0.55),
        "CARD_SELECTED": _mix(base, DARK["CARD"], 0.12),
        "DIVIDER": _mix(base, DARK["BG"], 0.15),
        "DIVIDER_TEXT": _mix(base, "#FFFFFF", 0.55),
        "DIVIDER_HOVER": _mix(base, DARK["BG"], 0.2),
        "CHIP": _rgba(base, 0.16),
        "CHIP_HOVER": _rgba(base, 0.26),
    }


SCHEME = "dark"
ACCENT_KEY = APP_ACCENT
globals().update(DARK)


def use(scheme: str, accent: str | None = None) -> None:
    """Switch every color token to the dark or light set, in the chosen accent (None keeps the current one;
    an unknown or empty one means Saldo's own)."""
    global SCHEME, ACCENT_KEY
    SCHEME = "light" if scheme == "light" else "dark"
    if accent is not None:
        ACCENT_KEY = accent if accent in ACCENTS else APP_ACCENT
    globals().update(LIGHT if SCHEME == "light" else DARK)
    if ACCENT_KEY != APP_ACCENT:
        _name, dark, light = ACCENTS[ACCENT_KEY]
        globals().update(accent_set(light if SCHEME == "light" else dark, SCHEME))


def accent_of(key: str, scheme: str | None = None) -> str:
    """A choice's color in the dark or light look (the current one by default)."""
    _name, dark, light = ACCENTS.get(key, ACCENTS[APP_ACCENT])
    return light if (scheme or SCHEME) == "light" else dark
