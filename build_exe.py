"""Build script to create a standalone Windows EXE for HandBrake Auto AV1-10bit."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def build():
    base_dir = Path(__file__).resolve().parent
    bin_hb = base_dir / "bin" / "HandBrakeCLI.exe"
    icon_file = base_dir / "app_icon.ico"
    png_icon = base_dir / "app_icon.png"

    if not bin_hb.exists():
        print("HandBrakeCLI.exe nicht gefunden. Lade offizielle Version herunter...")
        from scripts.download_handbrake import ensure_handbrake_cli
        ensure_handbrake_cli()

    # Kill any existing running instance so dist/HandBrakeAutoAV1.exe is not file-locked
    if sys.platform == "win32":
        try:
            subprocess.run(["taskkill", "/F", "/IM", "HandBrakeAutoAV1.exe"], capture_output=True)
        except Exception:
            pass

    if not icon_file.exists():
        print("Generiere App-Icon...")
        from create_icon import generate_icon
        generate_icon()

    print("==================================================")
    print("Baue HandBrake Auto AV1-10bit Standalone .EXE...")
    print("==================================================")

    assets_dir = base_dir / "assets"

    # PyInstaller arguments
    # On Windows: separator is ';'
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", "HandBrakeAutoAV1",
        f"--icon={str(icon_file)}",
        f"--add-data={str(png_icon)};.",
        f"--add-data={str(icon_file)};.",
        f"--add-data={str(assets_dir)};assets",
        f"--add-binary={str(bin_hb)};bin",
        str(base_dir / "app.py")
    ]

    print(f"Ausführen: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=base_dir)

    if result.returncode == 0:
        exe_path = base_dir / "dist" / "HandBrakeAutoAV1.exe"
        print("\n==================================================")
        print("BUILD ERFOLGREICH!")
        print(f"Fertige EXE: {exe_path}")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"Dateigröße: {size_mb:.1f} MB")
        print("==================================================")
    else:
        print("\nBUILD FEHLGESCHLAGEN!")
        sys.exit(result.returncode)


if __name__ == "__main__":
    build()
