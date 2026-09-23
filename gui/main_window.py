import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.config import load_config, save_config
from core.handbrake import (
    BatchConversionWorker,
    ConversionWorker,
    QueueItem,
    VideoMetadata,
    VideoScanWorker,
    locate_handbrake_cli,
    scan_folder_for_queue,
)
from core.updater import APP_VERSION, CheckUpdateWorker, ReleaseInfo
from gui.styles import get_dark_theme
from gui.update_dialog import UpdateDialog

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv",
    ".wmv", ".m4v", ".ts", ".m2ts", ".mpg", ".mpeg"
}


class DropZoneWidget(QFrame):
    """Large interactive drag and drop target zone for both files and folders."""

    def __init__(self, on_file_dropped_callback, on_folder_dropped_callback, on_click_callback):
        super().__init__()
        self.setObjectName("DropZone")
        self.setProperty("dragHover", "false")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.on_file_dropped = on_file_dropped_callback
        self.on_folder_dropped = on_folder_dropped_callback
        self.on_click = on_click_callback

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(4)

        self.icon_label = QLabel("📥")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 32px;")
        layout.addWidget(self.icon_label)

        self.title_label = QLabel("Video oder ganzen Ordner hier hineinziehen")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 15px; font-weight: 700; color: #f0f6fc;")
        layout.addWidget(self.title_label)

        self.sub_label = QLabel("Klicken für Datei • Unterstützt MP4, MKV, MOV, AVI etc. • AV1-10bit wird automatisch übersprungen")
        self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_label.setStyleSheet("font-size: 11px; color: #8b949e;")
        layout.addWidget(self.sub_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.on_click()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                p = Path(url.toLocalFile())
                if p.is_dir() or p.suffix.lower() in VIDEO_EXTENSIONS:
                    event.acceptProposedAction()
                    self.setProperty("dragHover", "true")
                    self.style().unpolish(self)
                    self.style().polish(self)
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.setProperty("dragHover", "false")
        self.style().unpolish(self)
        self.style().polish(self)
        event.accept()

    def dropEvent(self, event: QDropEvent):
        self.setProperty("dragHover", "false")
        self.style().unpolish(self)
        self.style().polish(self)

        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.is_dir():
                self.on_folder_dropped(path)
                event.acceptProposedAction()
                return
            elif path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS:
                self.on_file_dropped(path)
                event.acceptProposedAction()
                return
        event.ignore()


class CompactDropZoneWidget(QFrame):
    """Compact drop zone banner displayed when a file or folder is already active."""

    def __init__(self, on_file_dropped_callback, on_folder_dropped_callback, on_click_callback):
        super().__init__()
        self.setObjectName("CompactDropZone")
        self.setProperty("dragHover", "false")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.on_file_dropped = on_file_dropped_callback
        self.on_folder_dropped = on_folder_dropped_callback
        self.on_click = on_click_callback

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 5, 12, 5)
        layout.setSpacing(8)

        lbl_icon = QLabel("🔄")
        lbl_icon.setStyleSheet("font-size: 14px;")
        layout.addWidget(lbl_icon)

        self.lbl_text = QLabel("Anderes Video oder neuen Ordner hier hineinziehen oder klicken zum Wechseln")
        self.lbl_text.setStyleSheet("font-size: 12px; color: #8b949e; font-weight: 500;")
        layout.addWidget(self.lbl_text)
        layout.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.on_click()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                p = Path(url.toLocalFile())
                if p.is_dir() or p.suffix.lower() in VIDEO_EXTENSIONS:
                    event.acceptProposedAction()
                    self.setProperty("dragHover", "true")
                    self.style().unpolish(self)
                    self.style().polish(self)
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.setProperty("dragHover", "false")
        self.style().unpolish(self)
        self.style().polish(self)
        event.accept()

    def dropEvent(self, event: QDropEvent):
        self.setProperty("dragHover", "false")
        self.style().unpolish(self)
        self.style().polish(self)

        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.is_dir():
                self.on_folder_dropped(path)
                event.acceptProposedAction()
                return
            elif path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS:
                self.on_file_dropped(path)
                event.acceptProposedAction()
                return
        event.ignore()


