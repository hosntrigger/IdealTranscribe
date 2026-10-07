#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$HOME/.local/share/local-transcriber"
BIN_LINK="$HOME/.local/bin/local-transcriber"
DESKTOP_FILE="$HOME/.local/share/applications/local-transcriber.desktop"

echo "Deinstalliere die aktuell installierte Local-Transcriber-GUI ..."
rm -rf "$APP_DIR"
rm -f "$BIN_LINK"
rm -f "$DESKTOP_FILE"

echo
echo "Fertig."
echo "Nicht gelöscht wurden:"
echo "  ~/whisper.cpp"
echo "  ~/whisper.cpp/models"
echo "  ~/.local/share/LocalTranscriber"
