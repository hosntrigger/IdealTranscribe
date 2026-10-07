#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$HOME/.local/share/local-transcriber"
DATA_DIR="$HOME/.local/share/LocalTranscriber"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
VENV_DIR="$APP_DIR/venv"

echo "===================================================="
echo " Local Transcriber 1.0.0 – Raspberry Pi FINAL"
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

cp local_transcriber.py "$APP_DIR/local_transcriber.py"
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
exec "$VENV_DIR/bin/python" "$APP_DIR/local_transcriber.py" "\$@"
EOF
chmod +x "$APP_DIR/run.sh"

ln -sf "$APP_DIR/run.sh" "$BIN_DIR/local-transcriber"

cat > "$DESKTOP_DIR/local-transcriber.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Local Transcriber
Comment=Lokale Audio- und Video-Transkription
Exec=$APP_DIR/run.sh
Icon=$APP_DIR/assets/localtranscriber_icon_256.png
Terminal=false
Categories=AudioVideo;Utility;
StartupNotify=true
EOF
chmod +x "$DESKTOP_DIR/local-transcriber.desktop"

echo
echo "Installation abgeschlossen."
echo "Start im Terminal: local-transcriber"
echo "Oder im Anwendungsmenü: Local Transcriber"
echo
echo "Vorhandenes whisper.cpp unter ~/whisper.cpp wird automatisch erkannt."
