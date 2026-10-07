#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$HOME/.local/share/ideal-transcribe"
BIN_LINK="$HOME/.local/bin/ideal-transcribe"
LEGACY_BIN_LINK="$HOME/.local/bin/ideal-transcribe"
DESKTOP_FILE="$HOME/.local/share/applications/ideal-transcribe.desktop"
LEGACY_DESKTOP_FILE="$HOME/.local/share/applications/ideal-transcribe.desktop"

echo "Deinstalliere die aktuell installierte Local-Transcriber-GUI ..."
rm -rf "$APP_DIR"
rm -f "$BIN_LINK" "$LEGACY_BIN_LINK"
rm -f "$DESKTOP_FILE" "$LEGACY_DESKTOP_FILE"

echo
echo "Fertig."
echo "Nicht gelöscht wurden:"
echo "  ~/whisper.cpp"
echo "  ~/whisper.cpp/models"
echo "  ~/.local/share/IdealTranscribe"
