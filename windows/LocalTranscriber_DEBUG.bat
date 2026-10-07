@echo off
cd /d "%~dp0"
python local_transcriber.py
echo.
echo ============================================
echo Local Transcriber wurde beendet.
echo Falls oben ein Fehler steht, bitte kopieren.
echo ============================================
pause