class MainWindow(QWidget):
    """Main Application Window for HandBrake Auto AV1-10bit Converter."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("HandBrake Auto AV1-10bit Converter")
        self.resize(880, 620)
        self.setMinimumSize(800, 420)

        self.config = load_config()
        self.hb_cli = locate_handbrake_cli()

        # State
        self.mode = "single"  # "single" or "batch"
        self.current_metadata: Optional[VideoMetadata] = None
        self.batch_queue: List[QueueItem] = []
        self.current_folder: Optional[Path] = None

        # Workers
        self.scan_worker: Optional[VideoScanWorker] = None
        self.convert_worker: Optional[ConversionWorker] = None
        self.batch_worker: Optional[BatchConversionWorker] = None
        self.update_worker: Optional[CheckUpdateWorker] = None
        self.last_output_file: Optional[Path] = None

        self.init_ui()
        self.check_handbrake()

    def check_handbrake(self):
        if not self.hb_cli or not self.hb_cli.exists():
            QMessageBox.warning(
                self,
                "HandBrakeCLI nicht gefunden",
                "HandBrakeCLI.exe wurde weder im 'bin'-Ordner noch auf dem System gefunden.\n"
                "Bitte stelle sicher, dass HandBrakeCLI vorhanden ist."
            )

    def init_ui(self):
        self.setStyleSheet(get_dark_theme())

        # Main Root Layout holding the Scroll Area
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Scroll Area for responsive sizing on any display resolution
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("MainScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root_layout.addWidget(self.scroll_area)

        # Inner container widget inside Scroll Area
        self.container = QWidget()
        self.container.setObjectName("CentralWidget")
        self.scroll_area.setWidget(self.container)

        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(10)

        # ----------------- Top Header -----------------
        header_layout = QHBoxLayout()
        header_title_box = QVBoxLayout()
        header_title_box.setSpacing(1)

        lbl_app_title = QLabel("⚡ HandBrake AV1-10bit Auto-Konverter")
        lbl_app_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #58a6ff;")
        lbl_app_subtitle = QLabel("Exakte Übernahme von Quellparametern (Auflösung, FPS, Audio) • SVT-AV1 10-Bit")
        lbl_app_subtitle.setStyleSheet("font-size: 11px; color: #8b949e;")

        header_title_box.addWidget(lbl_app_title)
        header_title_box.addWidget(lbl_app_subtitle)
        header_layout.addLayout(header_title_box)
        header_layout.addStretch()

        self.btn_check_update = QPushButton(f"🔄 v{APP_VERSION}")
        self.btn_check_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_check_update.setToolTip(f"Klicken, um nach Updates im GitHub-Repository ({self.config.get('github_repo', 'itsbonfiretime/handbrake-auto-av1')}) zu suchen")
        self.btn_check_update.setStyleSheet(
            "background-color: #161b22; color: #8b949e; border: 1px solid #30363d; "
            "padding: 5px 10px; border-radius: 6px; font-weight: 600; font-size: 11px;"
        )
        self.btn_check_update.clicked.connect(lambda: self.check_for_updates(manual=True))
        header_layout.addWidget(self.btn_check_update)

        self.target_badge = QLabel("Ziel: AV1 10-bit • CRF 26")
        self.target_badge.setStyleSheet(
            "background-color: #1f6feb22; color: #58a6ff; border: 1px solid #1f6feb88; "
            "padding: 5px 12px; border-radius: 7px; font-weight: 700; font-size: 11px;"
        )
        header_layout.addWidget(self.target_badge)
        main_layout.addLayout(header_layout)

        # ----------------- Action Bar (Select File / Select Folder) -----------------
        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)

        self.btn_select_file = QPushButton("📄 Einzelnes Video wählen...")
        self.btn_select_file.clicked.connect(self.browse_input_file)
        action_bar.addWidget(self.btn_select_file)

        self.btn_select_folder = QPushButton("📁 Ganzen Ordner wählen (Batch-Modus)...")
        self.btn_select_folder.clicked.connect(self.browse_input_folder)
        action_bar.addWidget(self.btn_select_folder)

        action_bar.addStretch()

        self.cb_recursive = QCheckBox("Unterordner einbeziehen")
        self.cb_recursive.setChecked(self.config.get("recursive_folder_scan", False))
        self.cb_recursive.toggled.connect(self.on_setting_changed)
        action_bar.addWidget(self.cb_recursive)

        main_layout.addLayout(action_bar)

        # ----------------- Drop Zones -----------------
        self.drop_zone = DropZoneWidget(
            on_file_dropped_callback=self.on_file_selected,
            on_folder_dropped_callback=self.on_folder_selected,
            on_click_callback=self.browse_input_file
        )
        main_layout.addWidget(self.drop_zone)

        self.compact_drop_zone = CompactDropZoneWidget(
            on_file_dropped_callback=self.on_file_selected,
            on_folder_dropped_callback=self.on_folder_selected,
            on_click_callback=self.browse_input_file
        )
        self.compact_drop_zone.setVisible(False)
        main_layout.addWidget(self.compact_drop_zone)

        # ----------------- Single Video Hero Card -----------------
        self.hero_card = QFrame()
        self.hero_card.setObjectName("HeroCard")
        hero_layout = QVBoxLayout(self.hero_card)
        hero_layout.setContentsMargins(14, 12, 14, 12)
        hero_layout.setSpacing(8)

        title_row = QHBoxLayout()
        title_icon = QLabel("🎬")
        title_icon.setStyleSheet("font-size: 16px;")
        title_row.addWidget(title_icon)

        self.lbl_filename = QLabel("Dateiname: -")
        self.lbl_filename.setStyleSheet("font-size: 14px; font-weight: 700; color: #f0f6fc;")
        self.lbl_filename.setWordWrap(True)
        title_row.addWidget(self.lbl_filename, stretch=1)

        self.lbl_filesize = QLabel("- MB")
        self.lbl_filesize.setStyleSheet(
            "background-color: #1e2634; color: #58a6ff; border: 1px solid #2e3b50; "
            "padding: 3px 8px; border-radius: 5px; font-weight: 700; font-size: 11px;"
        )
        title_row.addWidget(self.lbl_filesize)
        hero_layout.addLayout(title_row)

        # 6 Metric Tiles Grid
        grid = QGridLayout()
        grid.setSpacing(6)

        def make_tile(title_text: str, val_text: str, icon: str):
            f = QFrame()
            f.setProperty("class", "MetricTile")
            f_layout = QVBoxLayout(f)
            f_layout.setContentsMargins(8, 4, 8, 4)
            f_layout.setSpacing(1)

            t = QLabel(f"{icon} {title_text}")
            t.setStyleSheet("font-size: 10px; color: #8b949e; font-weight: 600;")
            v = QLabel(val_text)
            v.setStyleSheet("font-size: 12px; color: #f0f6fc; font-weight: 700;")
            v.setWordWrap(True)

            f_layout.addWidget(t)
            f_layout.addWidget(v)
            return f, v

        self.tile_res, self.lbl_res = make_tile("AUFLÖSUNG", "-", "📐")
        self.tile_fps, self.lbl_fps = make_tile("BILDRATE (FPS)", "-", "⏱️")
        self.tile_dur, self.lbl_dur = make_tile("DAUER", "-", "⌛")
        self.tile_codec, self.lbl_codec = make_tile("QUELL-CODEC", "-", "🎞️")
        self.tile_audio, self.lbl_audio = make_tile("TONSPUREN", "-", "🔊")
        self.tile_target, self.lbl_target = make_tile("ZIEL-ENCODER", "AV1 10-Bit (SVT)", "🚀")

        grid.addWidget(self.tile_res, 0, 0)
        grid.addWidget(self.tile_fps, 0, 1)
        grid.addWidget(self.tile_dur, 0, 2)
        grid.addWidget(self.tile_codec, 1, 0)
        grid.addWidget(self.tile_audio, 1, 1)
        grid.addWidget(self.tile_target, 1, 2)
        hero_layout.addLayout(grid)

        self.param_note = QLabel("✓ Auflösung, Bildrate & Audiospuren werden 1:1 originalgetreu ohne Qualitätsverlust übernommen.")
        self.param_note.setStyleSheet(
            "font-size: 11px; color: #3fb950; font-weight: 600; "
            "background-color: #2386361a; border: 1px solid #23863644; "
            "padding: 4px 10px; border-radius: 5px;"
        )
        hero_layout.addWidget(self.param_note)

        self.hero_card.setVisible(False)
        main_layout.addWidget(self.hero_card)

        # ----------------- Batch Queue Card -----------------
        self.batch_card = QFrame()
        self.batch_card.setObjectName("BatchCard")
        batch_layout = QVBoxLayout(self.batch_card)
        batch_layout.setContentsMargins(14, 12, 14, 12)
        batch_layout.setSpacing(8)

        batch_header = QHBoxLayout()
        lbl_batch_icon = QLabel("📁")
        lbl_batch_icon.setStyleSheet("font-size: 16px;")
        batch_header.addWidget(lbl_batch_icon)

        self.lbl_batch_folder = QLabel("Ordner: -")
        self.lbl_batch_folder.setStyleSheet("font-size: 13px; font-weight: 700; color: #f0f6fc;")
        self.lbl_batch_folder.setWordWrap(True)
        batch_header.addWidget(self.lbl_batch_folder, stretch=1)

        self.lbl_batch_summary = QLabel("0 Videos")
        self.lbl_batch_summary.setStyleSheet(
            "background-color: #1e2634; color: #58a6ff; border: 1px solid #2e3b50; "
            "padding: 3px 10px; border-radius: 5px; font-weight: 700; font-size: 11px;"
        )
        batch_header.addWidget(self.lbl_batch_summary)
        batch_layout.addLayout(batch_header)

        # Overall Batch Progress Bar
        batch_prog_header = QHBoxLayout()
        self.lbl_batch_overall_status = QLabel("Gesamtfortschritt: 0 / 0 abgeschlossen")
        self.lbl_batch_overall_status.setStyleSheet("font-size: 11px; font-weight: 600; color: #c9d1d9;")
        batch_prog_header.addWidget(self.lbl_batch_overall_status)
        self.lbl_batch_overall_pct = QLabel("0%")
        self.lbl_batch_overall_pct.setStyleSheet("font-size: 11px; font-weight: 700; color: #a855f7;")
        batch_prog_header.addWidget(self.lbl_batch_overall_pct, alignment=Qt.AlignmentFlag.AlignRight)
        batch_layout.addLayout(batch_prog_header)

        self.batch_progress_bar = QProgressBar()
        self.batch_progress_bar.setObjectName("BatchProgressBar")
        self.batch_progress_bar.setRange(0, 100)
        self.batch_progress_bar.setValue(0)
        batch_layout.addWidget(self.batch_progress_bar)

        # Queue Table
        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(4)
        self.queue_table.setHorizontalHeaderLabels(["Video-Datei", "Größe", "Status", "Hinweis / Details"])
        self.queue_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.queue_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.queue_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.queue_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.queue_table.setMaximumHeight(120)
        self.queue_table.verticalHeader().setVisible(False)
        batch_layout.addWidget(self.queue_table)

        batch_note = QLabel("✓ Dateien, die bereits als AV1-10bit existieren, werden automatisch übersprungen.")
        batch_note.setStyleSheet(
            "font-size: 11px; color: #3fb950; font-weight: 600; "
            "background-color: #2386361a; border: 1px solid #23863644; "
            "padding: 4px 10px; border-radius: 5px;"
        )
        batch_layout.addWidget(batch_note)

        self.batch_card.setVisible(False)
        main_layout.addWidget(self.batch_card)

        # ----------------- Settings Card (Clean & Compact) -----------------
        settings_card = QFrame()
        settings_card.setObjectName("SettingsCard")
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setContentsMargins(14, 12, 14, 12)
        settings_layout.setSpacing(8)

        # Settings Checkboxes Row
        checks_row = QHBoxLayout()
        self.cb_auto_convert = QCheckBox("⚡ Sofort automatisch konvertieren (One-Drop Mode)")
        self.cb_auto_convert.setChecked(self.config.get("auto_convert_on_drop", True))
        self.cb_auto_convert.setStyleSheet("font-weight: 600; font-size: 12px; color: #f0f6fc;")
        self.cb_auto_convert.toggled.connect(self.on_setting_changed)
        checks_row.addWidget(self.cb_auto_convert)

        checks_row.addSpacing(20)

        self.cb_check_updates = QCheckBox("🔄 Beim Start nach Updates suchen")
        self.cb_check_updates.setChecked(self.config.get("check_updates_on_startup", True))
        self.cb_check_updates.setStyleSheet("font-weight: 500; font-size: 11px; color: #8b949e;")
        self.cb_check_updates.toggled.connect(self.on_setting_changed)
        checks_row.addWidget(self.cb_check_updates)
        checks_row.addStretch()

        settings_layout.addLayout(checks_row)

        # Output Folder Row
        out_box = QVBoxLayout()
        out_box.setSpacing(4)

        out_title_row = QHBoxLayout()
        lbl_out = QLabel("Ausgabeordner:")
        lbl_out.setStyleSheet("font-weight: 600; color: #c9d1d9; font-size: 12px;")
        out_title_row.addWidget(lbl_out)

        self.rb_same_dir = QRadioButton("Im selben Ordner wie Quelldatei speichern")
        self.rb_custom_dir = QRadioButton("Benutzerdefinierter Ordner")

        use_same = self.config.get("use_same_dir_as_source", True)
        self.rb_same_dir.setChecked(use_same)
        self.rb_custom_dir.setChecked(not use_same)

        self.rb_same_dir.toggled.connect(self.on_dir_mode_changed)

        out_title_row.addWidget(self.rb_same_dir)
        out_title_row.addWidget(self.rb_custom_dir)
        out_title_row.addStretch()
        out_box.addLayout(out_title_row)

        out_path_row = QHBoxLayout()
        out_path_row.setSpacing(6)
        self.txt_output_dir = QLineEdit()
        self.txt_output_dir.setPlaceholderText("Ordner auswählen...")
        self.txt_output_dir.setText(self.config.get("output_dir", ""))
        self.txt_output_dir.setEnabled(not use_same)
        out_path_row.addWidget(self.txt_output_dir, stretch=1)

        self.btn_browse_output = QPushButton("📁 Durchsuchen...")
        self.btn_browse_output.setEnabled(not use_same)
        self.btn_browse_output.clicked.connect(self.browse_output_dir)
        out_path_row.addWidget(self.btn_browse_output)
        out_box.addLayout(out_path_row)

        settings_layout.addLayout(out_box)

        # Sliders Row (CRF & Preset side by side with NO background)
        qual_row = QHBoxLayout()
        qual_row.setSpacing(16)

        # RF Slider Box
        rf_box = QVBoxLayout()
        rf_box.setSpacing(2)
        rf_header = QHBoxLayout()
        lbl_rf = QLabel("Qualität (CRF):")
        lbl_rf.setStyleSheet("font-weight: 600; color: #c9d1d9; font-size: 12px;")
        self.lbl_rf_val = QLabel(f"RF {self.config.get('quality_rf', 26)}")
        self.lbl_rf_val.setStyleSheet("color: #58a6ff; font-weight: 700; font-size: 12px;")
        rf_header.addWidget(lbl_rf)
        rf_header.addWidget(self.lbl_rf_val)
        rf_header.addStretch()
        rf_box.addLayout(rf_header)

        self.slider_rf = QSlider(Qt.Orientation.Horizontal)
        self.slider_rf.setMinimum(18)
        self.slider_rf.setMaximum(36)
        self.slider_rf.setValue(self.config.get("quality_rf", 26))
        self.slider_rf.valueChanged.connect(self.on_rf_slider_changed)
        rf_box.addWidget(self.slider_rf)

        self.lbl_rf_desc = QLabel("RF 26: Empfohlen für 10-Bit (Sehr hohe Qualität)")
        self.lbl_rf_desc.setStyleSheet("font-size: 10px; color: #8b949e;")
        rf_box.addWidget(self.lbl_rf_desc)
        qual_row.addLayout(rf_box)

        # Preset Slider Box
        preset_box = QVBoxLayout()
        preset_box.setSpacing(2)
        preset_header = QHBoxLayout()
        lbl_preset = QLabel("Geschwindigkeit (Preset):")
        lbl_preset.setStyleSheet("font-weight: 600; color: #c9d1d9; font-size: 12px;")
        self.lbl_preset_val = QLabel(f"Preset {self.config.get('encoder_preset', '6')}")
        self.lbl_preset_val.setStyleSheet("color: #58a6ff; font-weight: 700; font-size: 12px;")
        preset_header.addWidget(lbl_preset)
        preset_header.addWidget(self.lbl_preset_val)
        preset_header.addStretch()
        preset_box.addLayout(preset_header)

        self.slider_preset = QSlider(Qt.Orientation.Horizontal)
        self.slider_preset.setMinimum(4)
        self.slider_preset.setMaximum(8)
        self.slider_preset.setValue(int(self.config.get("encoder_preset", "6")))
        self.slider_preset.valueChanged.connect(self.on_preset_slider_changed)
        preset_box.addWidget(self.slider_preset)

        self.lbl_preset_desc = QLabel("Preset 6: Ausgewogen (Empfohlen • Schnell & hohe Effizienz)")
        self.lbl_preset_desc.setStyleSheet("font-size: 10px; color: #8b949e;")
        preset_box.addWidget(self.lbl_preset_desc)
        qual_row.addLayout(preset_box)

        settings_layout.addLayout(qual_row)
        main_layout.addWidget(settings_card)

        # ----------------- Progress & Execution Card -----------------
        self.progress_card = QFrame()
        self.progress_card.setObjectName("ProgressCard")
        progress_layout = QVBoxLayout(self.progress_card)
        progress_layout.setContentsMargins(14, 12, 14, 12)
        progress_layout.setSpacing(8)

        status_bar = QHBoxLayout()
        self.lbl_status_icon = QLabel("⏳")
        self.lbl_status_icon.setStyleSheet("font-size: 16px;")
        status_bar.addWidget(self.lbl_status_icon)

        self.lbl_status = QLabel("Warte auf Video oder Ordner...")
        self.lbl_status.setStyleSheet("font-size: 13px; font-weight: 700; color: #f0f6fc;")
        self.lbl_status.setWordWrap(True)
        status_bar.addWidget(self.lbl_status, stretch=1)

        self.lbl_percent_big = QLabel("0%")
        self.lbl_percent_big.setStyleSheet("font-size: 20px; font-weight: 800; color: #58a6ff;")
        status_bar.addWidget(self.lbl_percent_big)
        progress_layout.addLayout(status_bar)

        # Redesigned Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        # Multi-metric Live Bar (FPS, ETA, Pass)
        self.live_stats_bar = QHBoxLayout()
        self.live_stats_bar.setSpacing(10)

        def make_stat_badge(label_text: str):
            lbl = QLabel(label_text)
            lbl.setStyleSheet(
                "background-color: #0b0f17; border: 1px solid #1f2735; border-radius: 5px; "
                "padding: 3px 8px; font-size: 11px; color: #c9d1d9; font-weight: 600;"
            )
            return lbl

        self.badge_fps = make_stat_badge("⚡ Tempo: - fps")
        self.badge_eta = make_stat_badge("⏳ Restzeit: --:--:--")
        self.badge_pass = make_stat_badge("📦 Status: -")

        self.live_stats_bar.addWidget(self.badge_fps)
        self.live_stats_bar.addWidget(self.badge_eta)
        self.live_stats_bar.addWidget(self.badge_pass)
        self.live_stats_bar.addStretch()

        progress_layout.addLayout(self.live_stats_bar)

        # Action Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_convert = QPushButton("▶ In AV1-10Bit konvertieren")
        self.btn_convert.setObjectName("PrimaryButton")
        self.btn_convert.clicked.connect(self.start_conversion)
        self.btn_convert.setEnabled(False)
        btn_row.addWidget(self.btn_convert)

        self.btn_cancel = QPushButton("✖ Abbrechen")
        self.btn_cancel.setObjectName("DangerButton")
        self.btn_cancel.clicked.connect(self.cancel_conversion)
        self.btn_cancel.setVisible(False)
        btn_row.addWidget(self.btn_cancel)

        self.btn_open_folder = QPushButton("📂 Ausgabeordner öffnen")
        self.btn_open_folder.setObjectName("SuccessButton")
        self.btn_open_folder.clicked.connect(self.open_output_folder)
        self.btn_open_folder.setVisible(False)
        btn_row.addWidget(self.btn_open_folder)

        btn_row.addStretch()

        self.cb_show_log = QCheckBox("📋 Log / Details anzeigen")
        self.cb_show_log.toggled.connect(self.toggle_log_console)
        btn_row.addWidget(self.cb_show_log)

        progress_layout.addLayout(btn_row)

        # Collapsible Log Console (100px compact)
        self.log_console = QPlainTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumHeight(110)
        self.log_console.setVisible(False)
        progress_layout.addWidget(self.log_console)

        main_layout.addWidget(self.progress_card)

        # Initialize descriptions
        self.update_slider_descriptions()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(25, self.auto_adjust_size)
        if self.config.get("check_updates_on_startup", True):
            QTimer.singleShot(2500, lambda: self.check_for_updates(manual=False))

    def check_for_updates(self, manual: bool = False):
        if self.update_worker and self.update_worker.isRunning():
            return

        repo = self.config.get("github_repo", "itsbonfiretime/handbrake-auto-av1")
        if manual:
            self.btn_check_update.setText("🔄 Prüfe...")
            self.btn_check_update.setEnabled(False)

        self.update_worker = CheckUpdateWorker(repo=repo, current_version=APP_VERSION)
        self.update_worker.update_available.connect(lambda info: self.on_update_available(info, manual))
        self.update_worker.no_update.connect(lambda ver: self.on_no_update(ver, manual))
        self.update_worker.check_error.connect(lambda err: self.on_update_error(err, manual))
        self.update_worker.start()

    def on_update_available(self, info: ReleaseInfo, manual: bool):
        self.btn_check_update.setEnabled(True)
        self.btn_check_update.setText(f"✨ Update: {info.version}")
        self.btn_check_update.setStyleSheet(
            "background-color: #238636; color: #ffffff; border: 1px solid #2ea043; "
            "padding: 5px 10px; border-radius: 6px; font-weight: 700; font-size: 11px;"
        )
        dlg = UpdateDialog(info, APP_VERSION, self)
        dlg.exec()

    def on_no_update(self, ver: str, manual: bool):
        self.btn_check_update.setEnabled(True)
        self.btn_check_update.setText(f"✓ v{APP_VERSION}")
        self.btn_check_update.setStyleSheet(
            "background-color: #161b22; color: #8b949e; border: 1px solid #30363d; "
            "padding: 5px 10px; border-radius: 6px; font-weight: 600; font-size: 11px;"
        )
        if manual:
            QMessageBox.information(
                self,
                "Auf dem neuesten Stand",
                f"Du nutzt bereits die neueste Version von HandBrake Auto AV1 (v{APP_VERSION})."
            )

    def on_update_error(self, err_msg: str, manual: bool):
        self.btn_check_update.setEnabled(True)
        self.btn_check_update.setText(f"🔄 v{APP_VERSION}")
        self.btn_check_update.setStyleSheet(
            "background-color: #161b22; color: #8b949e; border: 1px solid #30363d; "
            "padding: 5px 10px; border-radius: 6px; font-weight: 600; font-size: 11px;"
        )
        if manual:
            QMessageBox.warning(
                self,
                "Update-Prüfung",
                f"Konnte nicht nach Updates suchen:\n{err_msg}"
            )

    def auto_adjust_size(self):
        """Automatically adjust the window height to fit dynamic content without clipping."""
        if self.isMaximized():
            return

        QApplication.processEvents()
        if hasattr(self, "container") and self.container and self.container.layout():
            self.container.layout().activate()
            hint_h = self.container.layout().sizeHint().height()
        else:
            hint_h = self.sizeHint().height()

        screen = QApplication.primaryScreen()
        max_h = screen.availableGeometry().height() - 60 if screen else 960

        target_h = max(420, min(hint_h + 16, max_h))
        self.resize(self.width(), target_h)

    def trigger_auto_adjust(self):
        """Schedules auto size adjustment after Qt event loop flushes pending layout changes."""
        self.auto_adjust_size()
        QTimer.singleShot(25, self.auto_adjust_size)

    def toggle_log_console(self, checked: bool):
        self.log_console.setVisible(checked)
        self.trigger_auto_adjust()
        if checked:
            QTimer.singleShot(60, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        sb = self.scroll_area.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def on_dir_mode_changed(self):
        use_same = self.rb_same_dir.isChecked()
        self.txt_output_dir.setEnabled(not use_same)
        self.btn_browse_output.setEnabled(not use_same)
        self.on_setting_changed()

    def browse_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Ausgabeordner auswählen", self.txt_output_dir.text())
        if folder:
            self.txt_output_dir.setText(folder)
            self.on_setting_changed()

    def browse_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Video auswählen",
            "",
            "Videodateien (*.mp4 *.mkv *.mov *.avi *.webm *.flv *.ts *.m2ts);;Alle Dateien (*.*)"
        )
        if file_path:
            self.on_file_selected(Path(file_path))

    def browse_input_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Ordner mit Videodateien auswählen", "")
        if folder_path:
            self.on_folder_selected(Path(folder_path))

    def on_rf_slider_changed(self, val: int):
        self.lbl_rf_val.setText(f"RF {val}")
        self.update_slider_descriptions()
        self.update_target_badge()
        self.on_setting_changed()

    def on_preset_slider_changed(self, val: int):
        self.lbl_preset_val.setText(f"Preset {val}")
        self.update_slider_descriptions()
        self.on_setting_changed()

    def update_slider_descriptions(self):
        rf = self.slider_rf.value()
        if rf <= 22:
            self.lbl_rf_desc.setText(f"RF {rf}: Nahezu verlustfrei (Sehr große Dateigröße)")
        elif rf <= 25:
            self.lbl_rf_desc.setText(f"RF {rf}: Exzellente Qualität (Geringfügig komprimiert)")
        elif rf <= 28:
            self.lbl_rf_desc.setText(f"RF {rf}: Empfohlen für 10-Bit (Optimale Balance Qualität & Größe)")
        elif rf <= 32:
            self.lbl_rf_desc.setText(f"RF {rf}: Hohe Kompression (Kleine Dateigröße)")
        else:
            self.lbl_rf_desc.setText(f"RF {rf}: Maximale Kompression (Sehr kleine Datei)")

        p = self.slider_preset.value()
        desc = {
            4: "Preset 4: Sehr langsam (Höchste AV1-Kompressionseffizienz)",
            5: "Preset 5: Langsam (Hohe Effizienz)",
            6: "Preset 6: Ausgewogen (Empfohlen • Schnell & hohe Effizienz)",
            7: "Preset 7: Schnell (Geringerer Rechenaufwand)",
            8: "Preset 8: Sehr schnell (Schnellster Durchlauf)",
        }
        self.lbl_preset_desc.setText(desc.get(p, f"Preset {p}"))

    def update_target_badge(self):
        rf = self.slider_rf.value()
        self.target_badge.setText(f"Ziel: AV1 10-bit • CRF {rf}")

    def on_setting_changed(self):
        self.config["auto_convert_on_drop"] = self.cb_auto_convert.isChecked()
        self.config["use_same_dir_as_source"] = self.rb_same_dir.isChecked()
        self.config["output_dir"] = self.txt_output_dir.text()
        self.config["quality_rf"] = self.slider_rf.value()
        self.config["encoder_preset"] = str(self.slider_preset.value())
        self.config["recursive_folder_scan"] = self.cb_recursive.isChecked()
        self.config["check_updates_on_startup"] = self.cb_check_updates.isChecked()
        save_config(self.config)

    # ----------------- Single File Handling -----------------
    def on_file_selected(self, path: Path):
        self.mode = "single"
        if not self.hb_cli or not self.hb_cli.exists():
            QMessageBox.critical(
                self,
                "HandBrakeCLI fehlt",
                "HandBrakeCLI wurde nicht gefunden. Bitte platziere HandBrakeCLI.exe im 'bin'-Ordner."
            )
            return

        self.drop_zone.setVisible(False)
        self.compact_drop_zone.setVisible(True)
        self.batch_card.setVisible(False)
        self.trigger_auto_adjust()

        self.lbl_status_icon.setText("🔍")
        self.lbl_status.setText(f"Analysiere Video-Metadaten: {path.name}...")
        self.lbl_percent_big.setText("0%")
        self.progress_bar.setValue(0)
        self.btn_convert.setEnabled(False)
        self.btn_open_folder.setVisible(False)
        self.log_console.clear()

        self.scan_worker = VideoScanWorker(path, self.hb_cli)
        self.scan_worker.scan_completed.connect(self.on_scan_completed)
        self.scan_worker.scan_failed.connect(self.on_scan_failed)
        self.scan_worker.start()

    def on_scan_completed(self, meta: VideoMetadata):
        self.current_metadata = meta

        self.lbl_filename.setText(meta.file_name)
        self.lbl_filesize.setText(meta.file_size_formatted)
        self.lbl_res.setText(f"{meta.resolution_str} (DAR {meta.dar_str})")
        self.lbl_fps.setText(f"{meta.fps_str} fps (exakt übernommen)")
        self.lbl_dur.setText(meta.duration_str)
        self.lbl_codec.setText(f"{meta.video_codec.upper()} ({meta.bit_depth}-Bit)")

        audio_str = f"{len(meta.audio_tracks)} Spur(en)"
        if meta.audio_tracks:
            audio_str += f" ({meta.audio_tracks[0]})"
        self.lbl_audio.setText(audio_str)

        self.hero_card.setVisible(True)
        self.trigger_auto_adjust()
        self.btn_convert.setEnabled(True)
        self.btn_convert.setText("▶ In AV1-10Bit konvertieren")

        self.lbl_status_icon.setText("🎬")
        self.lbl_status.setText(f"Bereit: {meta.file_name}")

        if self.cb_auto_convert.isChecked():
            self.lbl_status_icon.setText("⚡")
            self.lbl_status.setText("One-Drop Mode: Starte Konvertierung automatisch...")
            self.start_conversion()

    def on_scan_failed(self, error_msg: str):
        self.lbl_status_icon.setText("⚠️")
        self.lbl_status.setText("Video-Analyse fehlgeschlagen.")
        self.hero_card.setVisible(False)
        self.trigger_auto_adjust()
        QMessageBox.warning(self, "Analysefehler", f"Konnte Video nicht analysieren:\n{error_msg}")

    # ----------------- Folder Batch Handling -----------------
    def on_folder_selected(self, folder_path: Path):
        self.mode = "batch"
        self.current_folder = folder_path

        if not self.hb_cli or not self.hb_cli.exists():
            QMessageBox.critical(
                self,
                "HandBrakeCLI fehlt",
                "HandBrakeCLI wurde nicht gefunden. Bitte platziere HandBrakeCLI.exe im 'bin'-Ordner."
            )
            return

        self.drop_zone.setVisible(False)
        self.compact_drop_zone.setVisible(True)
        self.hero_card.setVisible(False)

        use_same = self.rb_same_dir.isChecked()
        out_dir = None if use_same else Path(self.txt_output_dir.text().strip())
        recursive = self.cb_recursive.isChecked()

        self.batch_queue = scan_folder_for_queue(
            folder_path=folder_path,
            output_dir=out_dir,
            use_same_dir=use_same,
            recursive=recursive,
            skip_existing_av1=True
        )

        total_files = len(self.batch_queue)
        skipped = sum(1 for it in self.batch_queue if it.status == "Übersprungen")
        to_convert = total_files - skipped

        self.lbl_batch_folder.setText(f"Ordner: {folder_path}")
        self.lbl_batch_summary.setText(f"{total_files} Videos ({to_convert} zu konvertieren, {skipped} übersprungen)")
        self.lbl_batch_overall_status.setText(f"Gesamtfortschritt: 0 / {to_convert} abgeschlossen ({skipped} bereits vorhanden)")
        self.lbl_batch_overall_pct.setText("0%")
        self.batch_progress_bar.setValue(0)

        # Populate queue table
        self.queue_table.setRowCount(total_files)
        for row, it in enumerate(self.batch_queue):
            item_name = QTableWidgetItem(f"🎬 {it.file_name}")
            item_size = QTableWidgetItem(it.file_size_formatted)
            item_status = QTableWidgetItem(it.status)
            item_detail = QTableWidgetItem(it.skip_reason if it.skip_reason else "Bereit")

            if it.status == "Übersprungen":
                item_status.setForeground(Qt.GlobalColor.darkYellow)
                item_detail.setForeground(Qt.GlobalColor.gray)
            elif it.status == "Wartend":
                item_status.setForeground(Qt.GlobalColor.cyan)

            self.queue_table.setItem(row, 0, item_name)
            self.queue_table.setItem(row, 1, item_size)
            self.queue_table.setItem(row, 2, item_status)
            self.queue_table.setItem(row, 3, item_detail)

        self.batch_card.setVisible(True)
        self.trigger_auto_adjust()

        if to_convert == 0:
            self.btn_convert.setEnabled(False)
            self.lbl_status_icon.setText("✅")
            self.lbl_status.setText(f"Alle {total_files} Videos in diesem Ordner sind bereits als AV1-10bit konvertiert!")
            return

        self.btn_convert.setEnabled(True)
        self.btn_convert.setText(f"▶ Alle {to_convert} Videos in AV1-10Bit konvertieren")
        self.lbl_status_icon.setText("📁")
        self.lbl_status.setText(f"{to_convert} neue Videos bereit zur Stapelkonvertierung.")

        if self.cb_auto_convert.isChecked():
            self.lbl_status_icon.setText("⚡")
            self.lbl_status.setText(f"One-Drop Mode: Starte Batch-Konvertierung für {to_convert} Videos...")
            self.start_conversion()

    # ----------------- Conversion Start & Management -----------------
    def start_conversion(self):
        if self.mode == "single":
            self.start_single_conversion()
        else:
            self.start_batch_conversion()

    def start_single_conversion(self):
        if not self.current_metadata:
            return

        input_path = self.current_metadata.file_path
        output_path = self.determine_output_path(input_path)
        self.last_output_file = output_path

        self.btn_convert.setVisible(False)
        self.btn_cancel.setVisible(True)
        self.btn_open_folder.setVisible(False)
        self.compact_drop_zone.setEnabled(False)

        self.lbl_status_icon.setText("⚡")
        self.lbl_status.setText(f"Enkodiert AV1-10bit: {output_path.name}")
        self.progress_bar.setValue(0)
        self.lbl_percent_big.setText("0%")
        self.badge_fps.setText("⚡ Tempo: -- fps")
        self.badge_eta.setText("⏳ Restzeit: --:--:--")
        self.badge_pass.setText("📦 Durchgang: Pass 1/1")
        self.log_console.clear()

        self.convert_worker = ConversionWorker(
            hb_cli=self.hb_cli,
            input_path=input_path,
            output_path=output_path,
            metadata=self.current_metadata,
            config=self.config
        )
        self.convert_worker.progress_updated.connect(self.on_conversion_progress)
        self.convert_worker.log_line_received.connect(self.on_log_line)
        self.convert_worker.conversion_finished.connect(self.on_single_conversion_finished)
        self.convert_worker.start()

    def start_batch_conversion(self):
        if not self.batch_queue:
            return

        to_convert = sum(1 for it in self.batch_queue if it.status == "Wartend")
        if to_convert == 0:
            QMessageBox.information(self, "Bereits erledigt", "Alle Videos in diesem Ordner sind bereits als AV1-10bit vorhanden.")
            return

        self.btn_convert.setVisible(False)
        self.btn_cancel.setVisible(True)
        self.btn_open_folder.setVisible(False)
        self.compact_drop_zone.setEnabled(False)

        self.lbl_status_icon.setText("⚡")
        self.lbl_status.setText(f"Starte Stapelverarbeitung ({to_convert} Videos)...")
        self.progress_bar.setValue(0)
        self.lbl_percent_big.setText("0%")
        self.log_console.clear()

        self.batch_worker = BatchConversionWorker(
            hb_cli=self.hb_cli,
            queue=self.batch_queue,
            config=self.config
        )
        self.batch_worker.item_started.connect(self.on_batch_item_started)
        self.batch_worker.item_progress.connect(self.on_batch_item_progress)
        self.batch_worker.item_finished.connect(self.on_batch_item_finished)
        self.batch_worker.batch_progress.connect(self.on_batch_overall_progress)
        self.batch_worker.batch_finished.connect(self.on_batch_finished)
        self.batch_worker.log_line_received.connect(self.on_log_line)
        self.batch_worker.start()

    def cancel_conversion(self):
        reply = QMessageBox.question(
            self,
            "Konvertierung abbrechen?",
            "Möchtest du die laufende Konvertierung wirklich abbrechen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.lbl_status_icon.setText("🛑")
        self.lbl_status.setText("Breche Konvertierung ab...")

        if self.mode == "single" and self.convert_worker and self.convert_worker.isRunning():
            self.convert_worker.cancel()
        elif self.mode == "batch" and self.batch_worker and self.batch_worker.isRunning():
            self.batch_worker.cancel()

    # ----------------- Batch Progress Events -----------------
    def on_batch_item_started(self, idx: int, item: QueueItem):
        self.lbl_status_icon.setText("⚡")
        self.lbl_status.setText(f"[{idx+1}/{len(self.batch_queue)}] Enkodiert: {item.file_name}")
        self.progress_bar.setValue(0)
        self.lbl_percent_big.setText("0%")
        self.last_output_file = item.target_path

        status_item = self.queue_table.item(idx, 2)
        if status_item:
            status_item.setText("Wird konvertiert...")
            status_item.setForeground(Qt.GlobalColor.yellow)

    def on_batch_item_progress(self, idx: int, percent: float, rate_fps: float, eta_sec: int, status_text: str):
        pct_int = int(percent)
        self.progress_bar.setValue(pct_int)
        self.lbl_percent_big.setText(f"{percent:.1f}%")

        if eta_sec > 0:
            m, s = divmod(eta_sec, 60)
            h, m = divmod(m, 60)
            eta_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
        else:
            eta_str = "--:--:--"

        self.badge_eta.setText(f"⏳ Restzeit: {eta_str}")
        self.badge_fps.setText(f"⚡ Tempo: {rate_fps:.1f} fps" if rate_fps > 0 else "⚡ Tempo: aktiv")
        self.badge_pass.setText(f"📦 Status: {status_text}")

        detail_item = self.queue_table.item(idx, 3)
        if detail_item:
            detail_item.setText(f"{percent:.1f}% • {rate_fps:.1f} fps • Rest: {eta_str}")

    def on_batch_item_finished(self, idx: int, item: QueueItem):
        status_item = self.queue_table.item(idx, 2)
        detail_item = self.queue_table.item(idx, 3)

        if status_item:
            status_item.setText(item.status)
            if item.status == "Fertig":
                status_item.setForeground(Qt.GlobalColor.green)
            elif item.status == "Übersprungen":
                status_item.setForeground(Qt.GlobalColor.darkYellow)
            elif item.status == "Fehler":
                status_item.setForeground(Qt.GlobalColor.red)

        if detail_item and item.skip_reason:
            detail_item.setText(item.skip_reason)

    def on_batch_overall_progress(self, completed_count: int, total_count: int, overall_percent: float):
        self.batch_progress_bar.setValue(int(overall_percent))
        self.lbl_batch_overall_pct.setText(f"{overall_percent:.1f}%")
        self.lbl_batch_overall_status.setText(f"Gesamtfortschritt: {completed_count} / {total_count} verarbeitet")

    def on_batch_finished(self, converted_count: int, skipped_count: int, failed_count: int):
        self.btn_convert.setVisible(True)
        self.btn_cancel.setVisible(False)
        self.compact_drop_zone.setEnabled(True)
        self.btn_open_folder.setVisible(True)

        self.lbl_status_icon.setText("🎉")
        msg = f"Stapelverarbeitung abgeschlossen: {converted_count} konvertiert, {skipped_count} übersprungen"
        if failed_count > 0:
            msg += f", {failed_count} Fehler"
        self.lbl_status.setText(msg)
        self.badge_pass.setText("📦 Batch beendet")
        self.badge_eta.setText("⏳ Restzeit: 00:00")
        self.progress_bar.setValue(100)
        self.lbl_percent_big.setText("100%")
        self.trigger_auto_adjust()

    # ----------------- Single Progress Events -----------------
    def on_conversion_progress(self, percent: float, rate_fps: float, eta_sec: int, status_text: str):
        pct_int = int(percent)
        self.progress_bar.setValue(pct_int)
        self.lbl_percent_big.setText(f"{percent:.1f}%")

        if eta_sec > 0:
            m, s = divmod(eta_sec, 60)
            h, m = divmod(m, 60)
            eta_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
        else:
            eta_str = "--:--:--"

        self.badge_eta.setText(f"⏳ Restzeit: {eta_str}")
        self.badge_fps.setText(f"⚡ Tempo: {rate_fps:.1f} fps" if rate_fps > 0 else "⚡ Tempo: aktiv")
        self.badge_pass.setText(f"📦 Status: {status_text}")
        self.lbl_status.setText(f"Enkodiert AV1-10bit: {self.current_metadata.file_name if self.current_metadata else ''}")

    def on_log_line(self, line: str):
        self.log_console.appendPlainText(line)
        sb = self.log_console.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_single_conversion_finished(self, success: bool, message: str, output_path: str):
        self.btn_convert.setVisible(True)
        self.btn_cancel.setVisible(False)
        self.compact_drop_zone.setEnabled(True)

        if success:
            self.progress_bar.setValue(100)
            self.lbl_percent_big.setText("100%")
            self.lbl_status_icon.setText("✅")
            self.lbl_status.setText("Konvertierung erfolgreich abgeschlossen!")
            self.badge_eta.setText("⏳ Restzeit: 00:00")
            self.badge_pass.setText("📦 Status: Fertig")
            self.btn_open_folder.setVisible(True)
        else:
            self.lbl_status_icon.setText("❌")
            self.lbl_status.setText(f"Fehler: {message}")

        self.trigger_auto_adjust()

    def determine_output_path(self, input_path: Path) -> Path:
        stem = input_path.stem
        ext = ".mkv"

        if self.rb_same_dir.isChecked() or not self.txt_output_dir.text().strip():
            target_dir = input_path.parent
        else:
            target_dir = Path(self.txt_output_dir.text().strip())

        output_file = target_dir / f"{stem}_AV1-10bit{ext}"
        counter = 1
        while output_file.exists():
            output_file = target_dir / f"{stem}_AV1-10bit_{counter}{ext}"
            counter += 1

        return output_file

    def open_output_folder(self):
        if self.last_output_file and self.last_output_file.exists():
            subprocess.run(["explorer", f"/select,{str(self.last_output_file)}"])
        elif self.current_folder and self.current_folder.exists():
            subprocess.run(["explorer", str(self.current_folder)])
        elif self.last_output_file and self.last_output_file.parent.exists():
            subprocess.run(["explorer", str(self.last_output_file.parent)])
        elif self.txt_output_dir.text().strip() and Path(self.txt_output_dir.text().strip()).exists():
            subprocess.run(["explorer", self.txt_output_dir.text().strip()])

    def closeEvent(self, event):
        if self.convert_worker and self.convert_worker.isRunning():
            self.convert_worker.cancel()
            self.convert_worker.wait(2000)
        if self.batch_worker and self.batch_worker.isRunning():
            self.batch_worker.cancel()
            self.batch_worker.wait(2000)
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.wait(1000)
        event.accept()
