#!/usr/bin/env sh
set -e
DEST="$HOME/guardian"
BIN="$HOME/.local/bin"
command -v python3 >/dev/null || { echo "python3 not found. Install it first."; exit 1; }
SRC="$(cd "$(dirname "$0")" && pwd)"
if [ "$SRC" != "$DEST" ]; then mkdir -p "$DEST"; cp -R "$SRC"/. "$DEST"/; fi
chmod +x "$DEST/guardian"
mkdir -p "$BIN"
ln -sf "$DEST/guardian" "$BIN/guardian"
case ":$PATH:" in *":$BIN:"*) ;; *)
  echo "export PATH=\"$BIN:\$PATH\"" >> "$HOME/.bashrc"
  [ -f "$HOME/.zshrc" ] && echo "export PATH=\"$BIN:\$PATH\"" >> "$HOME/.zshrc"
  echo "Added $BIN to PATH — open a new terminal." ;;
esac
echo "Installed. Try:  guardian run $DEST/demo.grd"
