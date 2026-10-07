# Local Transcriber

**Local Transcriber by IDEALVISUAL** is a desktop GUI for local audio/video transcription with `whisper.cpp`. It is free for permitted noncommercial use; commercial use requires a separate license.

## Version

**1.0.0**

## Features

- local/offline transcription
- Windows and Raspberry Pi builds with the same UI and workflow
- drag & drop (when TkDND is available) and file picker
- batch queue
- resizable split between queue and live output
- pause / resume / cancel
- safe close confirmation during active jobs
- TXT / SRT / VTT output
- selectable Whisper models
- model install / update / uninstall
- automatic FLAC preparation for problematic formats
- WAV / MP3 / original-audio modes
- configurable output folder
- Light / Dark theme; Dark is the default on a fresh setup
- Windows: CPU/CUDA detection and NVIDIA CUDA preference
- Raspberry Pi: ARM/CPU profiles, temperature protection and batch cooldown
- voluntary project-support link

## Windows

Source and build helpers are under `windows/`.

Build locally with:

```text
windows/BUILD_WINDOWS_EXE.bat
```

The finished executable is created at `windows/dist/LocalTranscriber.exe`. A release should normally attach the tested EXE or a ZIP containing it to GitHub Releases instead of committing binaries to the source tree.

## Raspberry Pi

The Raspberry Pi package is under `linux-raspberrypi/` and uses the same Tkinter UI/codebase as Windows, adapted for ARM/CPU.

Install:

```bash
chmod +x install.sh
./install.sh
```

It preserves an existing `~/whisper.cpp` installation and can reuse existing models from `~/whisper.cpp/models`.

## Privacy

Transcription is performed locally. Audio and video files do not need to be uploaded to a cloud transcription service. Model/component downloads require internet access when requested.

## Project support

Local Transcriber is free for permitted noncommercial use. Voluntary support for further development:

https://paypal.me/gottschn

## License

Local Transcriber source code and official builds are provided under the **PolyForm Noncommercial License 1.0.0**. See `LICENSE`.

- permitted noncommercial use: free
- commercial/business use: separate commercial license required

See `COMMERCIAL_LICENSE.md` for the commercial-use policy.

Third-party software retains its own licenses. See `THIRD_PARTY_NOTICES.md`.
