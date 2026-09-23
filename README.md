# ⚡ HandBrake Auto AV1-10bit Converter (Windows)

[![GitHub Release](https://img.shields.io/github/v/release/itsbonfiretime/handbrake-auto-av1?style=flat-square&color=58a6ff)](https://github.com/itsbonfiretime/handbrake-auto-av1/releases/latest)
[![Platform Windows](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078d4?style=flat-square&logo=windows)](https://github.com/itsbonfiretime/handbrake-auto-av1/releases/latest)
[![Code Python](https://img.shields.io/badge/python-3.10%20%7C%203.13-3776ab?style=flat-square&logo=python)](https://www.python.org/)
[![License MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

Ein modernes, elegantes Windows-Tool zur automatischen Konvertierung von Videos in das zukunftssichere **AV1 10-Bit** Format mittels `HandBrakeCLI`.

Entwickelt für maximale Einfachheit: **Video oder ganzen Ordner per Drag & Drop hineinziehen – fertig!**

---

## 📥 Download

Lade die neueste, eigenständige `.exe` direkt aus den [GitHub Releases](https://github.com/itsbonfiretime/handbrake-auto-av1/releases/latest) herunter:

👉 **[HandBrakeAutoAV1.exe herunterladen (Neueste Version)](https://github.com/itsbonfiretime/handbrake-auto-av1/releases/latest/download/HandBrakeAutoAV1.exe)**

*Keine Vorinstallation von Python oder HandBrake nötig – alles ist in einer einzigen portablen Datei gebündelt!*

---

## 🌟 Highlights & Features

- **🔄 Integriertes Auto-Update**:
  - Prüft beim Start oder per Knopfdruck automatisch auf neue GitHub-Releases.
  - Zeigt Release-Notes und Changelog direkt in der App an.
  - Lädt Updates herunter und ersetzt die laufende `.exe` nahtlos per Selbst-Update.
- **🎯 Drag & Drop / One-Drop Workflow**:
  - Einzelne Videodateien (`.mp4`, `.mkv`, `.mov`, `.avi`, `.webm`, `.flv`, `.ts`, etc.) oder ganze Ordner einfach hineinziehen.
  - Bei aktivem One-Drop-Modus startet die Konvertierung automatisch.
- **📁 Ordner- & Stapelverarbeitung (Batch Mode)**:
  - Konvertiert ganze Ordner nacheinander mit Echtzeit-Fortschrittsanzeige.
  - **Intelligenter Skip**: Erkennt automatisch Videos, die bereits als AV1-10bit vorliegen, und überspringt diese.
- **📐 100% Exakte Quellparameter-Übernahme**:
  - **Auflösung**: Kein Pixelverlust (`--crop 0:0:0:0 --auto-anamorphic`), originale Auflösung und Seitenverhältnis bleiben unverändert.
  - **Bildrate**: Behält exakt die Quell-Framerate bei (`--rate <fps> --pfr`).
  - **Audio**: Verlustfreies Passthrough aller Tonspuren (`--all-audio --aencoder copy`), inkl. Dolby Atmos/TrueHD, DTS-HD, AC3, EAC3, AAC, FLAC, Opus.
  - **Untertitel & Kapitel**: Alle Untertitelspuren und Kapitelmarker werden originalgetreu übernommen.
- **🚀 SVT-AV1 10-Bit Kodierung**:
  - Moderner SVT-AV1 10-Bit Encoder (`svt_av1_10bit`).
  - Einstellbare Qualität (RF-Slider, Standard: `RF 26`) und Geschwindigkeit (Preset 4–8, Standard: `Preset 6`).
- **💎 Modernes Dark Theme & Auto-Resize**:
  - Responsive Benutzeroberfläche, die sich beim Auf- und Zuklappen von Inhalten automatisch in der Größe anpasst.
- **📁 Flexibler Ausgabeordner**:
  - Standardmäßig im selben Ordner wie die Quelldatei oder in einem frei wählbaren Zielverzeichnis.
  - Nach Fertigstellung öffnet ein Klick direkt den Ordner im Windows-Explorer.

---

## 🛠️ Für Entwickler: Aus Quellcode ausführen & Bauen

### 1. Voraussetzungen
- Windows 10 oder 11 (64-Bit)
- Python 3.10+ (getestet mit Python 3.13)

### 2. Repository klonen & Abhängigkeiten installieren
```powershell
git clone https://github.com/itsbonfiretime/handbrake-auto-av1.git
cd handbrake-auto-av1
pip install -r requirements.txt
pip install pyinstaller pillow
```

### 3. Anwendung starten
```powershell
python app.py
```

### 4. Standalone EXE lokal bauen
```powershell
python build_exe.py
```
*Hinweis: Fehlt `HandBrakeCLI.exe` im `bin/`-Ordner, lädt das Build-Skript die offizielle Version automatisch herunter.*

---

## 🤖 GitHub Actions CI/CD (Automatische Releases)

Das Repository verfügt über einen vorkonfigurierten GitHub Actions Workflow (`.github/workflows/build-release.yml`):
- Sobald ein Git-Tag gepusht wird (z. B. `git tag v1.0.1 && git push --tags`), baut GitHub Actions die Windows `.exe` vollautomatisch auf einem Windows-Runner und veröffentlicht ein neues GitHub Release mit angehängter `HandBrakeAutoAV1.exe`.
- Die Anwendung erkennt dieses Release bei allen Benutzern automatisch über die integrierte Update-Funktion!

---

## ⚙️ Einstellungen & Speicherort
Einstellungen (Qualitätsstufe, Presets, Ausgabeordner, Update-Prüfung) werden dauerhaft unter `%APPDATA%\HandBrakeAutoAV1\config.json` gespeichert.
