@echo off
cd /d "%~dp0"
python local_transcriber.py
if errorlevel 1 (
  echo.
  echo Local Transcriber wurde mit einem Fehler beendet.
  pause
)
