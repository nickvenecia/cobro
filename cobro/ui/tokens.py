"""Design tokens (the same system as Listo): the ONLY place sizes, spacing, type and colors are defined.

Every widget, layout and stylesheet rule uses these names. If something needs a value
that isn't here, add a token (and document it in DESIGN.md) instead of typing a number.
"""

from __future__ import annotations

# ---------------------------------------------------------------- spacing (4-pt grid)
SPACE_1 = 4  # tight: a label and its control, an icon and its text
SPACE_2 = 8  # related items: buttons in a row, cards in the list, options in a stack
SPACE_3 = 12  # between groups (sections) inside a panel
SPACE_4 = 16  # padding of panels, bars and the main areas
SPACE_5 = 24  # padding of dialogs and the empty-state drop zone

# ---------------------------------------------------------------- control sizes
CONTROL_H = 34  # EVERY button, dropdown, text field and segmented control
SMALL_H = 24  # chips, token buttons, icon-only buttons
INDICATOR = 16  # standard icon size
TOGGLE_ROW_H = 32  # an on/off setting: label left, switch right
TOGGLE_W, TOGGLE_H = 36, 20  # the switch
TOGGLE_INSET = 3  # gap between the switch's track and its knob
ICON = 16
ICON_SM = 14
ICON_LG = 24  # placeholder icons in empty thumbnails
ICON_XL = 44  # the drop-zone arrow
BAR_H = 6  # progress bars
TRACK_H = 4  # slider groove
HANDLE = 14  # slider handle
SCROLL_W = 10  # scrollbar width
SCROLL_GUTTER = SCROLL_W  # space always kept for it (see widgets.FitScroll)
SCROLL_MIN = 30  # shortest scrollbar handle

# ---------------------------------------------------------------- corner radius
RADIUS_XS = 4  # checkbox box
RADIUS_SM = 6  # chips, menu/list rows, small buttons
RADIUS = 8  # controls: buttons, fields, dropdowns, segmented controls
RADIUS_LG = 12  # cards, popups, panels inside dialogs
RADIUS_XL = 16  # the drop zone

# ---------------------------------------------------------------- type scale (px)
TEXT_XS = 11  # chips
TEXT_SM = 12  # secondary text: file details, hints, tooltips
TEXT_MD = 13  # body text and every control (the default)
TEXT_LG = 14  # emphasized text: file names in the list, footer title
TEXT_XL = 18  # dialog titles, empty-state headline
TEXT_BRAND = 21  # the "cobro." wordmark only
TEXT_TITLEBAR = 15  # the wordmark in the Mac title bar

WEIGHT_REGULAR = 400
WEIGHT_MEDIUM = 500  # controls
WEIGHT_SEMIBOLD = 600  # titles, labels, primary button
WEIGHT_BOLD = 700  # wordmark, dialog titles

# ---------------------------------------------------------------- layout
LIST_W = 300  # step 1 panel (Invoices)
DETAILS_W = 380  # step 2 panel (Details)
HEADER_H = 52  # the numbered step header on top of every panel
TITLEBAR_H = 32  # Cobro's own Mac title bar (fitted to the real one once the window shows)
STEP_BADGE = 22  # the round step number
SEG_INSET = 2  # gap between a segmented control's frame and its buttons
CARD_H = 64  # an invoice in the list
TEXT_BOX_H = 2 * CONTROL_H - SPACE_2  # a two-line text box (addresses, details)
TEXT_BOX_TALL = 4 * CONTROL_H - SPACE_3  # payment and terms text
NUM_FIELD_W = 96  # qty / rate fields
SWATCH = 12  # the color dot in the Color dropdown
LOGO_THUMB = 40  # the logo preview in the profile dialog
PAGE_GAP = 24  # space between preview pages
PAGE_SHADOW = 18  # blur of the paper's shadow in the preview
DIALOG_W = 480
PROFILE_DIALOG_H = 640  # the profile dialog: name, logo and contact show without scrolling
WINDOW_SIZE = (1440, 880)
WINDOW_MIN = (1180, 640)

# ---------------------------------------------------------------- colors (dark theme, shared with Listo)
BG = "#111113"  # window background
PANEL = "#17171A"  # sidebar, footer, dialogs
CARD = "#1E1E22"  # cards, fields
CARD_HOVER = "#24242A"
CARD_SELECTED = "#16282A"  # a selected invoice card (cool, so it reads as turquoise)
RAISED = "#2A2A30"  # buttons, popups
RAISED_HOVER = "#33333A"
RAISED_PRESS = "#26262C"
BORDER = "#2C2C33"
BORDER_STRONG = "#3A3A42"
BORDER_HOVER = "#4A4A54"
BORDER_CHECK = "#55555F"  # unchecked checkbox outline
TEXT = "#F4F1EC"
MUTED = "#A09B93"  # secondary text
FAINT = "#6E6A64"  # hints, disabled, section labels
WELL = "#0C0C0E"  # sunken areas: thumbnails, previews, logs
ACCENT = "#3CC8B4"  # Southwest turquoise — selection, primary action, focus (Listo's is marigold)
ACCENT_HOVER = "#5DD6C4"
ACCENT_PRESS = "#2AA996"
ON_ACCENT = "#04211D"  # text/icons on turquoise
ACCENT_OFF = "#1F3532"  # disabled primary button
ACCENT_OFF_TEXT = "#5B807A"
ACCENT_TINT = "rgba(60, 200, 180, 0.08)"  # turquoise wash
ACCENT_EDGE = "rgba(60, 200, 180, 0.55)"
GOOD = "#4CC38A"
BAD = "#F0616D"
BAD_TINT = "#2A1A1D"  # danger button hover
BAD_EDGE = "#5A2A30"  # failed card border
WARN = "#E9B949"
PAPER = "#FFFFFF"  # the invoice paper (and logo thumbnails) in the preview
SHADOW = "rgba(0, 0, 0, 0.55)"  # the paper's shadow on the dark preview
