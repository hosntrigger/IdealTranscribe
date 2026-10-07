from pathlib import Path
import ast

src = Path(__file__).with_name("ideal_transcribe.py")
text = src.read_text(encoding="utf-8")
ast.parse(text)

checks = [
    "class DownloadDialog",
    'APP_VERSION = "1.0.0 RC3"',
    "def auto_setup(self):",
    "Automatisch (FLAC)",
    "https://paypal.me/gottschn",
]
for check in checks:
    if check not in text:
        raise SystemExit(f"FEHLT: {check}")

if "Automatisch (M4A/AAC)" in text:
    raise SystemExit("ALTE M4A-BESCHRIFTUNG NOCH VORHANDEN")

print("RC2 SELFTEST OK")
