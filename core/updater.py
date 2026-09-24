import os
import re
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.request
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from PyQt6.QtCore import QThread, pyqtSignal

APP_VERSION = "1.0.2"


def parse_version_tuple(version_str: str) -> Tuple[int, ...]:
    """Parses a version string into a comparable integer tuple, e.g. 'v1.2.3' -> (1, 2, 3)."""
    cleaned = version_str.strip().lstrip("vV")
    # Extract only digits and dots
    parts = re.findall(r"\d+", cleaned)
    if not parts:
        return (0, 0, 0)
    return tuple(int(p) for p in parts)


def is_newer_version(remote_ver: str, local_ver: str) -> bool:
    """Returns True if remote_ver is strictly newer than local_ver."""
    return parse_version_tuple(remote_ver) > parse_version_tuple(local_ver)


@dataclass
class ReleaseInfo:
    version: str
    title: str
    body: str
    html_url: str
    asset_name: str
    download_url: str
    asset_size_bytes: int
    published_at: str

    @property
    def formatted_size(self) -> str:
        mb = self.asset_size_bytes / (1024 * 1024)
        return f"{mb:.1f} MB"


def is_installed_mode() -> bool:
    """Returns True if the application is running from an installed directory (with uninstaller)."""
    if not getattr(sys, "frozen", False):
        return False
    exe_dir = Path(sys.executable).parent
    if (exe_dir / "unins000.exe").exists() or (exe_dir / "uninstall.bat").exists():
        return True
    exe_str = str(sys.executable).lower()
    if "\\programs\\handbrakeautoav1" in exe_str or "program files" in exe_str:
        return True
    return False


class CheckUpdateWorker(QThread):
    """Asynchronous worker to check for new releases on GitHub."""

    update_available = pyqtSignal(ReleaseInfo)
    no_update = pyqtSignal(str)
    check_error = pyqtSignal(str)

    def __init__(self, repo: str, current_version: str = APP_VERSION):
        super().__init__()
        self.repo = repo.strip()
        self.current_version = current_version

    def run(self):
        if not self.repo or "/" not in self.repo:
            self.check_error.emit("Ungültiges GitHub-Repository in der Konfiguration angegeben.")
            return

        api_url = f"https://api.github.com/repos/{self.repo}/releases/latest"
        req = urllib.request.Request(
            api_url,
            headers={
                "User-Agent": "HandBrakeAutoAV1-Updater",
                "Accept": "application/vnd.github.v3+json",
            }
        )

        try:
            # Create standard SSL context
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
                if response.status != 200:
                    self.check_error.emit(f"GitHub API antwortete mit Status {response.status}.")
                    return
                data = json.loads(response.read().decode("utf-8"))

            tag_name = data.get("tag_name", "").strip()
            if not tag_name:
                self.no_update.emit(self.current_version)
                return

            if not is_newer_version(tag_name, self.current_version):
                self.no_update.emit(self.current_version)
                return

            # Find executable asset based on installed vs portable mode
            assets = data.get("assets", [])
            target_asset = None
            is_installed = is_installed_mode()

            if is_installed:
                # Installed mode: prefer Setup installer
                for asset in assets:
                    name = asset.get("name", "").lower()
                    if name.endswith(".exe") and ("setup" in name or "installer" in name):
                        target_asset = asset
                        break
            else:
                # Portable mode: prefer standalone portable .exe
                for asset in assets:
                    name = asset.get("name", "").lower()
                    if name.endswith(".exe") and "setup" not in name and "installer" not in name and "handbrake" in name:
                        target_asset = asset
                        break

            # Fallbacks: try any handbrake exe, then any exe
            if not target_asset:
                for asset in assets:
                    name = asset.get("name", "").lower()
                    if name.endswith(".exe") and "handbrake" in name:
                        target_asset = asset
                        break

            if not target_asset:
                for asset in assets:
                    if asset.get("name", "").lower().endswith(".exe"):
                        target_asset = asset
                        break

            if not target_asset:
                self.check_error.emit(
                    f"Neue Version {tag_name} auf GitHub gefunden, enthält jedoch kein .exe Asset zum Download."
                )
                return

            info = ReleaseInfo(
                version=tag_name,
                title=data.get("name", tag_name),
                body=data.get("body", "Keine Versionshinweise vorhanden."),
                html_url=data.get("html_url", f"https://github.com/{self.repo}/releases/latest"),
                asset_name=target_asset.get("name", "HandBrakeAutoAV1.exe"),
                download_url=target_asset.get("browser_download_url", ""),
                asset_size_bytes=target_asset.get("size", 0),
                published_at=data.get("published_at", "")[:10]
            )

            self.update_available.emit(info)

        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.check_error.emit(
                    f"Noch keine Releases im Repository '{self.repo}' auf GitHub veröffentlicht."
                )
            elif e.code == 403:
                self.check_error.emit("GitHub API-Ratenlimit erreicht. Bitte später erneut versuchen.")
            else:
                self.check_error.emit(f"Fehler bei GitHub-Anfrage: HTTP {e.code}")
        except urllib.error.URLError as e:
            self.check_error.emit(f"Keine Internetverbindung zu GitHub möglich: {e.reason}")
        except Exception as e:
            self.check_error.emit(f"Unerwarteter Fehler bei Update-Prüfung: {e}")


