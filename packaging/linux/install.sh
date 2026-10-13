#!/usr/bin/env bash
# Installs Saldo for the current user and adds it to your app menu.
# The program goes in ~/.local/opt/saldo; your invoices live apart from it (~/.local/share/saldo), so
# installing again never touches them.
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.local/opt/saldo"
if [ -e "$DEST/businesses.json" ] || [ -e "$DEST/invoices" ]; then
  echo "$DEST holds invoices, so it wasn't replaced. Move them somewhere else first."
  exit 1
fi
rm -rf "$DEST"
mkdir -p "$DEST" "$HOME/.local/share/applications"
cp -R "$SRC"/. "$DEST"/
sed "s|SALDO_DIR|$DEST|g" "$SRC/saldo.desktop" > "$HOME/.local/share/applications/saldo.desktop"
rm -f "$HOME/.local/share/applications/cobro.desktop"  # the app's old name: Saldo takes its place in the menu
chmod +x "$DEST/Saldo"
echo "Saldo installed. Find it in your app menu, or run: $DEST/Saldo"
