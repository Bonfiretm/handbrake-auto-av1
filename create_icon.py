import struct
import sys
from pathlib import Path
from PyQt6.QtGui import QGuiApplication, QImage, QPainter, QColor, QFont, QLinearGradient, QBrush, QPen
from PyQt6.QtCore import Qt, QRectF

def generate_icon():
    app = QGuiApplication(sys.argv)

    size = 256
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)

    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Background rounded rect with stylish gradient
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, QColor(30, 58, 138))  # deep blue
    grad.setColorAt(1.0, QColor(2, 132, 199))  # vibrant sky blue
    painter.setBrush(QBrush(grad))
    painter.setPen(QPen(QColor(56, 189, 248), 6))
    painter.drawRoundedRect(QRectF(10, 10, size - 20, size - 20), 44, 44)

    # Inner subtle glow border
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(255, 255, 255, 40), 2))
    painter.drawRoundedRect(QRectF(16, 16, size - 32, size - 32), 38, 38)

    # Lightning bolt / speed indicator
    painter.setPen(QColor(255, 255, 255))
    font_main = QFont("Segoe UI", 60, QFont.Weight.Black)
    painter.setFont(font_main)
    painter.drawText(QRectF(0, 48, size, 85), Qt.AlignmentFlag.AlignCenter, "AV1")

    # 10-BIT Subtitle badge
    painter.setPen(QColor(253, 224, 71))  # amber / yellow highlight
    font_sub = QFont("Segoe UI", 30, QFont.Weight.ExtraBold)
    painter.setFont(font_sub)
    painter.drawText(QRectF(0, 138, size, 45), Qt.AlignmentFlag.AlignCenter, "10-BIT")

    painter.end()

    png_path = Path("app_icon.png")
    ico_path = Path("app_icon.ico")
    img.save(str(png_path))

    # Convert to Windows ICO format (PNG format container)
    with open(png_path, "rb") as f:
        png_data = f.read()

    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png_data), 22)
    with open(ico_path, "wb") as f:
        f.write(header + entry + png_data)

    print("Generated app_icon.png and app_icon.ico")

if __name__ == "__main__":
    generate_icon()
