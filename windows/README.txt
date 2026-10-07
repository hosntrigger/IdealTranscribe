IDEAL TRANSCRIBE – UNIVERSAL WINDOWS V2.3

Ziel:
Eine Windows-Version für Laptop UND leistungsstarke Workstation.

Neu gegenüber V1:
- automatische Hardware-Erkennung
- erkennt NVIDIA über nvidia-smi
- bevorzugt auf NVIDIA-Rechnern automatisch einen CUDA-Build von whisper.cpp
- auf anderen Rechnern CPU-Build
- "Alles automatisch einrichten"
  * lädt aktuelle whisper.cpp Windows-Binaries direkt von GitHub Releases
  * installiert FFmpeg über winget (Gyan.FFmpeg)
- Modellverwaltung direkt in der GUI
- Base / Small / Medium / Large V3 Turbo per Klick herunterladbar
- Modelle liegen zentral unter:
  %LOCALAPPDATA%\IdealTranscribe\models
- Komponenten liegen unter:
  %LOCALAPPDATA%\IdealTranscribe\bin
- gleiche Grundbedienung wie OfficePi-Version
- Batch / TXT / SRT / VTT
- gleicher Ordner / transkripte / benutzerdefiniert
- OGG/Opus/AMR/3GP automatische WAV-Vorkonvertierung
- Leistungsprofile
- Fortschrittsanzeige

START:
1. ZIP entpacken
2. setup_windows.bat einmal ausführen
3. IdealTranscribe.bat starten
4. Beim ersten Start "Alles automatisch einrichten" wählen
5. Gewünschtes Modell über "Modell verwalten..." installieren

Hinweis:
Der aktuelle whisper.cpp Release wird zur Laufzeit über die GitHub Releases API ermittelt.
Modelle werden aus dem offiziellen ggerganov/whisper.cpp Hugging-Face-Repository geladen.


V2.1 FIX:
- Python-3.14-kompatible Fehlerdialoge bei asynchronen Setup-/Downloadfehlern.

V2.2 FIX:
- whisper.cpp Release-Suche korrigiert.
- berücksichtigt, dass aktuelle Versions-Tags ohne Binärdateien existieren können.
- sucht automatisch den neuesten Release mit:
  CPU: whisper-bin-x64.zip
  NVIDIA: whisper-cublas-*-bin-x64.zip
- echtes Drag & Drop über tkinterdnd2/TkinterDnD.
- FFmpeg-Erkennung auch in WinGet-Paketordnern.

V2.3:
- Modellverwaltung erweitert.
- installierte Modelle zeigen Dateigröße.
- "Update prüfen" pro Modell.
- "Alle installierten Modelle auf Updates prüfen".
- "Aktualisieren" lädt ein Modell sicher neu und ersetzt es erst nach vollständigem Download.
- "Deinstallieren" mit Sicherheitsabfrage.
- Modell-Metadaten (ETag/Last-Modified/Größe) werden gespeichert.
- ältere Modellinstallationen ohne Metadaten werden anhand der Dateigröße geprüft.

V2.3.1 HOTFIX:
- Syntaxfehler aus v2.3 behoben.
- Python-Datei vor Veröffentlichung mit py_compile geprüft.
- zusätzliche IdealTranscribe_DEBUG.bat beigelegt; deren Fenster bleibt bei Laufzeitfehlern offen.

V2.4.1:
- Wiederholungsversuche bei GitHub/API-Downloads.
- erhöhte Timeouts.
- Fallback auf Windows curl.exe bei urllib/WinError 10054.
- bereits installierte Komponenten bleiben bei erneutem Setup erhalten.

V2.5:
- Erweiterter Modellkatalog:
  Base, Small, Medium Q5_0, Medium,
  Large V3 Turbo Q5_0, Large V3 Turbo Q8_0,
  Large V3 Turbo, Large V3 Q5_0, Large V3.
- Hardwareabhängige Empfehlungen in Hauptfenster und Modellverwaltung.
- RTX 3090 / große NVIDIA-GPUs:
  Large V3 Turbo = empfohlen,
  Large V3 = maximale Qualität,
  Large V3 Q5_0 = effizient.
- Button "Empfohlene Modelle installieren".
- Button "Alle Modelle installieren".
- Vor Stapelinstallation: deutliche Warnung mit Anzahl, geschätztem Speicherbedarf,
  freiem Plattenplatz und Modellliste.
- Modelle werden nacheinander geladen; bereits fertig installierte Modelle bleiben
  bei einem späteren Fehler erhalten.

V2.6:
- Transkribieren-/Abbrechen-Leiste dauerhaft am unteren Fensterrand.
- Buttons bleiben auch bei hoher DPI-Skalierung und kleineren Fenstern sichtbar.
- Hardwareempfehlung direkt im Hauptfenster.
- Bei der ersten v2.6-Nutzung wird das primär empfohlene Modell automatisch vorausgewählt.
- Danach bleibt eine bewusste Benutzerauswahl erhalten.
- Button "Empfohlen verwenden" setzt jederzeit das Hardware-Standardmodell.
- Untere Leiste zeigt permanent das empfohlene Modell.

V2.6.1 HOTFIX:
- Auto-Audioaufbereitung nutzt jetzt FLAC statt M4A/AAC.
- FLAC: 16 kHz, Mono, verlustfrei komprimiert; zuverlässig mit whisper.cpp/miniaudio.
- Alte gespeicherte Einstellung "Automatisch (M4A/AAC)" wird automatisch auf FLAC migriert.
- Auf NVIDIA-Systemen wird der CUDA-Build von whisper.cpp ausdrücklich vor dem CPU-Build bevorzugt.
- Komponentenstatus zeigt jetzt "Whisper: installiert (CUDA)" bzw. "(CPU)".
- Wenn eine NVIDIA-GPU erkannt wird, aber nur der CPU-Build vorhanden ist, bietet die Ersteinrichtung den CUDA-Build nach.
