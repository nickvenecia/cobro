# Changelog

## 2.2.1
- **Fixed: saving your profile closed Saldo.** Save Changes (or Add Profile) in Settings › Profiles could close Saldo, on a Mac every time, however you got there: Edit Profile…, Edit… beside From, Add a Profile… or Add Your Profile… the first time. The fix in 2.2.0 missed the real cause; this one is tested in a Mac's own windows on every build
- **The invoice list stays where you scrolled it.** It used to jump back to the top a moment after every change you made
- **Scrolling the panel on the right no longer gets stuck on a text box.** Long terms, payment text or a line item's details used to catch the wheel and scroll inside their box, and the panel stopped. Click into a box to scroll what's in it
- **Another invoice or client opens at its top**, not partway down where you left the last one

## 2.2.0
- **Fixed a crash when adding your first profile.** Saving it from the Add Your Profile… tile could close Saldo. Right-clicking a client in the sidebar and choosing Delete Client… could too
- **Every date is picked in a calendar**, never typed: click a date (or press Space) and pick the day. Today is in your accent color and the day you picked sits on a rounded tile
- **Work dates are picked too**: Show Work Dates, then the first and last day. They print just as before ("Sep 26–27, 2026"). Dates you typed in an older version stay as they were until you pick new ones
- **Not every job is a delivery**: a new invoice starts without a delivery date. Show Delivery Date adds one when there was a delivery. A new profile's terms no longer say the work "has been delivered"
- **Save Client**: a new client has Save Client across the bottom, so you know they're kept. Once saved, New Invoice takes its place to bill them right away

## 2.1.1
- Words are never cut off: the tile that starts your profile (and every other start tile) puts its words on a second line when they don't fit on one

## 2.1.0
- **cobro. is now saldo.** Same app, new name. Everything you made carries over
- The first time Saldo opens, every invoice, client, profile, number and setting from Cobro is there, and so is your AI key. Cobro's own files are left as they were
- **A new icon**: "s." on the dark tile, the full stop in the same turquoise
- On a Mac, Saldo takes the old Cobro app's place instead of sitting beside it
- On Linux, the install script keeps the program apart from your invoices, so installing again never touches them

