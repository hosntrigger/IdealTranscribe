@echo off
setlocal
cd /d "%~dp0"

echo ====================================================
echo Ideal Transcribe 1.0.0 - Windows EXE Builder
echo ====================================================
echo.
echo Erstellt lokal eine EXE. Kein Upload, kein Release.
echo.

python -m pip install --upgrade pyinstaller tkinterdnd2
if errorlevel 1 goto :fail

python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name "IdealTranscribe" ^
  --icon "assets\localtranscriber_icon.ico" ^
  --add-data "assets;assets" ^
  --collect-all tkinterdnd2 ^
  local_transcriber.py
if errorlevel 1 goto :fail

echo.
echo Fertig:
echo %CD%\dist\IdealTranscribe.exe
echo.
pause
exit /b 0

:fail
echo.
echo BUILD FEHLGESCHLAGEN.
pause
exit /b 1
