"""Modern Dark Theme Stylesheet for HandBrake Auto AV1-10bit Converter."""

import sys
from pathlib import Path


def get_asset_url(filename: str) -> str:
    """Returns a forward-slash normalized absolute path or relative path to asset."""
    if hasattr(sys, "_MEIPASS"):
        p = Path(sys._MEIPASS) / "assets" / filename
        if p.exists():
            return str(p).replace("\\", "/")
    
    local = Path(__file__).resolve().parent.parent / "assets" / filename
    if local.exists():
        return str(local).replace("\\", "/")
    
    return f"assets/{filename}"


def get_dark_theme() -> str:
    check_url = get_asset_url("check.png")
    radio_url = get_asset_url("radio_dot.png")

    return f"""
/* Root Window Background */
QWidget#CentralWidget, MainWindow {{
    background-color: #0b0f17;
}}

/* Global text and font defaults */
QWidget {{
    color: #e2e8f0;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}}

/* Universal reset: Labels, Sliders, Checkboxes and RadioButtons have NO background */
QLabel {{
    background: transparent;
    color: #e2e8f0;
}}

QCheckBox {{
    background: transparent;
    spacing: 8px;
    color: #e2e8f0;
    font-weight: 500;
}}

QRadioButton {{
    background: transparent;
    spacing: 8px;
    color: #e2e8f0;
}}

QSlider {{
    background: transparent;
}}

/* ScrollBars */
QScrollBar:vertical {{
    border: none;
    background: #0d121c;
    width: 7px;
    margin: 0px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: #273142;
    min-height: 20px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{
    background: #3b475a;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    border: none;
    background: #0d121c;
    height: 7px;
    margin: 0px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: #273142;
    min-width: 20px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #3b475a;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Base Container Cards */
QFrame.Card, QFrame#HeroCard, QFrame#SettingsCard, QFrame#ProgressCard, QFrame#BatchCard {{
    background-color: #141a24;
    border: 1px solid #232c3d;
    border-radius: 10px;
}}

/* Drop Zone (Idle State) */
QFrame#DropZone {{
    background-color: #101620;
    border: 2px dashed #283346;
    border-radius: 12px;
}}
QFrame#DropZone[dragHover="true"] {{
    background-color: #13243c;
    border: 2px dashed #38bdf8;
}}
QFrame#DropZone:hover {{
    border-color: #38bdf8;
    background-color: #121926;
}}

/* Compact Drop Zone (Active State) */
QFrame#CompactDropZone {{
    background-color: #101620;
    border: 1px dashed #283346;
    border-radius: 8px;
    padding: 4px;
}}
QFrame#CompactDropZone[dragHover="true"] {{
    background-color: #13243c;
    border-color: #38bdf8;
}}
QFrame#CompactDropZone:hover {{
    border-color: #58a6ff;
}}

/* Metric Tile Frame */
QFrame.MetricTile {{
    background-color: #0b0f17;
    border: 1px solid #1f2735;
    border-radius: 8px;
    padding: 6px 10px;
}}
QFrame.MetricTile:hover {{
    border-color: #38bdf8;
}}

/* Standard PushButtons */
QPushButton {{
    background-color: #1e2634;
    color: #f1f5f9;
    border: 1px solid #2e3b50;
    border-radius: 7px;
    padding: 7px 14px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: #2b364a;
    border-color: #58a6ff;
}}
QPushButton:pressed {{
    background-color: #171f2c;
}}
QPushButton:disabled {{
    background-color: #121721;
    color: #4b5563;
    border-color: #1e2634;
}}

/* Primary Action Button (Start) */
QPushButton#PrimaryButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:0.5 #2563eb, stop:1 #0284c7);
    color: #ffffff;
    border: 1px solid #38bdf8;
    border-radius: 8px;
    padding: 9px 20px;
    font-size: 13px;
    font-weight: 700;
}}
QPushButton#PrimaryButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #0369a1);
    border-color: #7dd3fc;
}}
QPushButton#PrimaryButton:pressed {{
    background: #1e40af;
}}
QPushButton#PrimaryButton:disabled {{
    background: #151b26;
    color: #475569;
    border: 1px solid #1e2634;
}}

/* Danger Button (Cancel) */
QPushButton#DangerButton {{
    background-color: #7f1d1d;
    color: #fecaca;
    border: 1px solid #b91c1c;
    border-radius: 7px;
    padding: 7px 16px;
    font-weight: 600;
}}
QPushButton#DangerButton:hover {{
    background-color: #991b1b;
    border-color: #ef4444;
}}
QPushButton#DangerButton:pressed {{
    background-color: #450a0a;
}}

/* Success Button (Open Folder) */
QPushButton#SuccessButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #047857, stop:1 #059669);
    color: #ffffff;
    border: 1px solid #34d399;
    border-radius: 7px;
    padding: 8px 16px;
    font-weight: 700;
}}
QPushButton#SuccessButton:hover {{
    background: #059669;
    border-color: #6ee7b7;
}}

/* Line Edit Input */
QLineEdit {{
    background-color: #0d121c;
    border: 1px solid #263143;
    border-radius: 7px;
    padding: 6px 10px;
    color: #f1f5f9;
    selection-background-color: #2563eb;
}}
QLineEdit:focus {{
    border: 1px solid #38bdf8;
}}
QLineEdit:disabled {{
    background-color: #090d14;
    color: #4b5563;
    border-color: #1a222e;
}}

/* ----------------- REDESIGNED CHECKBOX ----------------- */
QCheckBox::indicator {{
    width: 17px;
    height: 17px;
    border-radius: 4px;
    border: 1.5px solid #334155;
    background-color: #0d121c;
}}
QCheckBox::indicator:hover {{
    border-color: #38bdf8;
    background-color: #131d2e;
}}
QCheckBox::indicator:checked {{
    background-color: #2563eb;
    border-color: #38bdf8;
    image: url({check_url});
}}

/* ----------------- REDESIGNED RADIO BUTTON ----------------- */
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 1.5px solid #334155;
    background-color: #0d121c;
}}
QRadioButton::indicator:hover {{
    border-color: #38bdf8;
}}
QRadioButton::indicator:checked {{
    border-color: #38bdf8;
    background-color: #0d121c;
    image: url({radio_url});
}}

/* ----------------- REDESIGNED SLIDERS (NO BACKGROUND) ----------------- */
QSlider {{
    height: 22px;
}}
QSlider::groove:horizontal {{
    height: 5px;
    background: #1e2634;
    border-radius: 2.5px;
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #38bdf8);
    border-radius: 2.5px;
}}
QSlider::add-page:horizontal {{
    background: #1e2634;
    border-radius: 2.5px;
}}
QSlider::handle:horizontal {{
    background: #ffffff;
    border: 2px solid #38bdf8;
    width: 15px;
    height: 15px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{
    background: #38bdf8;
    border: 2px solid #ffffff;
}}

/* ----------------- REDESIGNED PROGRESSBARS ----------------- */
/* Main Current Video Progress Bar */
QProgressBar {{
    background-color: #0d121c;
    border: 1px solid #232c3d;
    border-radius: 10px;
    text-align: center;
    color: transparent;
    height: 20px;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:0.4 #0284c7, stop:0.8 #06b6d4, stop:1 #10b981);
    border-radius: 9px;
}}

/* Batch Overall Progress Bar */
QProgressBar#BatchProgressBar {{
    background-color: #0d121c;
    border: 1px solid #1f2735;
    border-radius: 4px;
    height: 8px;
}}
QProgressBar#BatchProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8b5cf6, stop:1 #ec4899);
    border-radius: 3px;
}}

/* Queue Table */
QTableWidget {{
    background-color: #0d121c;
    border: 1px solid #1f2735;
    border-radius: 7px;
    gridline-color: #141a24;
    color: #e2e8f0;
    selection-background-color: #1f6feb22;
    selection-color: #f1f5f9;
}}
QHeaderView::section {{
    background-color: #141a24;
    color: #8b949e;
    font-weight: 700;
    font-size: 11px;
    padding: 5px;
    border: none;
    border-bottom: 1px solid #232c3d;
}}

/* PlainTextEdit (Log Console) */
QPlainTextEdit {{
    background-color: #090d14;
    border: 1px solid #1f2735;
    border-radius: 7px;
    color: #94a3b8;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 11px;
    padding: 6px;
}}

/* Tooltips */
QToolTip {{
    background-color: #141a24;
    color: #f1f5f9;
    border: 1px solid #232c3d;
    border-radius: 6px;
    padding: 4px 8px;
}}
"""

DARK_THEME = get_dark_theme()