## 2.0.0
- **A new window.** The sidebar on the left takes you to All Invoices, with Drafts, Unpaid and Paid under it (the arrow folds them away), and to your clients. The middle is one table of your invoices. Click one and it opens on the right, ready to edit; Esc or ✕ puts it away
- **Clients in the sidebar**: All Clients shows everyone you bill in one table (who to address, their email, how many invoices, what's unpaid, what you've billed in all), and each client sits under it in the sidebar. Click one to see and change their details, every invoice you've made them, and **New Invoice** to bill them again. The section's **+** (or ⇧⌘N) adds a client; they're kept once they have a name
- **The invoice table**: sort by any column; divided by month (newest first) or by client, each with its total, and each folds with a click; filter by status, profile and year; search. Unpaid, Overdue, Paid and Total add up underneath
- **The invoice in its own window**: **Invoice…** shows the page exactly as it prints, with Save PDF…, Print…, Save as PNG…, Copy as Text, Email Client and Mark as Sent
- **Settings** (⌘,): Appearance (Match System, Light or Dark), Accent Color (Saldo's turquoise or seven others), your Profiles, Account, Keyboard Shortcuts, and Your Data (Show Folder, Back Up…)
- **Light and dark**: Saldo follows your computer's setting and switches with it while it's open, or you pick one in Settings. The invoice's own Dark Page (the moon) is separate, and PDFs, PNGs and prints always stay white
- **Undo and redo** (⌘Z, ⇧⌘Z) for invoices, clients and profiles
- **AI, with your own key** (optional): connect Anthropic, OpenAI, Google Gemini, Kimi, OpenRouter, DeepSeek, Mistral, xAI, Groq or a model on your own computer in Settings › AI. The assistant (⌘J, or the bubble in the toolbar) tidies up an invoice's line items or answers questions about them. Only the line items' words are sent, never amounts or clients, and nothing changes until you approve it
- **Pick many**: ⌘A, or Shift- and ⌘-click, then Delete. One alert names what goes
- **Search** finds invoices by number, client, project, status, line items, amount or date ("Oct 13")
- **Export as CSV…**: the invoices showing, one row each, for your bookkeeping or taxes. **Back Up…** saves everything as one zip file
- **Profiles**: your name, logo, contact details and payment text live in your profile (what used to be "Business"). Pick one under From, with **Edit…** right next to it; keep as many as you invoice from
- **Saved clients**: save a client once (in All Clients, or **New Client…** under Bill To), then just pick them under Bill To. Change a client in their panel or with **Edit…**; drafts follow the change, invoices you already sent keep what they said
- **Numbers per client** (optional): `JLF-NRTH-2026-001` or `NRTH-2026-001`, each client with its own count, picked under the profile's Number Style. A draft's number follows its client until you type your own
- **Everything folds away**: every group on the right (and in your profile) folds, remembers how you left it, and says what's inside while folded. Line items fold to one row each, one open at a time. **Drag a line item by its grip** to put it somewhere else (Esc puts it back); Duplicate, Move Up, Move Down and Remove are in each item's ⋯ menu
- **The paper**: every page says which page it is (Page 1 of 1), and every invoice is set in Inter, with the invoice number in IBM Plex Mono. Invoices that used one of the older type styles now print in Inter too; their color, header, logo and paper size stay as you picked them. A new profile's paper starts in turquoise
- **Only what applies**: Discount, Deposit and Sales Tax show when an invoice has them (**+ Discount** adds one, × takes an empty one off), and a line item's details box appears once it has details (**+ Details**)
- **Ways to start**: a page with nothing on it shows what you can do as tiles (Add Your Profile…, New Invoice, Clear Filters)
- **Updates read better**: the update window shows what's new in plain words, straight from these notes
- **Messages are easier to notice.** They float over your list, just above the totals, and rise in and fade away: a green check when something worked, an amber sign on an amber card when it didn't, and a dark card on the white page in the light look. Long ones stay up long enough to read, resting the pointer on one keeps it up, and they never get in the way of a click
- A new invoice you leave without filling anything in isn't kept
- Scrolling over a date or a dropdown never changes it
- A name next to a logo no longer leaves an empty line above the tagline; the logo and name line up in the middle
- **Safer logos**: every logo, SVG too, is redrawn by Saldo as a clean picture before it's kept (anything else the file carried is left behind), very big files are refused, and logos are scaled to print size on the page, so PDFs stay small
- **A new icon**: "c." on a dark tile, the full stop in turquoise
- Everything you made in version 1.1 opens as it was

## 1.1.0
- **First release.** Make an invoice, see it exactly as it will print, save it as a PDF
- **Fill it in once**: your business (name, addresses, where checks go, how to pay, terms) starts every new invoice; numbers count up on their own (JLF-2026-001); clients are remembered and offered as you type
- **Everything on the invoice**: bill to, project with shoot/work dates and delivery date, line items with details, discount, sales tax, deposit paid, payment terms from due on receipt to Net 60
- **Your look**: logo (PNG, JPG, SVG) in three sizes; type styles Modern, Clean, Classic, Editorial, Screenplay, Poster and Technical, or any two fonts including ones on your computer; seven colors or any color; clean or color-band header; Letter or A4. The preview changes as you pick
- **Send it out**: Save PDF… (fonts embedded), Print…, Save as PNG…, Copy as Text
- **Keep track**: Draft, Sent, Paid (with the date), Overdue on its own; unpaid and paid-this-year totals; filters; duplicate for the next job
- **More than one business**, each with its own details, numbering and look
- Long invoices flow onto more pages with page numbers
- Saves as you type; everything stays on your computer
- Updates itself from GitHub
