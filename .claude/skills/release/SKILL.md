---
name: release
description: Publish a new version of Cobro. Put the version number and changelog on the pull request, merge it into main when the checks are green, then confirm the release and its six downloads are up. Use when the owner types /release (optionally with a version like 1.2.0, or patch / minor / major) or plainly asks to release, ship or merge-and-publish.
---

# /release: merge into main and publish

The owner running /release is their go-ahead to merge into main and publish a version (CLAUDE.md,
"How we work"). Never push to main directly; everything goes through the pull request.

1. **What's being released.** The open PR for this session's branch, or the PR the owner names
   (check out its branch). If there's no PR but CHANGELOG.md has entries under "Unreleased" on main
   (already merged, never released), make a PR from this session's branch, freshly started from
   main, that carries only the version change. If there's nothing new at all, say so and stop.
2. **Pick the version.** Use the owner's if they gave one. Otherwise read the "Unreleased"
   entries: anything new → next minor (1.1.0 → 1.2.0); only fixes → next patch (1.1.0 → 1.1.1).
   Never reuse a version that already has a tag (`git ls-remote --tags origin`). Say which you
   picked and why in one line.
3. **Put it on the PR.** Set `__version__` in `cobro/__init__.py` and rename `## Unreleased` to
   `## X.Y.Z` in CHANGELOG.md. Run `ruff format . && ruff check . && python -m pytest -q`. Commit
   ("Cobro X.Y.Z") and push. If the PR is a draft, mark it ready (`update_pull_request`).
4. **Wait for green checks without polling.** `subscribe_pr_activity`, end the turn, act on the CI
   event. Red: fix and push. Never merge with a red check.
5. **Merge** with `merge_pull_request` (merge method "merge"). If GitHub refuses (no permission),
   send the owner the PR link and ask them to press **Merge pull request**. That's their only step.
6. **The release publishes itself.** On main, the "Build Cobro" run sees that `cobro/__init__.py`
   names a version with no tag yet. It builds every platform, then creates the tag vX.Y.Z and the
   GitHub Release with the downloads (about 5 minutes after the merge). Check about 10 minutes
   later (`send_later`): `get_release_by_tag` vX.Y.Z must list the six files named in CLAUDE.md
   "Releasing". If the run failed, read its job logs and fix through a new PR.
7. **Tell the owner** in plain words: the version, its page
   `https://github.com/nickvenecia/cobro/releases/tag/vX.Y.Z`, and that Cobro offers
   "Update to X.Y.Z" on its daily check (or right away from ⋯ → Check for Updates…).
