"""Build script to compile the native Windows Setup installer using PyInstaller.
Bypasses Inno Setup Temp-dropper execution to prevent Windows 11 Smart App Control Error 4551.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def build_installer():
    base_dir = Path(__file__).resolve().parent
    dist_dir = base_dir / "dist"
    exe_file = dist_dir / "HandBrakeAutoAV1.exe"
    icon_file = base_dir / "app_icon.ico"
    installer_script = base_dir / "installer" / "installer_gui.py"

    if not exe_file.exists():
        print("HandBrakeAutoAV1.exe wurde in dist/ nicht gefunden. Baue zuerst die EXE...")
        from build_exe import build
        build()

    # Kill any running setup instances
    if sys.platform == "win32":
        try:
            subprocess.run(["taskkill", "/F", "/IM", "HandBrakeAutoAV1_Setup.exe"], capture_output=True)
        except Exception:
            pass

    print("==================================================")
    print("Baue nativen HandBrake Auto AV1 Setup-Installer...")
    print("==================================================")

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", "HandBrakeAutoAV1_Setup",
        f"--icon={str(icon_file)}",
        f"--add-data={str(exe_file)};.",
        f"--add-data={str(icon_file)};.",
        str(installer_script)
    ]

    print(f"Ausführen: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=base_dir)

    if res.returncode == 0:
        setup_exe = dist_dir / "HandBrakeAutoAV1_Setup.exe"
        if setup_exe.exists():
            size_mb = setup_exe.stat().st_size / (1024 * 1024)
            print("==================================================")
            print("NATIVEN SETUP-INSTALLER ERFOLGREICH GEBAUT!")
            print(f"Setup-Datei: {setup_exe}")
            print(f"Dateigröße: {size_mb:.1f} MB")
            print("==================================================")
            return setup_exe
    else:
        print("Fehler beim Kompilieren des Installers!")
        sys.exit(res.returncode)


if __name__ == "__main__":
    build_installer()
