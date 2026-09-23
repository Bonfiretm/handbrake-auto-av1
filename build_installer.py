"""Build script to compile the Windows Setup installer using Inno Setup."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def locate_iscc() -> Path | None:
    """Finds Inno Setup Compiler (ISCC.exe)."""
    # 1. System PATH
    found = shutil.which("iscc")
    if found:
        return Path(found)

    # 2. Standard install directories
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
        Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe"),
        Path("C:/Program Files/Inno Setup 6/ISCC.exe"),
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return None


def build_installer():
    base_dir = Path(__file__).resolve().parent
    dist_dir = base_dir / "dist"
    exe_file = dist_dir / "HandBrakeAutoAV1.exe"
    iss_file = base_dir / "installer" / "setup.iss"

    if not exe_file.exists():
        print("HandBrakeAutoAV1.exe wurde in dist/ nicht gefunden. Baue zuerst die EXE...")
        from build_exe import build
        build()

    iscc_path = locate_iscc()
    if not iscc_path:
        print("Inno Setup Compiler (ISCC.exe) wurde nicht gefunden. Lade Inno Setup herunter...")
        try:
            import tempfile
            import urllib.request
            url = "https://github.com/jrsoftware/issrc/releases/download/is-7_1_0/innosetup-7.1.0-x64.exe"
            tmp_installer = Path(tempfile.gettempdir()) / "innosetup-setup.exe"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as resp, open(tmp_installer, "wb") as f:
                f.write(resp.read())
            target_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Programs" / "Inno Setup 6"
            subprocess.run([str(tmp_installer), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER", f"/DIR={str(target_dir)}"])
            iscc_path = locate_iscc()
        except Exception as e:
            print(f"Automatischer Inno Setup Download fehlgeschlagen: {e}")

    if not iscc_path:
        print("\nFEHLER: Inno Setup konnte nicht installiert werden!")
        sys.exit(1)

    print("==================================================")
    print(f"Kompiliere Setup-Installer mit: {iscc_path}")
    print("==================================================")

    cmd = [str(iscc_path), str(iss_file)]
    res = subprocess.run(cmd, cwd=base_dir)

    if res.returncode == 0:
        setup_exe = dist_dir / "HandBrakeAutoAV1_Setup.exe"
        if setup_exe.exists():
            size_mb = setup_exe.stat().st_size / (1024 * 1024)
            print("==================================================")
            print("INSTALLER ERFOLGREICH GEBAUT!")
            print(f"Setup-Datei: {setup_exe}")
            print(f"Dateigröße: {size_mb:.1f} MB")
            print("==================================================")
            return setup_exe
    else:
        print("Fehler beim Kompilieren des Installers!")
        sys.exit(res.returncode)


if __name__ == "__main__":
    build_installer()
