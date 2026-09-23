"""Helper script to download official HandBrakeCLI for Windows if not present."""

import os
import ssl
import sys
import urllib.request
import zipfile
from pathlib import Path

HANDBRAKE_VERSION = "1.11.2"
DOWNLOAD_URL = f"https://github.com/HandBrake/HandBrake/releases/download/{HANDBRAKE_VERSION}/HandBrakeCLI-{HANDBRAKE_VERSION}-win-x86_64.zip"


def ensure_handbrake_cli(target_dir: Path = None) -> Path:
    if target_dir is None:
        target_dir = Path(__file__).resolve().parent.parent / "bin"

    target_dir.mkdir(parents=True, exist_ok=True)
    target_exe = target_dir / "HandBrakeCLI.exe"

    if target_exe.exists():
        print(f"HandBrakeCLI already exists at {target_exe}")
        return target_exe

    print(f"Downloading HandBrakeCLI v{HANDBRAKE_VERSION} from {DOWNLOAD_URL}...")
    zip_path = target_dir / "HandBrakeCLI.zip"

    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        DOWNLOAD_URL,
        headers={"User-Agent": "HandBrakeAutoAV1-Builder"}
    )

    with urllib.request.urlopen(req, context=ctx) as response, open(zip_path, "wb") as out_file:
        out_file.write(response.read())

    print("Extracting HandBrakeCLI.exe...")
    with zipfile.ZipFile(zip_path, "r") as z:
        # HandBrake zip may contain HandBrakeCLI.exe directly or inside a folder
        found = False
        for member in z.namelist():
            if member.lower().endswith("handbrakecli.exe"):
                with z.open(member) as source, open(target_exe, "wb") as target:
                    target.write(source.read())
                found = True
                break

    if zip_path.exists():
        zip_path.unlink()

    if found and target_exe.exists():
        print(f"HandBrakeCLI successfully installed to {target_exe}")
        return target_exe
    else:
        raise RuntimeError("Could not find HandBrakeCLI.exe inside downloaded archive!")


if __name__ == "__main__":
    ensure_handbrake_cli()
