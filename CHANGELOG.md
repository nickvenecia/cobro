# Changelog

## 1.2.0
- **A new window.** The sidebar on the left takes you to All Invoices, Drafts, Unpaid and Paid. The middle is one table of your invoices. Click one and it opens on the right, ready to edit; Esc or ✕ puts it away
- **The invoice table**: sort by any column; divided by month (newest first) or by client, each with its total, and each folds with a click; filter by status, profile and year; search. Unpaid, Overdue, Paid and Total add up underneath
- **The invoice in its own window**: **Invoice…** shows the page exactly as it prints, with Save PDF…, Print…, Save as PNG…, Copy as Text, Email Client and Mark as Sent
- **Settings** (⌘,): Appearance (Match System, Light or Dark), Accent Color (Cobro's turquoise or seven others), your Profiles, Account, Keyboard Shortcuts, and Your Data (Show Folder, Back Up…)
- **Light and dark**: Cobro follows your computer's setting and switches with it while it's open, or you pick one in Settings. The invoice's own Dark Page (the moon) is separate, and PDFs, PNGs and prints always stay white
- **Undo and redo** (⌘Z, ⇧⌘Z) for invoices, clients and profiles
- **Pick many**: ⌘A, or Shift- and ⌘-click, then Delete. One alert names what goes
- **Export as CSV…**: the invoices showing, one row each, for your bookkeeping or taxes. **Back Up…** saves everything as one zip file
- **Profiles**: your name, logo, contact details and payment text live in your profile (what used to be "Business"). Pick one under From, with **Edit…** right next to it; keep as many as you invoice from
- **Saved clients**: **New Client…** under Bill To saves a client once; after that just pick them. **Edit…** changes a client; drafts follow the change, invoices you already sent keep what they said
- **Numbers per client** (optional): `JLF-NRTH-2026-001` or `NRTH-2026-001`, each client with its own count, picked under the profile's Number Style. A draft's number follows its client until you type your own
- **Everything folds away**: every group on the right (and in your profile) folds, remembers how you left it, and says what's inside while folded. Line items fold to one row each, one open at a time; Duplicate, Move Up, Move Down and Remove are in each item's ⋯ menu
- **The paper**: every invoice is set in Inter, with the invoice number in IBM Plex Mono. Invoices that used one of the older type styles now print in Inter too; their color, header, logo and paper size stay as you picked them. A new profile's paper starts in turquoise
- **Only what applies**: Discount, Deposit and Sales Tax show when an invoice has them (**+ Discount** adds one, × takes an empty one off), and a line item's details box appears once it has details (**+ Details**)
- A new invoice you leave without filling anything in isn't kept
- Scrolling over a date or a dropdown never changes it
- A name next to a logo no longer leaves an empty line above the tagline; the logo and name line up in the middle
- Everything you made in Cobro 1.1 opens as it was

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
