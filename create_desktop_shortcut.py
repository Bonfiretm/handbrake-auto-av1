import os
import subprocess
import sys
from pathlib import Path

def create_shortcut():
    desktop = Path(os.environ["USERPROFILE"]) / "Desktop"
    target_exe = sys.executable.replace("python.exe", "pythonw.exe")
    script_path = Path(__file__).resolve().parent / "app.py"
    work_dir = Path(__file__).resolve().parent
    icon_path = work_dir / "app_icon.ico"
    lnk_path = desktop / "HandBrake Auto AV1.lnk"

    vbs_content = f'''Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{lnk_path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{target_exe}"
oLink.Arguments = """{script_path}"""
oLink.WorkingDirectory = "{work_dir}"
oLink.IconLocation = "{icon_path},0"
oLink.Description = "HandBrake Auto AV1-10bit Converter"
oLink.Save
'''
    vbs_file = work_dir / "temp_shortcut.vbs"
    with open(vbs_file, "w", encoding="utf-8") as f:
        f.write(vbs_content)

    subprocess.run(["cscript", "//nologo", str(vbs_file)])
    if vbs_file.exists():
        vbs_file.unlink()

    print(f"Desktop Verknüpfung erfolgreich erstellt: {lnk_path}")

if __name__ == "__main__":
    create_shortcut()
