#!/usr/bin/env bash
# Installs Cobro for the current user and adds it to your app menu.
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.local/share/cobro"
rm -rf "$DEST"
mkdir -p "$DEST" "$HOME/.local/share/applications"
cp -R "$SRC"/. "$DEST"/
sed "s|COBRO_DIR|$DEST|g" "$SRC/cobro.desktop" > "$HOME/.local/share/applications/cobro.desktop"
chmod +x "$DEST/Cobro"
echo "Cobro installed. Find it in your app menu, or run: $DEST/Cobro"
