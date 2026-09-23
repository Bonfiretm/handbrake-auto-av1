import os
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow


def main():
    # Windows taskbar icon grouping support
    if sys.platform == "win32":
        try:
            import ctypes
            myappid = "antigravity.handbrake.autoav1.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("HandBrake Auto AV1-10bit")
    app.setOrganizationName("HandBrakeAuto")

    # Set default clean UI font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Load Icon
    icon_path = Path(__file__).resolve().parent / "app_icon.png"
    if hasattr(sys, "_MEIPASS"):
        meipass_icon = Path(sys._MEIPASS) / "app_icon.png"
        if meipass_icon.exists():
            icon_path = meipass_icon

    if icon_path.exists():
        icon = QIcon(str(icon_path))
        app.setWindowIcon(icon)

    window = MainWindow()
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
