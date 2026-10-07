@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo  Local Transcriber - Universal Windows V2
echo ============================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo Python wurde nicht gefunden.
  echo Bitte Python installieren und "Add Python to PATH" aktivieren.
  pause
  exit /b 1
)

python -m pip install -r requirements.txt

echo.
echo Fertig. Danach LocalTranscriber.bat starten.
echo whisper.cpp, FFmpeg und Modelle koennen direkt in der GUI eingerichtet werden.
pause
