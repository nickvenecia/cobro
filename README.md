<p align="center"><img src="cobro/assets/icon.png" width="128" alt="Cobro icon"></p>

<h1 align="center">cobro.</h1>
<p align="center"><b>Make an invoice. Send it. Get paid.</b><br>
Clean, good-looking invoices as PDFs, with your logo and your colors. Runs on Mac, Windows and Linux.</p>

<p align="center"><img src="docs/screenshot.png" width="860" alt="Cobro: places on the left, your invoices in the middle, the one you picked on the right"></p>

---

## Download

Click the one for your computer. These links always give you the newest version.

| Your computer | Download |
|---|---|
| Mac with Apple Silicon (M1 and newer) | **[Cobro for Mac (Apple Silicon)](https://github.com/nickvenecia/cobro/releases/latest/download/Cobro-mac-apple-silicon.dmg)** |
| Intel Mac | **[Cobro for Mac (Intel)](https://github.com/nickvenecia/cobro/releases/latest/download/Cobro-mac-intel.dmg)** |
| Windows | **[Cobro for Windows (installer)](https://github.com/nickvenecia/cobro/releases/latest/download/Cobro-windows-setup.exe)** · [portable .zip](https://github.com/nickvenecia/cobro/releases/latest/download/Cobro-windows-portable.zip) |
| Linux | **[Cobro for Linux (AppImage)](https://github.com/nickvenecia/cobro/releases/latest/download/Cobro-linux-x64.AppImage)** · [.tar.gz](https://github.com/nickvenecia/cobro/releases/latest/download/Cobro-linux-x64.tar.gz) |

Not sure which Mac you have? Apple menu → About This Mac: "Chip: Apple M…" means Apple Silicon. Every version is on the **[Releases page](https://github.com/nickvenecia/cobro/releases)**.

**Installing:**
- **Mac:** open the .dmg and drag Cobro into Applications. The app isn't signed with a paid Apple developer account yet, so the first time macOS says it can't check it: open **System Settings → Privacy & Security**, scroll down and click **Open Anyway**. Only once.
- **Windows:** run the installer (no admin needed). If SmartScreen pops up, click **More info → Run anyway**.
- **Linux:** make the AppImage runnable (right-click → Properties → Allow executing, or `chmod +x`) and double-click it.

Everything comes bundled, fonts included. There's no Python or terminal needed.

**Updates:** Cobro checks for a new version once a day. When there is one, an **Update to …** button appears in the sidebar: it shows what's new, downloads the right file for your computer, swaps it in and reopens Cobro. You can also click your profile at the bottom of the sidebar → **Check for Updates…**, or turn the daily check off in **Settings › General**.

## What it does

**Everything in one window.** On the left, where you are: All Invoices, Drafts, Unpaid and Paid. In the middle, all your invoices in one table, by month or by client, with what's unpaid, overdue and paid added up underneath. Click one and it opens on the right, ready to edit. It saves itself as you type.

**Fill it in once.** Add your profile the first time you open Cobro: name, logo, address, where checks go, how you like to be paid, your terms. Every new invoice starts with all of it, with the next number already filled in (`JLF-2026-001`, `JLF-2026-002`…). Save your clients once too (**Bill To → New Client…**), then just pick them: no more typing the same address every time.

**Numbers your way.** One count for all your invoices (`JLF-2026-001`), or a separate count for each client with their code in it (`JLF-NRTH-2026-001`, or just `NRTH-2026-001`). Pick it under your profile's **Numbers & Tax**.

**Everything on the invoice, in the order it reads:** who it's for, the invoice number and date, payment terms (due on receipt, Net 7 to Net 60), the project with its shoot or work dates and delivery date, line items with details, quantities and rates (a rate of 0 prints as *Included*), and, only when you add them, a discount, sales tax and a deposit already paid.

**Make it look like yours:**
- **Logo** (PNG, JPG or SVG), in three sizes, with or without your name next to it
- **Paper color**: Turquoise, Ink Blue, Amber, Oxblood, Sage, Plum or Graphite, on the amount due, the balance and the header
- **Header**: clean, or a full color band
- **Paper**: Letter or A4

Every invoice is set in Inter, with the invoice number in IBM Plex Mono, so it looks the same on every computer.

**Send it out:** **Invoice…** opens the page exactly as it prints, with **Save PDF…** (fonts embedded, text selectable, small files), **Print…**, **Save as PNG…**, **Copy as Text** and **Email Client**. The moon turns on a **Dark Page** that's easier on the eyes; PDFs and prints always come out on white paper.

**Keep track:** each invoice is a Draft, Sent or Paid (with the date it was paid). Sent invoices past their due date show as **Overdue**, in red. Filter by status, profile or year, search, and pick many at once. **Export as CSV…** gives you a spreadsheet of what's showing, for your bookkeeping or your taxes. Right-click an invoice to **duplicate** it for the next job. **⌘Z** undoes the last change.

**More than one profile?** Add as many as you like (your own name, your production company…) in **Settings › Profiles** and pick one under **From**. Each has its own details, logo, numbering and paper.

**AI, if you want it.** Bring your own key (Anthropic, OpenAI, Google Gemini, Kimi, OpenRouter, DeepSeek, Mistral, xAI, Groq, or a model on your own computer) in **Settings › AI**. The assistant (⌘J) tidies up an invoice's line items or answers questions about them. Only the line items' words are sent, never amounts or clients, and nothing changes until you approve it. Your key stays in your computer's keychain.

**Light or dark**, as your computer is set, or pick one in **Settings › General**, with the accent color of your choice.

**Your data stays yours.** Invoices are saved as small files on your computer only. Nothing is uploaded. **Back Up…** saves everything as one zip file. Long invoices flow onto more pages on their own.

## Run from source

```bash
git clone https://github.com/nickvenecia/cobro.git && cd cobro
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m cobro                    # the app
python -m cobro cli sample out.pdf --header band   # a sample invoice, no window
python -m pytest -q                # tests
```

Build the app yourself: `pyinstaller cobro.spec --noconfirm` → `dist/`.

## Making a release

Merging is releasing. Builds and tests run on GitHub for every push and pull request. A pull request that
bumps `__version__` in `cobro/__init__.py` (with its notes at the top of `CHANGELOG.md` under that number)
publishes a new Release when it's merged: GitHub Actions builds the Mac (Apple Silicon and Intel), Windows and
Linux versions, tests each one, tags the commit and attaches the downloads. No tagging by hand.

### Optional: signing the Mac app
To get rid of the "can't check this app" warning you need an Apple Developer account ($99/yr). Add these repository secrets and the workflow will sign and notarize automatically: `MACOS_CERTIFICATE` (base64 .p12), `MACOS_CERTIFICATE_PWD`, `MACOS_SIGN_IDENTITY`, `APPLE_ID`, `APPLE_TEAM_ID`, `APPLE_APP_PASSWORD`.

## Changing the icon
Run `python scripts/make_icon.py`, or replace `cobro/assets/icon.png` with a 1024×1024 PNG (transparent corners). The Mac and Windows icons are generated from it at build time.

## Security
Found a security problem? Please report it privately, as [SECURITY.md](SECURITY.md) explains.

## License
Copyright © Nick Venecia.

Cobro's code is open source under GPL-3.0: you're welcome to read it, learn from it, change it and share it,
as long as what you share stays open source under the same license. The fonts it ships are under the
SIL Open Font License; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

### Name and icon
The name **Cobro**, the "cobro." wordmark and the app icon are **not** covered by the GPL. They belong to
Nick Venecia and identify the official app. If you publish a modified version, please give it a different
name and icon so people don't mistake it for Cobro. Saying that it's "based on Cobro" is welcome.
