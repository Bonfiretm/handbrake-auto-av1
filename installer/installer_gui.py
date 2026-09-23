"""Modern Native Windows Setup Wizard for HandBrake Auto AV1-10bit.
Bypasses Inno Setup Temp-Execution blocks (Smart App Control Error 4551).
"""

import os
import shutil
import subprocess
import sys
import winreg
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "HandBrake Auto AV1-10bit"
APP_VERSION = "1.0.1"
PUBLISHER = "Bonfiretm"
DEFAULT_INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "Programs" / "HandBrakeAutoAV1"


def get_bundled_payload_path() -> Path:
    """Finds the bundled HandBrakeAutoAV1.exe inside PyInstaller bundle or local dist."""
    if hasattr(sys, "_MEIPASS"):
        # Running inside PyInstaller bundle
        bundle_dir = Path(sys._MEIPASS)
        cand = bundle_dir / "HandBrakeAutoAV1.exe"
        if cand.exists():
            return cand

    # Running from script / dev
    base_dir = Path(__file__).resolve().parent.parent
    cand = base_dir / "dist" / "HandBrakeAutoAV1.exe"
    if cand.exists():
        return cand

    raise FileNotFoundError("Bündel-Datei HandBrakeAutoAV1.exe wurde nicht gefunden.")


def get_bundled_icon_path() -> Path:
    if hasattr(sys, "_MEIPASS"):
        cand = Path(sys._MEIPASS) / "app_icon.ico"
        if cand.exists():
            return cand
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "app_icon.ico"


def create_windows_shortcut(target_exe: Path, shortcut_path: Path, icon_path: Path, description: str):
    """Creates a Windows .lnk shortcut using PowerShell without requiring extra modules."""
    ps_cmd = f"""
    $WshShell = New-Object -comObject WScript.Shell;
    $Shortcut = $WshShell.CreateShortcut("{str(shortcut_path)}");
    $Shortcut.TargetPath = "{str(target_exe)}";
    $Shortcut.WorkingDirectory = "{str(target_exe.parent)}";
    $Shortcut.IconLocation = "{str(icon_path)},0";
    $Shortcut.Description = "{description}";
    $Shortcut.Save();
    """
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NO_WINDOW
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], creationflags=flags)


def register_in_windows_uninstall(install_dir: Path, target_exe: Path, icon_path: Path):
    """Registers application in Windows 'Apps & Features' registry."""
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\HandBrakeAutoAV1"
    uninstall_bat = install_dir / "uninstall.bat"

    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, PUBLISHER)
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(icon_path))
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(install_dir))
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'cmd.exe /c "{str(uninstall_bat)}"')
        winreg.SetValueEx(key, "QuietUninstallString", 0, winreg.REG_SZ, f'cmd.exe /c "{str(uninstall_bat)}" /silent')
        winreg.SetValueEx(key, "URLInfoAbout", 0, winreg.REG_SZ, "https://github.com/Bonfiretm/handbrake-auto-av1")
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Warnung: Konnte Registry-Eintrag nicht schreiben: {e}")


def create_uninstaller_script(install_dir: Path):
    """Creates a self-deleting Windows uninstall batch script."""
    uninstall_bat = install_dir / "uninstall.bat"
    desktop_link = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop" / f"{APP_NAME}.lnk"
    start_menu_dir = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / APP_NAME

    content = f"""@echo off
title Deinstallation von {APP_NAME}
echo Deinstalliere {APP_NAME}...

taskkill /F /IM HandBrakeAutoAV1.exe >nul 2>&1
timeout /t 1 /nobreak >nul

del "{str(desktop_link)}" >nul 2>&1
rmdir /s /q "{str(start_menu_dir)}" >nul 2>&1

reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\HandBrakeAutoAV1" /f >nul 2>&1

cd ..
timeout /t 1 /nobreak >nul
rmdir /s /q "{str(install_dir)}" >nul 2>&1

if "%1"=="/silent" goto END
msg * "{APP_NAME} wurde erfolgreich von deinem PC deinstalliert."
:END
"""
    with open(uninstall_bat, "w", encoding="ascii", errors="ignore") as f:
        f.write(content)


class InstallWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, target_dir: Path, create_desktop: bool, create_startmenu: bool):
        super().__init__()
        self.target_dir = target_dir
        self.create_desktop = create_desktop
        self.create_startmenu = create_startmenu

    def run(self):
        try:
            self.progress.emit(10, "Beende eventuell laufende Instanzen...")
            subprocess.run(["taskkill", "/F", "/IM", "HandBrakeAutoAV1.exe"], capture_output=True)

            self.progress.emit(25, "Erstelle Zielverzeichnis...")
            self.target_dir.mkdir(parents=True, exist_ok=True)

            self.progress.emit(45, "Kopiere Programmdateien...")
            payload_exe = get_bundled_payload_path()
            target_exe = self.target_dir / "HandBrakeAutoAV1.exe"
            shutil.copy2(payload_exe, target_exe)

            icon_source = get_bundled_icon_path()
            target_icon = self.target_dir / "app_icon.ico"
            if icon_source.exists():
                shutil.copy2(icon_source, target_icon)

            # Copy uninstaller marker
            marker_unins = self.target_dir / "unins000.exe"
            # Touch or copy small marker so updater knows it is installed
            with open(marker_unins, "w") as f:
                f.write("installed")

            self.progress.emit(70, "Erstelle Verknüpfungen...")
            if self.create_desktop:
                desktop_dir = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
                link_path = desktop_dir / f"{APP_NAME}.lnk"
                create_windows_shortcut(target_exe, link_path, target_icon, APP_NAME)

            if self.create_startmenu:
                start_menu_programs = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / APP_NAME
                start_menu_programs.mkdir(parents=True, exist_ok=True)
                link_path = start_menu_programs / f"{APP_NAME}.lnk"
                create_windows_shortcut(target_exe, link_path, target_icon, APP_NAME)

            self.progress.emit(85, "Registriere Deinstallationsprogramm...")
            create_uninstaller_script(self.target_dir)
            register_in_windows_uninstall(self.target_dir, target_exe, target_icon)

            self.progress.emit(100, "Installation abgeschlossen!")
            self.finished.emit(True, "Installation erfolgreich abgeschlossen.")

        except Exception as e:
            self.finished.emit(False, str(e))


