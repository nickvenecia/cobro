#!/bin/bash
# Cloud sessions only: install what Cobro's tests, lint and screenshots need, so every session can
# check a change before it's pushed. Safe to run again (skips what's already there).
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# Qt needs a few system libraries even without a screen (the same list as the Linux CI build).
if ! ldconfig -p | grep 'libEGL.so.1' >/dev/null; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    libegl1 libgl1 libxkbcommon0 libfontconfig1 libdbus-1-3 >/dev/null
fi

# The app's own packages plus the test runner and the pinned linter (PyInstaller isn't needed here).
python3 -m pip install -q --disable-pip-version-check --root-user-action=ignore -r requirements.txt pytest "ruff==0.16.8"

# No screen in the cloud: Qt draws off-screen (tests, tests/screenshot.py, python -m cobro --smoke-test).
echo 'export QT_QPA_PLATFORM=offscreen' >> "$CLAUDE_ENV_FILE"
