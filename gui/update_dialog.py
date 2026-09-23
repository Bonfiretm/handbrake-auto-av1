import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from core.updater import DownloadUpdateWorker, ReleaseInfo, apply_update_and_restart
from gui.styles import get_dark_theme


class UpdateDialog(QDialog):
    """Modern dark themed dialog displaying new release details and managing update downloads."""

    def __init__(self, release_info: ReleaseInfo, current_version: str, parent=None):
        super().__init__(parent)
        self.release_info = release_info
        self.current_version = current_version
        self.download_worker: Optional[DownloadUpdateWorker] = None
        self.downloaded_file: Optional[Path] = None

        self.setWindowTitle("Software-Update verfügbar")
        self.setMinimumWidth(560)
        self.setStyleSheet(get_dark_theme())
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        # Header with icon and version badges
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_lbl = QLabel("✨")
        icon_lbl.setStyleSheet("font-size: 32px;")
        header_layout.addWidget(icon_lbl)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)

        title_lbl = QLabel("Eine neue Version ist verfügbar!")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #f0f6fc;")
        title_vbox.addWidget(title_lbl)

        version_row = QHBoxLayout()
        version_row.setSpacing(8)

        old_badge = QLabel(f"Installiert: v{self.current_version.lstrip('v')}")
        old_badge.setStyleSheet(
            "background-color: #21262d; color: #8b949e; border: 1px solid #30363d; "
            "padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;"
        )
        version_row.addWidget(old_badge)

        arrow_lbl = QLabel("➜")
        arrow_lbl.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 13px;")
        version_row.addWidget(arrow_lbl)

        new_badge = QLabel(f"Neu: {self.release_info.version}")
        new_badge.setStyleSheet(
            "background-color: #1f6feb22; color: #58a6ff; border: 1px solid #1f6feb88; "
            "padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700;"
        )
        version_row.addWidget(new_badge)

        size_badge = QLabel(f"📦 {self.release_info.formatted_size}")
        size_badge.setStyleSheet(
            "background-color: #161b22; color: #c9d1d9; border: 1px solid #30363d; "
            "padding: 2px 8px; border-radius: 4px; font-size: 11px;"
        )
        version_row.addWidget(size_badge)
        version_row.addStretch()

        title_vbox.addLayout(version_row)
        header_layout.addLayout(title_vbox, stretch=1)
        layout.addLayout(header_layout)

        # Release Title
        if self.release_info.title and self.release_info.title != self.release_info.version:
            rel_title = QLabel(f"📌 {self.release_info.title}")
            rel_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #58a6ff; margin-top: 4px;")
            layout.addWidget(rel_title)

        # Changelog Card
        lbl_notes = QLabel("Änderungen & Neuerungen:")
        lbl_notes.setStyleSheet("font-size: 11px; font-weight: 600; color: #8b949e;")
        layout.addWidget(lbl_notes)

        self.notes_browser = QTextBrowser()
        self.notes_browser.setOpenExternalLinks(True)
        self.notes_browser.setPlainText(self.release_info.body if self.release_info.body.strip() else "Keine Versionshinweise hinterlegt.")
        self.notes_browser.setStyleSheet(
            "QTextBrowser { background-color: #0b0f17; border: 1px solid #1f2735; "
            "border-radius: 6px; padding: 10px; color: #c9d1d9; font-size: 12px; font-family: Segoe UI, sans-serif; }"
        )
        self.notes_browser.setMaximumHeight(140)
        layout.addWidget(self.notes_browser)

        # Download Progress Area (Initially Hidden)
        self.download_card = QFrame()
        self.download_card.setStyleSheet("background-color: #0b0f17; border: 1px solid #1f2735; border-radius: 6px; padding: 8px;")
        dl_layout = QVBoxLayout(self.download_card)
        dl_layout.setContentsMargins(10, 8, 10, 8)
        dl_layout.setSpacing(6)

        dl_status_row = QHBoxLayout()
        self.lbl_dl_status = QLabel("Bereite Download vor...")
        self.lbl_dl_status.setStyleSheet("font-size: 11px; font-weight: 600; color: #58a6ff;")
        dl_status_row.addWidget(self.lbl_dl_status)

        self.lbl_dl_speed = QLabel("0.0 MB/s")
        self.lbl_dl_speed.setStyleSheet("font-size: 11px; color: #8b949e;")
        dl_status_row.addWidget(self.lbl_dl_speed, alignment=Qt.AlignmentFlag.AlignRight)
        dl_layout.addLayout(dl_status_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background-color: #161b22; border: 1px solid #30363d; border-radius: 5px; height: 14px; text-align: center; color: #ffffff; font-size: 10px; font-weight: bold; } "
            "QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1f6feb, stop:1 #388bfd); border-radius: 4px; }"
        )
        dl_layout.addWidget(self.progress_bar)

        self.download_card.setVisible(False)
        layout.addWidget(self.download_card)

        # Action Buttons
        self.btn_row = QHBoxLayout()
        self.btn_row.setSpacing(10)

        self.btn_cancel = QPushButton("Später")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_row.addWidget(self.btn_cancel)

        self.btn_row.addStretch()

        self.btn_update = QPushButton("🚀 Jetzt aktualisieren")
        self.btn_update.setObjectName("PrimaryButton")
        self.btn_update.clicked.connect(self.start_download)
        self.btn_row.addWidget(self.btn_update)

        layout.addLayout(self.btn_row)

    def start_download(self):
        self.btn_update.setEnabled(False)
        self.btn_cancel.setText("Abbrechen")
        self.download_card.setVisible(True)
        self.adjustSize()

        self.download_worker = DownloadUpdateWorker(
            download_url=self.release_info.download_url,
            expected_size=self.release_info.asset_size_bytes
        )
        self.download_worker.progress.connect(self.on_download_progress)
        self.download_worker.download_finished.connect(self.on_download_finished)
        self.download_worker.download_error.connect(self.on_download_error)
        self.download_worker.start()

    def on_download_progress(self, downloaded: int, total: int, pct: float, speed_mbps: float):
        self.progress_bar.setValue(int(pct))
        dl_mb = downloaded / (1024 * 1024)
        tot_mb = total / (1024 * 1024)
        self.lbl_dl_status.setText(f"Lade Update herunter: {dl_mb:.1f} MB / {tot_mb:.1f} MB ({pct:.1f}%)")
        self.lbl_dl_speed.setText(f"{speed_mbps:.1f} MB/s")

    def on_download_finished(self, new_exe_path: Path):
        self.downloaded_file = new_exe_path
        self.progress_bar.setValue(100)
        self.lbl_dl_status.setText("Download abgeschlossen! Starte Update...")
        self.lbl_dl_status.setStyleSheet("font-size: 11px; font-weight: 700; color: #3fb950;")

        is_frozen = getattr(sys, "frozen", False)
        if is_frozen:
            success = apply_update_and_restart(new_exe_path)
            if success:
                QApplication.quit()
                sys.exit(0)
            else:
                QMessageBox.warning(
                    self,
                    "Automatisches Update",
                    f"Die neue Version wurde erfolgreich heruntergeladen:\n{new_exe_path}\n\n"
                    "Bitte ersetze deine alte Datei manuell."
                )
                self.accept()
        else:
            QMessageBox.information(
                self,
                "Update heruntergeladen (Entwicklungsmodus)",
                f"Die neue Executable wurde heruntergeladen nach:\n{new_exe_path}\n\n"
                "Im Python-Quellcode-Modus kann die laufende Datei nicht automatisch ersetzt werden."
            )
            self.accept()

    def on_download_error(self, err_msg: str):
        self.lbl_dl_status.setText("Fehler beim Herunterladen.")
        self.lbl_dl_status.setStyleSheet("font-size: 11px; font-weight: 700; color: #f85149;")
        self.btn_update.setEnabled(True)
        self.btn_cancel.setText("Schließen")
        QMessageBox.critical(self, "Download-Fehler", err_msg)

    def closeEvent(self, event):
        if self.download_worker and self.download_worker.isRunning():
            self.download_worker.cancel()
            self.download_worker.wait(1000)
        event.accept()
