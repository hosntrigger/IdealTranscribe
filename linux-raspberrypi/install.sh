#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$HOME/.local/share/ideal-transcribe"
DATA_DIR="$HOME/.local/share/IdealTranscribe"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
VENV_DIR="$APP_DIR/venv"

echo "===================================================="
echo " Ideal Transcribe 1.0.0 – Raspberry Pi FINAL"
echo "===================================================="
echo
echo "Bestehendes whisper.cpp und vorhandene Modelle bleiben erhalten."
echo

sudo apt update
sudo apt install -y \
  python3 python3-tk python3-venv python3-pip \
  ffmpeg git cmake build-essential

# Alte GUI ersetzen, Daten/Modelle behalten.
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/assets" "$DATA_DIR/models" "$BIN_DIR" "$DESKTOP_DIR"

cp ideal_transcribe.py "$APP_DIR/ideal_transcribe.py"
cp -r assets/* "$APP_DIR/assets/"

# Bestehende whisper.cpp-Modelle ohne Kopieren wiederverwenden.
LEGACY_MODELS="$HOME/whisper.cpp/models"
if [ -d "$LEGACY_MODELS" ]; then
  for model in "$LEGACY_MODELS"/ggml-*.bin; do
    [ -e "$model" ] || continue
    target="$DATA_DIR/models/$(basename "$model")"
    if [ ! -e "$target" ]; then
      ln -s "$model" "$target" 2>/dev/null || true
    fi
  done
fi

python3 -m venv --system-site-packages "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null

# Optionales Drag & Drop; bei ARM-Problemen bleibt Dateiauswahl voll nutzbar.
if ! "$VENV_DIR/bin/python" -m pip install tkinterdnd2; then
  echo
  echo "Hinweis: tkinterdnd2 konnte nicht installiert werden."
  echo "Drag & Drop ist dann deaktiviert; 'Dateien hinzufügen' funktioniert weiterhin."
fi

cat > "$APP_DIR/run.sh" <<EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python" "$APP_DIR/ideal_transcribe.py" "\$@"
EOF
chmod +x "$APP_DIR/run.sh"

rm -f "$BIN_DIR/ideal-transcribe"
ln -sf "$APP_DIR/run.sh" "$BIN_DIR/ideal-transcribe"

rm -f "$DESKTOP_DIR/ideal-transcribe.desktop"
cat > "$DESKTOP_DIR/ideal-transcribe.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Ideal Transcribe
Comment=Lokale Audio- und Video-Transkription
Exec=$APP_DIR/run.sh
Icon=$APP_DIR/assets/idealtranscribe_icon_256.png
Terminal=false
Categories=AudioVideo;Audio;Video;
StartupNotify=true
EOF
chmod +x "$DESKTOP_DIR/ideal-transcribe.desktop"

echo
echo "Installation abgeschlossen."
echo "Start im Terminal: ideal-transcribe"
echo "Oder im Anwendungsmenü: Ideal Transcribe"
echo
echo "Vorhandenes whisper.cpp unter ~/whisper.cpp wird automatisch erkannt."
