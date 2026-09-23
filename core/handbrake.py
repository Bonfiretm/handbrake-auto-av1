import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import QThread, pyqtSignal


def get_windows_creation_flags() -> int:
    """Returns CREATE_NO_WINDOW on Windows to prevent console flashing."""
    if sys.platform == "win32":
        return subprocess.CREATE_NO_WINDOW
    return 0


def locate_handbrake_cli() -> Optional[Path]:
    """Finds the HandBrakeCLI executable across bundled and system paths."""
    candidates = []

    # 1. PyInstaller bundled path (_MEIPASS)
    if hasattr(sys, "_MEIPASS"):
        meipass = Path(sys._MEIPASS)
        candidates.append(meipass / "bin" / "HandBrakeCLI.exe")
        candidates.append(meipass / "HandBrakeCLI.exe")

    # 2. Next to executable
    exe_dir = Path(sys.executable).parent
    candidates.append(exe_dir / "bin" / "HandBrakeCLI.exe")
    candidates.append(exe_dir / "HandBrakeCLI.exe")

    # 3. Next to script / workspace
    base_dir = Path(__file__).resolve().parent.parent
    candidates.append(base_dir / "bin" / "HandBrakeCLI.exe")
    candidates.append(base_dir / "HandBrakeCLI.exe")

    # 4. Standard HandBrake install directory
    candidates.append(Path("C:/Program Files/HandBrake/HandBrakeCLI.exe"))
    candidates.append(Path("C:/Program Files (x86)/HandBrake/HandBrakeCLI.exe"))

    # Check candidates
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    # 5. System PATH
    found = shutil.which("HandBrakeCLI")
    if found:
        return Path(found)

    return None


@dataclass
class VideoMetadata:
    file_path: Path
    file_name: str
    file_size_formatted: str
    duration_str: str
    duration_seconds: float
    width: int
    height: int
    fps: float
    fps_str: str
    par_str: str
    dar_str: str
    video_codec: str
    bit_depth: int
    audio_tracks: List[str] = field(default_factory=list)
    subtitle_tracks: List[str] = field(default_factory=list)
    raw_title: dict = field(default_factory=dict)

    @property
    def resolution_str(self) -> str:
        res = f"{self.width}x{self.height}"
        if self.width >= 3840 or self.height >= 2160:
            res += " (4K UHD)"
        elif self.width >= 2560 or self.height >= 1440:
            res += " (1440p QHD)"
        elif self.width >= 1920 or self.height >= 1080:
            res += " (1080p Full HD)"
        elif self.width >= 1280 or self.height >= 720:
            res += " (720p HD)"
        return res


