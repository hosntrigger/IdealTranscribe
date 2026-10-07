Ideal Transcribe 1.0.0 – Raspberry Pi FINAL TEST

Diese Version basiert direkt auf der aktuellen Windows-FINAL3-Tkinter-Anwendung.

Gleiche Oberfläche/Funktionen:
- IDEALVISUAL-UI
- Hell/Dunkel, Dunkel als Standard
- Modellverwaltung
- Modell-Download / Update / Deinstallation
- Audioaufbereitung
- TXT / SRT / VTT
- Warteschlange
- verschiebbarer Bereich Warteschlange / Live-Ausgabe
- Pause / Fortsetzen
- Abbrechen
- Schließen-Warnung
- About / Projekt unterstützen

Pi-spezifisch unter der Haube:
- CPU / ARM statt CUDA
- 1 / 2 / 4 CPU-Threads
- nice-Prioritäten
- Temperaturschutz 78 °C / 70 °C
- 5 Sekunden Pause zwischen Batch-Dateien
- vorhandenes ~/whisper.cpp wird weiterverwendet
- vorhandene Modelle werden per Symlink eingebunden

Alte GUI entfernen:
  chmod +x UNINSTALL_OLD_VERSION.sh
  ./UNINSTALL_OLD_VERSION.sh

Neue Version installieren:
  chmod +x install.sh
  ./install.sh

Start:
  ideal-transcribe