class DownloadUpdateWorker(QThread):
    """Asynchronous worker to download the update executable."""

    progress = pyqtSignal(int, int, float, float)  # downloaded, total, percent, speed_mbps
    download_finished = pyqtSignal(Path)
    download_error = pyqtSignal(str)

    def __init__(self, download_url: str, expected_size: int = 0, asset_name: str = "HandBrakeAutoAV1.exe"):
        super().__init__()
        self.download_url = download_url
        self.expected_size = expected_size
        self.asset_name = asset_name or "HandBrakeAutoAV1.exe"
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            temp_dir = Path(tempfile.gettempdir()) / "HandBrakeAutoAV1_Update"
            temp_dir.mkdir(parents=True, exist_ok=True)
            safe_name = re.sub(r'[\\/*?:"<>|]', "", self.asset_name)
            if not safe_name.lower().endswith(".exe"):
                safe_name += ".exe"
            target_file = temp_dir / safe_name

            if target_file.exists():
                try:
                    target_file.unlink()
                except Exception:
                    pass

            req = urllib.request.Request(
                self.download_url,
                headers={"User-Agent": "HandBrakeAutoAV1-Updater"}
            )

            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=30, context=ctx) as response:
                total_size = int(response.headers.get("Content-Length", self.expected_size))
                downloaded = 0
                chunk_size = 64 * 1024  # 64 KB chunks
                start_time = time.time()

                with open(target_file, "wb") as f:
                    while True:
                        if self._is_cancelled:
                            target_file.unlink(missing_ok=True)
                            return

                        chunk = response.read(chunk_size)
                        if not chunk:
                            break

                        f.write(chunk)
                        downloaded += len(chunk)

                        elapsed = max(0.001, time.time() - start_time)
                        speed_mbps = (downloaded / (1024 * 1024)) / elapsed
                        pct = (downloaded / total_size * 100) if total_size > 0 else 0.0

                        self.progress.emit(downloaded, total_size, pct, speed_mbps)

            if not self._is_cancelled:
                self.download_finished.emit(target_file)

        except Exception as e:
            self.download_error.emit(f"Download fehlgeschlagen: {e}")


def apply_update_and_restart(new_exe_path: Path) -> bool:
    """Replaces the running executable with the newly downloaded one and restarts it."""
    is_frozen = getattr(sys, "frozen", False)

    if not is_frozen:
        # Development mode: Cannot overwrite running python script
        dist_exe = Path(__file__).resolve().parent.parent / "dist" / "HandBrakeAutoAV1.exe"
        if dist_exe.exists():
            current_exe = dist_exe
        else:
            return False
    else:
        current_exe = Path(sys.executable).resolve()

    pid = os.getpid()
    bat_file = Path(tempfile.gettempdir()) / "handbrake_updater.bat"
    is_setup = "setup" in new_exe_path.name.lower() or "installer" in new_exe_path.name.lower()

    if is_setup:
        local_app_data = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        installed_exe = Path(local_app_data) / "Programs" / "HandBrakeAutoAV1" / "HandBrakeAutoAV1.exe"
        if current_exe.exists() and "programs\\handbrakeautoav1" in str(current_exe).lower():
            target_to_launch = current_exe
        else:
            target_to_launch = installed_exe

        bat_content = f"""@echo off
setlocal enabledelayedexpansion
title HandBrake Auto AV1 Updater

set PID={pid}
set "SETUP_EXE={str(new_exe_path.resolve())}"
set "TARGET_EXE={str(target_to_launch.resolve())}"

:: 1. Wait for parent process to exit
:WAIT_PID
tasklist /fi "PID eq %PID%" 2>nul | find "%PID%" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto WAIT_PID
)

timeout /t 1 /nobreak >nul

:: 2. Run Setup silently with no automatic restart
start /wait "" "%SETUP_EXE%" /silent /norestart
del "%SETUP_EXE%" 2>nul

:: 3. Launch newly installed application
if exist "%TARGET_EXE%" (
    start "" "%TARGET_EXE%"
)

:: 4. Clean up this batch script
(goto) 2>nul & del "%~f0"
"""
    else:
        bat_content = f"""@echo off
setlocal enabledelayedexpansion
title HandBrake Auto AV1 Updater

set PID={pid}
set "NEW_EXE={str(new_exe_path.resolve())}"
set "TARGET_EXE={str(current_exe.resolve())}"
set "OLD_EXE={str(current_exe.resolve())}.old"

:: 1. Wait for parent process to exit
:WAIT_PID
tasklist /fi "PID eq %PID%" 2>nul | find "%PID%" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto WAIT_PID
)

timeout /t 1 /nobreak >nul

:: 2. Rename-replace strategy: rename target -> old, then move new -> target
set RETRY=0
:RETRY_LOOP
del "%OLD_EXE%" >nul 2>&1
move /y "%TARGET_EXE%" "%OLD_EXE%" >nul 2>&1
if not errorlevel 1 goto MOVE_NEW

set /a RETRY+=1
if !RETRY! leq 10 (
    timeout /t 1 /nobreak >nul
    goto RETRY_LOOP
)

:MOVE_NEW
move /y "%NEW_EXE%" "%TARGET_EXE%" >nul 2>&1
if errorlevel 1 (
    copy /y "%NEW_EXE%" "%TARGET_EXE%" >nul 2>&1
)

:: 3. Clean up temporary files
del "%OLD_EXE%" >nul 2>&1
del "%NEW_EXE%" >nul 2>&1

:: 4. Start updated application
if exist "%TARGET_EXE%" (
    start "" "%TARGET_EXE%"
)

:: 5. Clean up this batch script
(goto) 2>nul & del "%~f0"
"""

    try:
        with open(bat_file, "w", encoding="ascii", errors="ignore") as f:
            f.write(bat_content)

        flags = 0
        if sys.platform == "win32":
            flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

        subprocess.Popen(
            ["cmd.exe", "/c", str(bat_file)],
            creationflags=flags,
            close_fds=True
        )
        return True
    except Exception as e:
        print(f"Fehler beim Starten des Updaters: {e}")
        return False
