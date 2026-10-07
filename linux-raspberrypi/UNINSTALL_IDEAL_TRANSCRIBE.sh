#!/usr/bin/env bash
set -euo pipefail

echo "Deinstalliere Ideal Transcribe und entferne alte Programmreste ..."

rm -rf "$HOME/.local/share/ideal-transcribe"
rm -rf "$HOME/.local/share/IdealTranscribe"
rm -rf "$HOME/.local/share/local-transcriber"
rm -rf "$HOME/.local/share/LocalTranscriber"

rm -f "$HOME/.local/bin/ideal-transcribe"
rm -f "$HOME/.local/bin/local-transcriber"

rm -f "$HOME/.local/share/applications/ideal-transcribe.desktop"
rm -f "$HOME/.local/share/applications/local-transcriber.desktop"

update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo
echo "Fertig. Ideal Transcribe und alte GUI-Reste wurden entfernt."
echo "Unverändert bleiben:"
echo "  ~/whisper.cpp"
echo "  ~/whisper.cpp/models"
