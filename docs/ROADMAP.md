# Ideal Transcribe Roadmap

This roadmap lists ideas for future versions. Items here are **planned or under consideration**, not promises and not part of the current 1.0.0 release unless stated otherwise.

## Local AI post-processing

The next major direction is optional AI-assisted processing **after** Whisper transcription, while keeping the original transcript unchanged.

Planned modes include:

- correct obvious transcription, spelling and punctuation errors
- preserve meaning while improving readability
- structure long transcripts into paragraphs and sections
- summarize long recordings
- extract tasks, decisions and open questions
- meeting and interview presets
- custom post-processing instructions

The preferred architecture is local-first. A future version may connect to a local model provider such as Ollama, including a more powerful computer on the same local network.

## Principles

- the raw Whisper transcript is always preserved
- AI processing is optional
- local/offline processing remains a priority
- new modules should not destabilize the transcription core
- Windows and Raspberry Pi workflows should remain consistent where practical