class SetupWindow(QWidget):
    """PyQt6 Setup Wizard."""

    def __init__(self, silent: bool = False):
        super().__init__()
        self.silent = silent
        self.setWindowTitle(f"{APP_NAME} Setup (v{APP_VERSION})")
        self.setFixedSize(560, 420)
        self.target_dir = DEFAULT_INSTALL_DIR

        icon_path = get_bundled_icon_path()
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.apply_dark_theme()
        self.init_ui()

        if self.silent:
            self.start_installation()

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #0d1117;
                color: #c9d1d9;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                background: transparent;
            }
            QLineEdit {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 6px 10px;
                color: #f0f6fc;
                font-size: 12px;
            }
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 7px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #30363d;
                color: #f0f6fc;
            }
            QPushButton#PrimaryButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1f6feb, stop:1 #388bfd);
                color: #ffffff;
                border: none;
                font-weight: 700;
            }
            QPushButton#PrimaryButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #388bfd, stop:1 #58a6ff);
            }
            QProgressBar {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                height: 16px;
                text-align: center;
                color: #ffffff;
                font-size: 11px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1f6feb, stop:1 #2ea043);
                border-radius: 5px;
            }
            QCheckBox {
                background: transparent;
                font-size: 12px;
                color: #c9d1d9;
                spacing: 8px;
            }
        """)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        # Header
        header = QHBoxLayout()
        header.setSpacing(12)

        icon_lbl = QLabel("⚡")
        icon_lbl.setStyleSheet("font-size: 32px;")
        header.addWidget(icon_lbl)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        title_lbl = QLabel(f"Installation von {APP_NAME}")
        title_lbl.setStyleSheet("font-size: 17px; font-weight: 800; color: #58a6ff;")
        sub_lbl = QLabel(f"Version {APP_VERSION} • AV1 10-Bit Videokonverter für Windows")
        sub_lbl.setStyleSheet("font-size: 11px; color: #8b949e;")
        title_vbox.addWidget(title_lbl)
        title_vbox.addWidget(sub_lbl)
        header.addLayout(title_vbox, stretch=1)
        layout.addLayout(header)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #21262d; max-height: 1px;")
        layout.addWidget(sep)

        # Installation Directory Selector
        dir_lbl = QLabel("Installationsordner:")
        dir_lbl.setStyleSheet("font-weight: 600; font-size: 12px; color: #f0f6fc;")
        layout.addWidget(dir_lbl)

        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)
        self.txt_dir = QLineEdit(str(self.target_dir))
        dir_row.addWidget(self.txt_dir, stretch=1)

        self.btn_browse = QPushButton("Durchsuchen...")
        self.btn_browse.clicked.connect(self.browse_folder)
        dir_row.addWidget(self.btn_browse)
        layout.addLayout(dir_row)

        desc_lbl = QLabel("Wird im Benutzerverzeichnis ohne Administrator-Zwang installiert.")
        desc_lbl.setStyleSheet("font-size: 11px; color: #8b949e;")
        layout.addWidget(desc_lbl)

        # Checkboxes
        layout.addSpacing(6)
        self.cb_desktop = QCheckBox("Desktop-Verknüpfung erstellen")
        self.cb_desktop.setChecked(True)
        layout.addWidget(self.cb_desktop)

        self.cb_startmenu = QCheckBox("Startmenü-Eintrag erstellen")
        self.cb_startmenu.setChecked(True)
        layout.addWidget(self.cb_startmenu)

        self.cb_launch = QCheckBox("Nach der Installation sofort starten")
        self.cb_launch.setChecked(True)
        layout.addWidget(self.cb_launch)

        # Progress bar
        layout.addSpacing(6)
        self.lbl_status = QLabel("Bereit zur Installation.")
        self.lbl_status.setStyleSheet("font-size: 11px; color: #8b949e;")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        layout.addStretch()

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_cancel = QPushButton("Abbrechen")
        self.btn_cancel.clicked.connect(self.close)
        btn_row.addWidget(self.btn_cancel)

        btn_row.addStretch()

        self.btn_install = QPushButton("🚀 Installieren")
        self.btn_install.setObjectName("PrimaryButton")
        self.btn_install.clicked.connect(self.start_installation)
        btn_row.addWidget(self.btn_install)

        layout.addLayout(btn_row)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Installationsordner wählen", self.txt_dir.text())
        if folder:
            self.txt_dir.setText(folder)
            self.target_dir = Path(folder)

    def start_installation(self):
        self.target_dir = Path(self.txt_dir.text().strip())
        self.btn_install.setEnabled(False)
        self.btn_browse.setEnabled(False)
        self.txt_dir.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setVisible(True)

        self.worker = InstallWorker(
            target_dir=self.target_dir,
            create_desktop=self.cb_desktop.isChecked(),
            create_startmenu=self.cb_startmenu.isChecked()
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_progress(self, val: int, msg: str):
        self.progress_bar.setValue(val)
        self.lbl_status.setText(msg)

    def on_finished(self, success: bool, msg: str):
        if self.silent:
            if success and self.cb_launch.isChecked():
                target_exe = self.target_dir / "HandBrakeAutoAV1.exe"
                subprocess.Popen([str(target_exe)])
            sys.exit(0 if success else 1)

        if success:
            self.progress_bar.setValue(100)
            self.lbl_status.setText("✓ Erfolgreich installiert!")
            self.lbl_status.setStyleSheet("font-size: 12px; font-weight: bold; color: #3fb950;")
            self.btn_install.setText("Fertigstellen")
            self.btn_install.setEnabled(True)
            self.btn_install.clicked.disconnect()
            self.btn_install.clicked.connect(self.finish_setup)
            self.btn_cancel.setVisible(False)
        else:
            QMessageBox.critical(self, "Fehler", f"Installation fehlgeschlagen:\n{msg}")
            self.btn_install.setEnabled(True)
            self.btn_cancel.setEnabled(True)

    def finish_setup(self):
        if self.cb_launch.isChecked():
            target_exe = self.target_dir / "HandBrakeAutoAV1.exe"
            if target_exe.exists():
                subprocess.Popen([str(target_exe)])
        self.close()


def main():
    silent = "/silent" in [a.lower() for a in sys.argv] or "--silent" in [a.lower() for a in sys.argv]
    app = QApplication(sys.argv)
    w = SetupWindow(silent=silent)
    if not silent:
        w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
