# Ideal Transcribe 1.2.0 UI Preview

This is a source preview, not a stable release. Existing models and settings are retained. The original logo assets are unchanged. No additional Python GUI dependency.

## Windows
Extract the repository archive. In windows, run setup_windows.bat if needed, then IdealTranscribe.bat. To create an EXE, use BUILD_WINDOWS_EXE.bat.

## Raspberry Pi
Extract the archive. In linux-raspberrypi run: python3 ideal_transcribe.py (requires python3-tk). This starts the preview without replacing the installed app. It shares existing application data. After testing, install.sh updates the app and copies both Python modules. Back up existing application configuration before testing.

## Acceptance checklist
- Select each of the four themes without restarting. Restart and verify persistence.
- Verify original logos, German/English UI, keyboard focus, disabled controls and button rounding.
- At 980x700 and larger, verify queue, log, progress bar and actions remain visible.
- Open model manager twice; verify only one instance, contrasting surface and readable model rows. Verify download dialog is in front and manager remains open after completion.
- Verify CPU/CUDA or ARM backend, file queue and a short transcription with TXT/SRT/VTT.
- System title bars and native message boxes follow the OS; no forced compositor-dependent background dimming.