def format_bytes(size: int) -> str:
    """Format bytes into human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size) < 1024.0:
            return f"{size:3.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


class VideoScanWorker(QThread):
    """Scans video metadata asynchronously using HandBrakeCLI --scan --json."""
    scan_completed = pyqtSignal(object)  # VideoMetadata
    scan_failed = pyqtSignal(str)

    def __init__(self, file_path: Path, hb_cli: Path):
        super().__init__()
        self.file_path = Path(file_path)
        self.hb_cli = Path(hb_cli)

    def run(self):
        try:
            cmd = [
                str(self.hb_cli),
                "-i", str(self.file_path),
                "--scan",
                "--json",
                "-t", "0"
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=get_windows_creation_flags()
            )

            full_output = []
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    full_output.append(line)

            output_text = "".join(full_output)

            # Look for JSON Title Set in output
            json_marker = "JSON Title Set:"
            idx = output_text.find(json_marker)
            if idx == -1:
                # Try finding bare JSON with TitleList
                idx = output_text.find('{"MainFeature"')
                if idx == -1:
                    idx = output_text.find('"TitleList"')
                    if idx != -1:
                        # step back to nearest {
                        idx = output_text.rfind("{", 0, idx)

            if idx == -1:
                self.scan_failed.emit("HandBrake konnte keine Video-Metadaten analysieren.")
                return

            json_str = output_text[idx + len(json_marker):].strip()
            # Extract JSON object (bracket balancing)
            start_brace = json_str.find("{")
            if start_brace == -1:
                self.scan_failed.emit("Ungültiges Metadaten-Format erhalten.")
                return

            brace_count = 0
            json_end = -1
            for i, c in enumerate(json_str[start_brace:], start=start_brace):
                if c == "{":
                    brace_count += 1
                elif c == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break

            if json_end == -1:
                self.scan_failed.emit("Unvollständiges JSON-Paket von HandBrake empfangen.")
                return

            json_body = json_str[start_brace:json_end]
            data = json.loads(json_body)

            titles = data.get("TitleList", [])
            if not titles:
                self.scan_failed.emit("Keine lesbare Videospur im Video gefunden.")
                return

            # Main title
            title = titles[0]
            geom = title.get("Geometry", {})
            width = geom.get("Width", 1920)
            height = geom.get("Height", 1080)
            par = geom.get("PAR", {})
            par_num = par.get("Num", 1)
            par_den = par.get("Den", 1)

            framerate = title.get("FrameRate", {})
            fps_num = framerate.get("Num", 30)
            fps_den = framerate.get("Den", 1)
            fps = (fps_num / fps_den) if fps_den else 30.0

            color = title.get("Color", {})
            bit_depth = color.get("BitDepth", 8)
            video_codec = title.get("VideoCodec", "Unbekannt")

            # Duration
            duration_obj = title.get("Duration", {})
            hours = duration_obj.get("Hours", 0)
            mins = duration_obj.get("Minutes", 0)
            secs = duration_obj.get("Seconds", 0)
            duration_seconds = hours * 3600 + mins * 60 + secs
            duration_str = f"{hours:02d}:{mins:02d}:{secs:02d}"

            # Audio tracks
            audio_tracks = []
            for a in title.get("AudioList", []):
                lang = a.get("Language", "")
                desc = a.get("Description", "")
                codec = a.get("CodecName", "")
                ch = a.get("ChannelLayout", "")
                entry = f"{lang} ({codec.upper()}, {ch})" if (codec or ch) else desc
                audio_tracks.append(entry.strip())

            # Subtitles
            subtitle_tracks = []
            for s in title.get("SubtitleList", []):
                s_lang = s.get("Language", "Untertitel")
                s_name = s.get("Name", "")
                s_fmt = s.get("Format", "")
                entry = f"{s_lang} {s_name} [{s_fmt}]".strip()
                subtitle_tracks.append(entry)

            # File size
            try:
                size_bytes = self.file_path.stat().st_size
                size_str = format_bytes(size_bytes)
            except Exception:
                size_str = "Unbekannt"

            par_str = f"{par_num}:{par_den}"
            dar_val = (width * par_num) / (height * par_den) if (height * par_den) else (width / height)
            dar_str = f"{dar_val:.2f}:1"

            meta = VideoMetadata(
                file_path=self.file_path,
                file_name=self.file_path.name,
                file_size_formatted=size_str,
                duration_str=duration_str,
                duration_seconds=duration_seconds,
                width=width,
                height=height,
                fps=fps,
                fps_str=f"{fps:.3f}".rstrip("0").rstrip("."),
                par_str=par_str,
                dar_str=dar_str,
                video_codec=video_codec,
                bit_depth=bit_depth,
                audio_tracks=audio_tracks,
                subtitle_tracks=subtitle_tracks,
                raw_title=title,
            )

            self.scan_completed.emit(meta)

        except Exception as e:
            self.scan_failed.emit(f"Fehler bei der Analyse: {str(e)}")


class ConversionWorker(QThread):
    """Executes HandBrakeCLI encoding to AV1 10-bit and emits live progress."""
    conversion_started = pyqtSignal()
    progress_updated = pyqtSignal(float, float, int, str)  # (percent, fps, eta_seconds, status_text)
    log_line_received = pyqtSignal(str)
    conversion_finished = pyqtSignal(bool, str, str)  # (success, message, output_path)

    def __init__(
        self,
        hb_cli: Path,
        input_path: Path,
        output_path: Path,
        metadata: VideoMetadata,
        config: dict
    ):
        super().__init__()
        self.hb_cli = Path(hb_cli)
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.metadata = metadata
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self._is_cancelled = False

    def cancel(self):
        """Cancels the active conversion."""
        self._is_cancelled = True
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass

    def build_command(self) -> List[str]:
        """Builds exact HandBrakeCLI arguments preserving resolution and framerate."""
        rf = self.config.get("quality_rf", 26)
        preset = str(self.config.get("encoder_preset", "6"))

        cmd = [
            str(self.hb_cli),
            "-i", str(self.input_path),
            "-o", str(self.output_path),
            # Video Encoder: SVT-AV1 10-bit
            "-e", "svt_av1_10bit",
            "-q", str(rf),
            "--encoder-preset", preset,
            # Exact resolution preservation: no crop, auto anamorphic
            "--crop", "0:0:0:0",
            "--auto-anamorphic",
            # Exact framerate preservation: same as source, peak framerate
            "--rate", str(self.metadata.fps),
            "--pfr",
            # Audio passthrough
            "--all-audio",
            "--aencoder", "copy",
            "--audio-copy-mask", "aac,ac3,eac3,truehd,dts,dtshd,mp3,flac,opus",
            "--audio-fallback", "opus",
            # Subtitles & Chapters
            "--all-subtitles",
            "--markers",
            # JSON streaming output for exact progress reporting
            "--json"
        ]

        return cmd

    def run(self):
        self._is_cancelled = False
        self.conversion_started.emit()

        cmd = self.build_command()
        self.log_line_received.emit(f"Befehl: {' '.join(cmd)}")

        # Ensure output directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=get_windows_creation_flags()
            )

            in_json = False
            brace_depth = 0
            json_buf = []
            last_percent = 0.0

            # Regex fallback for standard HandBrake output
            prog_regex = re.compile(
                r"([\d\.]+)[\s]*%[\s]*\(([\d\.]+)[\s]*fps.*?ETA[\s]*([\d\w]+)\)",
                re.IGNORECASE
            )

            while True:
                if self._is_cancelled:
                    if self.output_path.exists():
                        try:
                            self.output_path.unlink()
                        except Exception:
                            pass
                    self.conversion_finished.emit(False, "Konvertierung vom Benutzer abgebrochen.", "")
                    return

                line = self.process.stdout.readline()
                if not line and self.process.poll() is not None:
                    break

                if not line:
                    continue

                line_clean = line.strip()
                if line_clean:
                    self.log_line_received.emit(line_clean)

                # Multiline JSON streaming parser
                if "Progress: {" in line:
                    in_json = True
                    brace_depth = 1
                    json_buf = ["{"]
                    continue
                elif in_json:
                    brace_depth += line.count("{") - line.count("}")
                    json_buf.append(line)
                    if brace_depth <= 0:
                        in_json = False
                        raw = "".join(json_buf)
                        try:
                            data = json.loads(raw)
                            state = data.get("State", "")

                            if state == "WORKING":
                                working = data.get("Working", {})
                                raw_prog = working.get("Progress", 0.0)
                                percent = float(raw_prog) * 100.0
                                rate = float(working.get("Rate", 0.0))
                                eta = int(working.get("ETASeconds", 0))
                                pass_num = working.get("Pass", 1)
                                pass_count = working.get("PassCount", 1)

                                last_percent = percent
                                status = f"Pass {pass_num}/{pass_count}" if pass_count > 1 else "Enkodiert AV1-10bit..."
                                self.progress_updated.emit(percent, rate, eta, status)

                            elif state == "MUXING":
                                self.progress_updated.emit(99.0, 0.0, 0, "Muxing / Fertigstellung...")

                            elif state == "WORKDONE":
                                self.progress_updated.emit(100.0, 0.0, 0, "Fertig!")
                        except Exception:
                            pass
                        continue

                # Regex fallback for non-JSON or mixed progress output
                match = prog_regex.search(line_clean)
                if match:
                    try:
                        pct = float(match.group(1))
                        fps = float(match.group(2))
                        eta_raw = match.group(3)
                        eta_sec = 0
                        h_match = re.search(r"(\d+)h", eta_raw)
                        m_match = re.search(r"(\d+)m", eta_raw)
                        s_match = re.search(r"(\d+)s", eta_raw)
                        if h_match:
                            eta_sec += int(h_match.group(1)) * 3600
                        if m_match:
                            eta_sec += int(m_match.group(1)) * 60
                        if s_match:
                            eta_sec += int(s_match.group(1))
                        self.progress_updated.emit(pct, fps, eta_sec, "Enkodiert AV1-10bit...")
                    except Exception:
                        pass

            exit_code = self.process.poll()

            if self._is_cancelled:
                self.conversion_finished.emit(False, "Abgebrochen.", "")
                return

            if exit_code == 0:
                self.progress_updated.emit(100.0, 0.0, 0, "Erfolgreich abgeschlossen!")
                self.conversion_finished.emit(
                    True,
                    f"Erfolgreich konvertiert:\n{self.output_path.name}",
                    str(self.output_path)
                )
            else:
                self.conversion_finished.emit(
                    False,
                    f"HandBrake beendete mit Fehlercode {exit_code}.",
                    ""
                )

        except Exception as e:
            self.conversion_finished.emit(False, f"Unerwarteter Fehler: {str(e)}", "")


def probe_video_metadata(file_path: Path, hb_cli: Path) -> Optional[VideoMetadata]:
    """Synchronously probes video metadata using HandBrakeCLI --scan --json."""
    try:
        cmd = [
            str(hb_cli),
            "-i", str(file_path),
            "--scan",
            "--json",
            "-t", "0"
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=get_windows_creation_flags()
        )

        full_output = []
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                full_output.append(line)

        output_text = "".join(full_output)

        json_marker = "JSON Title Set:"
        idx = output_text.find(json_marker)
        if idx == -1:
            idx = output_text.find('{"MainFeature"')
            if idx == -1:
                idx = output_text.find('"TitleList"')
                if idx != -1:
                    idx = output_text.rfind("{", 0, idx)

        if idx == -1:
            return None

        json_str = output_text[idx + len(json_marker):].strip()
        start_brace = json_str.find("{")
        if start_brace == -1:
            return None

        brace_count = 0
        json_end = -1
        for i, c in enumerate(json_str[start_brace:], start=start_brace):
            if c == "{":
                brace_count += 1
            elif c == "}":
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break

        if json_end == -1:
            return None

        json_body = json_str[start_brace:json_end]
        data = json.loads(json_body)
        titles = data.get("TitleList", [])
        if not titles:
            return None

        title = titles[0]
        geom = title.get("Geometry", {})
        width = geom.get("Width", 1920)
        height = geom.get("Height", 1080)
        par = geom.get("PAR", {})
        par_num = par.get("Num", 1)
        par_den = par.get("Den", 1)

        framerate = title.get("FrameRate", {})
        fps_num = framerate.get("Num", 30)
        fps_den = framerate.get("Den", 1)
        fps = (fps_num / fps_den) if fps_den else 30.0

        color = title.get("Color", {})
        bit_depth = color.get("BitDepth", 8)
        video_codec = title.get("VideoCodec", "Unbekannt")

        duration_obj = title.get("Duration", {})
        hours = duration_obj.get("Hours", 0)
        mins = duration_obj.get("Minutes", 0)
        secs = duration_obj.get("Seconds", 0)
        duration_seconds = hours * 3600 + mins * 60 + secs
        duration_str = f"{hours:02d}:{mins:02d}:{secs:02d}"

        audio_tracks = []
        for a in title.get("AudioList", []):
            lang = a.get("Language", "")
            desc = a.get("Description", "")
            codec = a.get("CodecName", "")
            ch = a.get("ChannelLayout", "")
            entry = f"{lang} ({codec.upper()}, {ch})" if (codec or ch) else desc
            audio_tracks.append(entry.strip())

        subtitle_tracks = []
        for s in title.get("SubtitleList", []):
            s_lang = s.get("Language", "Untertitel")
            s_name = s.get("Name", "")
            s_fmt = s.get("Format", "")
            entry = f"{s_lang} {s_name} [{s_fmt}]".strip()
            subtitle_tracks.append(entry)

        try:
            size_bytes = file_path.stat().st_size
            size_str = format_bytes(size_bytes)
        except Exception:
            size_str = "Unbekannt"

        par_str = f"{par_num}:{par_den}"
        dar_val = (width * par_num) / (height * par_den) if (height * par_den) else (width / height)
        dar_str = f"{dar_val:.2f}:1"

        return VideoMetadata(
            file_path=file_path,
            file_name=file_path.name,
            file_size_formatted=size_str,
            duration_str=duration_str,
            duration_seconds=duration_seconds,
            width=width,
            height=height,
            fps=fps,
            fps_str=f"{fps:.3f}".rstrip("0").rstrip("."),
            par_str=par_str,
            dar_str=dar_str,
            video_codec=video_codec,
            bit_depth=bit_depth,
            audio_tracks=audio_tracks,
            subtitle_tracks=subtitle_tracks,
            raw_title=title,
        )
    except Exception:
        return None


@dataclass
class QueueItem:
    file_path: Path
    file_name: str
    file_size_formatted: str
    target_path: Path
    status: str = "Wartend"  # Wartend, Konvertiert..., Fertig, Übersprungen, Fehler
    skip_reason: str = ""
    percent: float = 0.0
    rate_fps: float = 0.0
    eta_seconds: int = 0
    error_message: str = ""
    metadata: Optional[VideoMetadata] = None


VIDEO_EXTENSIONS_SET = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv",
    ".wmv", ".m4v", ".ts", ".m2ts", ".mpg", ".mpeg"
}


def scan_folder_for_queue(
    folder_path: Path,
    output_dir: Optional[Path],
    use_same_dir: bool,
    recursive: bool = False,
    skip_existing_av1: bool = True
) -> List[QueueItem]:
    """Scans folder for videos, identifying files and auto-skipping already converted AV1-10bit files."""
    items: List[QueueItem] = []
    if not folder_path.exists() or not folder_path.is_dir():
        return items

    if recursive:
        candidates = [p for p in folder_path.rglob("*") if p.is_file()]
    else:
        candidates = [p for p in folder_path.glob("*") if p.is_file()]

    video_files = [f for f in candidates if f.suffix.lower() in VIDEO_EXTENSIONS_SET]
    # Sort alphabetically
    video_files.sort(key=lambda p: p.name.lower())

    for f in video_files:
        stem_lower = f.stem.lower()
        is_av1_name = "_av1-10bit" in stem_lower or "[av1-10bit]" in stem_lower

        if use_same_dir or not output_dir:
            dest_dir = f.parent
        else:
            dest_dir = Path(output_dir)

        target_file = dest_dir / f"{f.stem}_AV1-10bit.mkv"
        target_exists = target_file.exists() and target_file.stat().st_size > 0

        try:
            sz_str = format_bytes(f.stat().st_size)
        except Exception:
            sz_str = "-"

        status = "Wartend"
        skip_reason = ""

        if skip_existing_av1:
            if is_av1_name:
                status = "Übersprungen"
                skip_reason = "Bereits AV1-10bit Datei"
            elif target_exists and f != target_file:
                status = "Übersprungen"
                skip_reason = f"AV1-10bit Zieldatei existiert bereits"

        item = QueueItem(
            file_path=f,
            file_name=f.name,
            file_size_formatted=sz_str,
            target_path=target_file,
            status=status,
            skip_reason=skip_reason,
            percent=100.0 if status == "Übersprungen" else 0.0
        )
        items.append(item)

    return items


class BatchConversionWorker(QThread):
    """Processes a queue of videos sequentially with AV1-10bit HandBrake encoding."""
    batch_started = pyqtSignal(int)  # total items
    item_started = pyqtSignal(int, object)  # (index, QueueItem)
    item_progress = pyqtSignal(int, float, float, int, str)  # (index, percent, fps, eta_sec, status_text)
    item_finished = pyqtSignal(int, object)  # (index, QueueItem)
    batch_progress = pyqtSignal(int, int, float)  # (completed_count, total_count, overall_percent)
    batch_finished = pyqtSignal(int, int, int)  # (converted_count, skipped_count, failed_count)
    log_line_received = pyqtSignal(str)

    def __init__(
        self,
        hb_cli: Path,
        queue: List[QueueItem],
        config: dict
    ):
        super().__init__()
        self.hb_cli = Path(hb_cli)
        self.queue = queue
        self.config = config
        self.active_worker: Optional[ConversionWorker] = None
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True
        if self.active_worker:
            self.active_worker.cancel()

    def run(self):
        self._is_cancelled = False
        total = len(self.queue)
        self.batch_started.emit(total)

        converted_count = 0
        skipped_count = 0
        failed_count = 0

        for idx, item in enumerate(self.queue):
            if self._is_cancelled:
                break

            # If already marked skipped by scan (e.g. filename or target exists)
            if item.status == "Übersprungen":
                skipped_count += 1
                self.item_finished.emit(idx, item)
                completed_so_far = converted_count + skipped_count + failed_count
                self.batch_progress.emit(completed_so_far, total, (completed_so_far / total) * 100.0)
                continue

            item.status = "Wird analysiert..."
            self.item_started.emit(idx, item)
            self.log_line_received.emit(f"=== [Batch {idx+1}/{total}] Analysiere: {item.file_name} ===")

            # Probe metadata
            meta = probe_video_metadata(item.file_path, self.hb_cli)
            if not meta:
                item.status = "Fehler"
                item.error_message = "Metadaten konnten nicht gelesen werden."
                failed_count += 1
                self.item_finished.emit(idx, item)
                completed_so_far = converted_count + skipped_count + failed_count
                self.batch_progress.emit(completed_so_far, total, (completed_so_far / total) * 100.0)
                continue

            item.metadata = meta

            # Check if source video is already AV1 10-bit
            if self.config.get("skip_existing_av1", True):
                if meta.video_codec.lower() in ["av1", "libdav1d"] and meta.bit_depth >= 10:
                    item.status = "Übersprungen"
                    item.skip_reason = "Quelle ist bereits AV1 10-Bit"
                    item.percent = 100.0
                    skipped_count += 1
                    self.log_line_received.emit(f"Übersprungen: {item.file_name} ist bereits AV1 10-Bit.")
                    self.item_finished.emit(idx, item)
                    completed_so_far = converted_count + skipped_count + failed_count
                    self.batch_progress.emit(completed_so_far, total, (completed_so_far / total) * 100.0)
                    continue

            # Start conversion of this item
            item.status = "Wird konvertiert..."
            self.active_worker = ConversionWorker(
                hb_cli=self.hb_cli,
                input_path=item.file_path,
                output_path=item.target_path,
                metadata=meta,
                config=self.config
            )

            current_idx = idx

            def on_item_prog(pct, fps, eta, st):
                item.percent = pct
                item.rate_fps = fps
                item.eta_seconds = eta
                self.item_progress.emit(current_idx, pct, fps, eta, st)

            self.active_worker.progress_updated.connect(on_item_prog)
            self.active_worker.log_line_received.connect(self.log_line_received.emit)

            # Run synchronously in this thread
            self.active_worker.run()

            if self._is_cancelled:
                item.status = "Abgebrochen"
                self.item_finished.emit(idx, item)
                break

            if item.target_path.exists() and item.target_path.stat().st_size > 0:
                item.status = "Fertig"
                item.percent = 100.0
                converted_count += 1
            else:
                item.status = "Fehler"
                failed_count += 1

            self.item_finished.emit(idx, item)
            completed_so_far = converted_count + skipped_count + failed_count
            self.batch_progress.emit(completed_so_far, total, (completed_so_far / total) * 100.0)

        self.batch_finished.emit(converted_count, skipped_count, failed_count)

