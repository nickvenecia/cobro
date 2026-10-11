---
name: try
description: Put the current changes on a draft pull request (never merged) and hand the owner download links to a test build of Cobro, so they can use the change in the real app before deciding. Use when the owner types /try or asks to "try it", "test it in the app", or for a "test build".
---

# /try: use a change in the real app before it goes into main

The owner wants to see the change working in Cobro on their own computer first. Nothing here
merges and nothing is released: that only happens with /release.

1. **Check it.** The session start hook installed everything. Run
   `ruff format . && ruff check . && python -m pytest -q`, and for anything you can see,
   `python tests/screenshot.py <scratchpad>/shots` and look at the pictures. Fix problems before pushing.
2. **Commit and push** on this session's branch (CONTRIBUTING.md §7). Add a line under "Unreleased"
   in CHANGELOG.md for anything a user would notice (start a `## Unreleased` heading at the top if
   the last release used it up).
3. **Open a draft pull request** into main, or reuse the open one for this branch. If the owner names
   an earlier try (a PR number or link), check out that PR's branch and keep working there instead.
   Draft keeps the Merge button off until /release. Title and body in plain words: what changed
   and what to look at when trying it.
4. **Wait for the test build without polling.** Call `subscribe_pr_activity` for the PR, tell the
   owner the build takes about 5 minutes, and end the turn. When the CI result arrives:
   - Red: find out why from the job logs, fix, push, and wait again.
   - Green: find the "Build Cobro" run for the PR's latest commit (`actions_list`, workflow runs on the
     branch) and send the owner:
     - the run page, `https://github.com/nickvenecia/cobro/actions/runs/<run id>`. Scroll to
       **Artifacts** at the bottom; they need to be signed in to GitHub.
     - which file to pick: `Cobro-mac-apple-silicon` (M1 and newer; Apple menu → About This Mac
       says "Chip: Apple M…"), `Cobro-mac-intel`, `Cobro-windows` or `Cobro-linux`. It downloads
       as a .zip with the usual .dmg / .exe / .AppImage inside.
     - how to try it: **quit the Cobro they normally use first** (only one Cobro runs at a time), open
       the .dmg and double-click Cobro right there, without dragging it to Applications, so their
       installed copy stays as it is. The first time, macOS may say it can't check the app:
       System Settings → Privacy & Security → Open Anyway.
     - their invoices: the test build opens their real invoices. If the change touches what gets
       saved (core/model.py, core/store.py), tell them to copy their data folder first
       (⋯ → Open Data Folder) so they can put it back.
5. **More changes after trying:** push to the same branch. A new test build follows by itself;
   repeat step 4.
6. **Never merge, never mark the PR ready, never release here.** When the owner is happy they run /release.
