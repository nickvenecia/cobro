# Security

## Reporting a problem

Please report security problems privately, not in a public issue: on GitHub, open this repository's
**Security** tab and choose **Report a vulnerability**. Say what you found and how to see it happen. You'll get
a reply, and a fix in a release, as soon as possible.

## What Saldo protects, and how

| What | How |
| --- | --- |
| AI keys, the account sign-in | In the system keychain only (`saldo/services/secrets.py`); never in a file or a log |
| Your invoices, clients and profiles | Saved only on your computer; atomic writes; unreadable files are set aside, never overwritten |
| Files and keys from Cobro (the app's old name) | Copied into Saldo's own folder and keychain entries the first time it opens; Cobro's are only read, never moved, changed or deleted |
| What's sent to an AI | Only the line items you ask it to help with (never clients, amounts owed or your profile), and only when you use AI |
| AI answers | Must fit a strict shape (`saldo/services/ai/tasks.py`): plain text, sane lengths, real numbers; you review every change before it's made, and one undo takes it back |
| API keys in transit | Sent only to the provider's own address over https (plain http only to this computer), never on a redirect |
| Logos | Read and drawn again by Saldo before they're kept (as a PNG, size-capped); anything else a file carried, including scripts or links inside an SVG, is left behind; files that aren't pictures are refused |
| Text on screen | Names and AI answers are always shown as plain text, never as formatting |
| CSV exports | Can't carry spreadsheet formulas |
| Updates | Only from this repository's releases; the SHA-256 must match; a signed Mac app must be replaced by one signed by the same developer |
| The build | GitHub Actions pinned to exact commits; the signing certificate only in the signing step (and the token for Cobro's old address only in the step that copies a release there); dependencies pinned, with Dependabot proposing updates |
