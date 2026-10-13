"""Releasing (scripts/release_notes.py and the build workflow): a version's notes, and the guards."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

import cobro

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release_notes", ROOT / "scripts" / "release_notes.py")
rn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rn)


def test_this_version_has_its_notes_at_the_top():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    notes = rn.notes(text, cobro.__version__)
    assert notes.strip() and "Cobro-mac-apple-silicon.dmg" in notes and "## Download" in notes


def test_only_that_versions_notes():
    text = "# Changelog\n\n## 1.3.0\n- New thing\n\n## 1.2.1\n- Old fix\n"
    assert rn.section(text, "1.3.0") == "- New thing"


@pytest.mark.parametrize(
    "text",
    [
        "# Changelog\n\n## Unreleased\n- x\n\n## 1.3.0\n- y\n",  # notes waiting under Unreleased
        "# Changelog\n\n## 1.2.0\n- y\n",  # the version was bumped but the notes weren't
        "# Changelog\n\n## 1.3.0\n\n## 1.2.0\n- y\n",  # an empty section
        "# Changelog\n",
    ],
)
def test_bad_changelogs_are_refused(text):
    with pytest.raises(rn.NotesError):
        rn.section(text, "1.3.0")


def test_the_workflow_releases_from_main_and_tags_only():
    wf = (ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")
    assert "push:refs/heads/main" in wf and "github.event_name != 'pull_request'" in wf
    assert "group: release" in wf and "cancel-in-progress: false" in wf
    assert "doesn't match __version__" in wf  # a tag that isn't the version is refused
    for line in wf.splitlines():  # every action pinned to an exact commit
        if "uses:" in line:
            ref = line.split("@", 1)[1].split()[0]
            assert len(ref) == 40, line
