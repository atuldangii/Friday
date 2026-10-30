"""
FRIDAY AI — Conversation Feed & Message Cards v1.2.0
Matches reference image:
  - Card-style message bubbles with avatars on the left
  - User: Dark card with circular silhouette avatar
  - FRIDAY: Dark card with orange glowing border and FRIDAY diamond emblem avatar
  - Multi-line formatting with green confirmation checkmarks
  - Timestamp in bottom right corner
  - Floating auto-scroll down arrow button
"""

from datetime import datetime
import re

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from config.constants import (
    COLOR_AMBER,
    COLOR_ERROR,
    COLOR_ORANGE,
    COLOR_SUCCESS,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    ICON_PNG,
)


class AvatarWidget(QWidget):
    """Draws a clean vector avatar: user silhouette or glowing FRIDAY diamond."""

    def __init__(self, is_friday: bool = True, parent=None):
        super().__init__(parent)
        self.is_friday = is_friday
        self.setFixedSize(30, 30)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0

        if self.is_friday:
            # Glowing orange FRIDAY diamond
            s = 11.0
            diamond = QPainterPath()
            diamond.moveTo(cx, cy - s)
            diamond.lineTo(cx + s, cy)
            diamond.lineTo(cx, cy + s)
            diamond.lineTo(cx - s, cy)
            diamond.closeSubpath()

            painter.setBrush(QBrush(QColor(0x22, 0x11, 0x02)))
            painter.setPen(QPen(QColor(0xFF, 0x79, 0x00), 1.6))
            painter.drawPath(diamond)

            # Inner chevron glyph
            glyph = QPainterPath()
            gx, gy = s * 0.40, s * 0.45
            glyph.moveTo(cx - gx, cy - gy)
            glyph.lineTo(cx + gx, cy - gy)
            glyph.lineTo(cx + gx * 0.2, cy + gy)
            glyph.lineTo(cx - gx * 0.2, cy + gy)
            glyph.lineTo(cx + gx * 0.35, cy - gy * 0.4)
            glyph.lineTo(cx - gx, cy - gy * 0.4)
            glyph.closeSubpath()
            painter.setBrush(QBrush(QColor(0xFF, 0xAA, 0x33)))
            painter.setPen(Qt.NoPen)
            painter.drawPath(glyph)
        else:
            # User profile silhouette in neutral circular badge
            painter.setBrush(QBrush(QColor(0x2A, 0x2A, 0x30)))
            painter.setPen(QPen(QColor(0x55, 0x55, 0x60), 1.0))
            painter.drawEllipse(QPointF(cx, cy), 13, 13)

            # Head
            painter.setBrush(QBrush(QColor(0xE0, 0xE0, 0xE0)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(cx, cy - 3.5), 4.0, 4.0)

            # Shoulders
            body = QPainterPath()
            body.moveTo(cx - 7.0, cy + 9.0)
            body.quadTo(cx, cy + 1.5, cx + 7.0, cy + 9.0)
            body.closeSubpath()
            painter.drawPath(body)


class MessageBubble(QFrame):
    """Message Card matching the reference image layout and typography."""

    def __init__(self, sender: str, message: str, parent=None):
        super().__init__(parent)
        self.sender    = sender
        self.message   = message
        self.timestamp = datetime.now().strftime("%I:%M %p")
        self._init_ui()

    def _init_ui(self):
        is_user = self.sender.upper() == "USER"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        # Left Avatar
        avatar = AvatarWidget(is_friday=not is_user)
        layout.addWidget(avatar, 0, Qt.AlignTop)

        # Content column
        content_lay = QVBoxLayout()
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(4)

        # Format message lines (supporting green checkmarks for completed actions)
        lines = self.message.strip().split("\n")
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            lbl = QLabel()
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

            # Check if this line is a success confirmation
            is_success_line = (
                line_str.startswith("✔") or
                line_str.startswith("✓") or
                "is open" in line_str.lower() or
                "is running" in line_str.lower() or
                "all done" in line_str.lower() or
                "successfully" in line_str.lower()
            )

            if is_success_line and not is_user:
                clean_text = line_str.lstrip("✔✓ ").strip()
                lbl.setText(f"<span style='color: #22C55E; font-weight: bold;'>✔</span> <span style='color: #22C55E;'>{clean_text}</span>")
                lbl.setStyleSheet("font-size: 13px; line-height: 1.4;")
            else:
                lbl.setText(line_str)
                lbl.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 13px; line-height: 1.4;")

            content_lay.addWidget(lbl)

        # Bottom row with timestamp aligned to the right
        time_row = QHBoxLayout()
        time_row.setContentsMargins(0, 2, 0, 0)
        time_row.addStretch()
        time_lbl = QLabel(self.timestamp)
        time_lbl.setStyleSheet("color: #7A7A85; font-size: 10px;")
        time_row.addWidget(time_lbl)
        content_lay.addLayout(time_row)

        layout.addLayout(content_lay, 1)

        # Container card styling
        if is_user:
            self.setStyleSheet("""
                MessageBubble {
                    background-color: #17171C;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 12px;
                }
            """)
        else:
            self.setStyleSheet("""
                MessageBubble {
                    background-color: #121216;
                    border: 1px solid rgba(255, 121, 0, 0.35);
                    border-radius: 12px;
                }
            """)


class ChatWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Container for scroll area + overlay scroll button
        self.stack = QWidget()
        stack_lay = QVBoxLayout(self.stack)
        stack_lay.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(12, 12, 12, 12)
        self.container_layout.setSpacing(10)
        self.container_layout.addStretch()

        self.scroll_area.setWidget(self.container)
        stack_lay.addWidget(self.scroll_area)

        # Floating scroll-to-bottom chevron button
        self.scroll_btn = QPushButton("⌵", self.stack)
        self.scroll_btn.setFixedSize(28, 28)
        self.scroll_btn.setCursor(Qt.PointingHandCursor)
        self.scroll_btn.setStyleSheet("""
            QPushButton {
                background: #1C1C22;
                color: #FF7900;
                border: 1px solid rgba(255, 121, 0, 0.35);
                border-radius: 14px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #281B0E;
                border: 1px solid #FF7900;
                color: #FFAA33;
            }
        """)
        self.scroll_btn.clicked.connect(self._scroll_bottom)

        lay.addWidget(self.stack)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Position floating button at bottom-right
        self.scroll_btn.move(self.width() - 40, self.height() - 40)

    def add_message(self, sender: str, text: str):
        bubble = MessageBubble(sender, text)
        count = self.container_layout.count()
        self.container_layout.insertWidget(count - 1, bubble)
        QTimer.singleShot(60, self._scroll_bottom)

    def _scroll_bottom(self):
        sb = self.scroll_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def clear(self):
        while self.container_layout.count() > 1:
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                pass
