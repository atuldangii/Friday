"""
FRIDAY AI — Floating Background HUD Overlay v1.2.0
Compact, non-intrusive floating overlay that appears above third-party applications
(Chrome, YouTube, LinkedIn, Notepad, VS Code) upon wake-word detection or global hotkey.
"""

from typing import Callable, Optional
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal, Slot
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
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config.constants import (
    COLOR_AMBER,
    COLOR_BG_CARD,
    COLOR_BG_DARK,
    COLOR_ERROR,
    COLOR_ORANGE,
    COLOR_SUCCESS,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    ICON_PNG,
)


class MiniVisualizer(QWidget):
    """Compact animated arc reactor core for the floating overlay."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(54, 54)
        self._angle = 0.0
        self._pulse = 0.0
        self._pulse_dir = 1
        self._state = "IDLE"

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(20)

    def set_state(self, state: str):
        self._state = state.upper()
        self.update()

    def _tick(self):
        sf = 2.4 if self._state in ("LISTENING", "PROCESSING", "SPEAKING") else 0.8
        self._angle = (self._angle + 1.2 * sf) % 360
        self._pulse += 0.03 * self._pulse_dir * sf
        if self._pulse >= 1.0:
            self._pulse, self._pulse_dir = 1.0, -1
        elif self._pulse <= 0.0:
            self._pulse, self._pulse_dir = 0.0, 1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        center = QPointF(cx, cy)
        r = min(w, h) / 2.0 - 4

        # Primary accent based on state
        if self._state == "STOPPED":
            col = QColor(0xEF, 0x44, 0x44)
        elif self._state == "LISTENING":
            col = QColor(0xFF, 0xAA, 0x33)
        elif self._state in ("PROCESSING", "EXECUTING"):
            col = QColor(0xFF, 0x79, 0x00)
        elif self._state == "SPEAKING":
            col = QColor(0x22, 0xC5, 0x5E)
        else:
            col = QColor(0xFF, 0x79, 0x00)

        # Base circle
        painter.setBrush(QBrush(QColor(0x12, 0x0A, 0x02)))
        painter.setPen(QPen(QColor(col.red(), col.green(), col.blue(), 100), 1.2))
        painter.drawEllipse(center, r, r)

        # Rotating outer arc
        painter.save()
        painter.translate(center)
        painter.rotate(self._angle)
        arc_pen = QPen(col, 2.2)
        arc_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(arc_pen)
        rect = QRectF(-r + 1, -r + 1, (r - 1) * 2, (r - 1) * 2)
        painter.drawArc(rect, 0, 100 * 16)
        painter.drawArc(rect, 180 * 16, 100 * 16)
        painter.restore()

        # Inner diamond logo
        s = 8.0 + self._pulse * 1.5
        diamond = QPainterPath()
        diamond.moveTo(cx, cy - s)
        diamond.lineTo(cx + s * 0.9, cy)
        diamond.lineTo(cx, cy + s)
        diamond.lineTo(cx - s * 0.9, cy)
        diamond.closeSubpath()
        painter.setBrush(QBrush(QColor(0xFF, 0xAA, 0x33)))
        painter.setPen(Qt.NoPen)
        painter.drawPath(diamond)


class FridayOverlayWindow(QWidget):
    """
    Compact, non-intrusive HUD overlay displayed over third-party applications
    when wake-word is triggered or global hotkey is pressed.
    """

    command_submitted = Signal(str)
    emergency_stop_triggered = Signal()
    expand_main_window_requested = Signal()
    mic_mute_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._auto_dismiss_timer = QTimer(self)
        self._auto_dismiss_timer.setSingleShot(True)
        self._auto_dismiss_timer.timeout.connect(self.hide_overlay)

        self._drag_pos = None
        self._is_pinned = False
        self._is_muted = False

        self._init_ui()

    def _init_ui(self):
        self.resize(440, 210)

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(6, 6, 6, 6)

        # Container frame
        self.frame = QFrame()
        self.frame.setObjectName("overlayFrame")
        self.frame.setStyleSheet("""
            QFrame#overlayFrame {
                background-color: #0E0E14;
                border: 1.5px solid #FF7900;
                border-radius: 14px;
            }
        """)
        f_lay = QVBoxLayout(self.frame)
        f_lay.setContentsMargins(14, 10, 14, 10)
        f_lay.setSpacing(8)

        # ── 1. Top Bar: Mini Brand + State Badge + Actions ──────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # Diamond icon
        ico_lbl = QLabel("🔶")
        ico_lbl.setStyleSheet("color: #FF7900; font-size: 13px;")
        title_lbl = QLabel("FRIDAY")
        title_lbl.setStyleSheet("color: #FF7900; font-size: 13px; font-weight: 800; letter-spacing: 1.5px;")

        self.state_badge = QLabel("READY")
        self.state_badge.setStyleSheet("""
            QLabel {
                background: rgba(255, 121, 0, 0.14);
                border: 1px solid #FF7900;
                border-radius: 6px;
                color: #FFAA33;
                font-size: 9.5px;
                font-weight: bold;
                padding: 1px 8px;
            }
        """)

        top_row.addWidget(ico_lbl)
        top_row.addWidget(title_lbl)
        top_row.addWidget(self.state_badge)
        top_row.addStretch()

        # Mic Mute / Unmute button
        self.mic_mute_btn = QPushButton("🎙")
        self.mic_mute_btn.setFixedSize(24, 24)
        self.mic_mute_btn.setToolTip("Mute / Unmute Microphone (Ctrl+Alt+M)")
        self.mic_mute_btn.setCursor(Qt.PointingHandCursor)
        self.mic_mute_btn.setStyleSheet(self._btn_style())
        self.mic_mute_btn.clicked.connect(self._toggle_mic_mute)
        top_row.addWidget(self.mic_mute_btn)

        # Pin button
        self.pin_btn = QPushButton("📌")
        self.pin_btn.setFixedSize(24, 24)
        self.pin_btn.setToolTip("Pin overlay (prevent auto-dismiss)")
        self.pin_btn.setCursor(Qt.PointingHandCursor)
        self.pin_btn.setStyleSheet(self._btn_style())
        self.pin_btn.clicked.connect(self._toggle_pin)
        top_row.addWidget(self.pin_btn)

        # Expand to full main window button
        expand_btn = QPushButton("⤢")
        expand_btn.setFixedSize(24, 24)
        expand_btn.setToolTip("Open full FRIDAY HUD")
        expand_btn.setCursor(Qt.PointingHandCursor)
        expand_btn.setStyleSheet(self._btn_style())
        expand_btn.clicked.connect(self._request_expand)
        top_row.addWidget(expand_btn)

        # Dismiss / Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setToolTip("Dismiss overlay")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 5px;
                color: #A6A6B0;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #EF4444;
                color: #FFFFFF;
                border: 1px solid #EF4444;
            }
        """)
        close_btn.clicked.connect(self.hide_overlay)
        top_row.addWidget(close_btn)

        f_lay.addLayout(top_row)

        # ── 2. Middle Row: Mini Visualizer + Live Transcription & Result ────
        mid_row = QHBoxLayout()
        mid_row.setSpacing(12)

        self.viz = MiniVisualizer()
        mid_row.addWidget(self.viz, 0, Qt.AlignVCenter)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)

        self.user_query_lbl = QLabel('Listening for your command...')
        self.user_query_lbl.setWordWrap(True)
        self.user_query_lbl.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 600;")
        info_col.addWidget(self.user_query_lbl)

        self.response_lbl = QLabel("")
        self.response_lbl.setWordWrap(True)
        self.response_lbl.setStyleSheet("color: #22C55E; font-size: 11.5px;")
        info_col.addWidget(self.response_lbl)

        mid_row.addLayout(info_col, 1)
        f_lay.addLayout(mid_row, 1)

        # ── 3. Bottom Row: Compact Command Input + Send & Stop Buttons ──────
        deck = QHBoxLayout()
        deck.setSpacing(6)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText('Type command (or speak naturally)...')
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: #15151C;
                border: 1px solid rgba(255, 121, 0, 0.35);
                border-radius: 7px;
                color: #FFFFFF;
                font-size: 12px;
                padding: 4px 8px;
            }
            QLineEdit::placeholder {
                color: #72727E;
                font-style: italic;
            }
        """)
        self.input_field.returnPressed.connect(self._send_typed)
        deck.addWidget(self.input_field, 1)

        send_btn = QPushButton("➤")
        send_btn.setFixedSize(30, 30)
        send_btn.setCursor(Qt.PointingHandCursor)
        send_btn.setToolTip("Send command")
        send_btn.setStyleSheet("""
            QPushButton {
                background: #FF7900;
                border: none;
                border-radius: 6px;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #FFAA33;
            }
        """)
        send_btn.clicked.connect(self._send_typed)
        deck.addWidget(send_btn)

        stop_btn = QPushButton("⏹")
        stop_btn.setFixedSize(30, 30)
        stop_btn.setCursor(Qt.PointingHandCursor)
        stop_btn.setToolTip("Emergency Stop")
        stop_btn.setStyleSheet("""
            QPushButton {
                background: #1C1C24;
                border: 1px solid rgba(239, 68, 68, 0.4);
                border-radius: 6px;
                color: #EF4444;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #EF4444;
                color: #FFFFFF;
            }
        """)
        stop_btn.clicked.connect(self._trigger_stop)
        deck.addWidget(stop_btn)

        f_lay.addLayout(deck)
        main_lay.addWidget(self.frame)

    def _btn_style(self) -> str:
        return """
            QPushButton {
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 5px;
                color: #C2C2CC;
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(255, 121, 0, 0.18);
                border: 1px solid #FF7900;
                color: #FFAA33;
            }
        """

    def _toggle_pin(self):
        self._is_pinned = not self._is_pinned
        if self._is_pinned:
            self.pin_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 121, 0, 0.22);
                    border: 1.5px solid #FF7900;
                    border-radius: 5px;
                    color: #FFAA33;
                    font-size: 11px;
                }
            """)
            self._auto_dismiss_timer.stop()
        else:
            self.pin_btn.setStyleSheet(self._btn_style())

    def _toggle_mic_mute(self):
        self.set_mic_muted(not self._is_muted)
        self.mic_mute_toggled.emit(self._is_muted)

    def set_mic_muted(self, is_muted: bool):
        self._is_muted = is_muted
        if self._is_muted:
            self.mic_mute_btn.setText("🔇")
            self.mic_mute_btn.setToolTip("Unmute Microphone (Listening Paused)")
            self.mic_mute_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(239, 68, 68, 0.25);
                    border: 1px solid #EF4444;
                    border-radius: 5px;
                    color: #EF4444;
                    font-size: 11px;
                }
            """)
        else:
            self.mic_mute_btn.setText("🎙")
            self.mic_mute_btn.setToolTip("Mute Microphone (Ctrl+Alt+M)")
            self.mic_mute_btn.setStyleSheet(self._btn_style())

    def _request_expand(self):
        self.hide_overlay()
        self.expand_main_window_requested.emit()

    def _send_typed(self):
        text = self.input_field.text().strip()
        if text:
            self.input_field.clear()
            self.user_query_lbl.setText(f'"{text}"')
            self.response_lbl.setText("Executing...")
            self.set_state("EXECUTING")
            self.command_submitted.emit(text)

    def _trigger_stop(self):
        self.set_state("STOPPED")
        self.emergency_stop_triggered.emit()

    # ── Display & State Methods ───────────────────────────────────────────────

    def show_overlay(self, user_text: Optional[str] = None, initial_state: str = "LISTENING"):
        """Displays the floating overlay in the top-right corner of the active screen."""
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            # Position at top right with comfortable padding
            x = avail.x() + avail.width() - self.width() - 24
            y = avail.y() + 32
            self.move(x, y)

        if user_text:
            self.user_query_lbl.setText(f'"{user_text}"')
        else:
            self.user_query_lbl.setText("Hello Sir, what can I do for you?")

        self.response_lbl.setText("")
        self.set_state(initial_state)

        self.show()
        self.raise_()

        # If voice is running, don't auto-dismiss until response is delivered
        self._auto_dismiss_timer.stop()

    def hide_overlay(self):
        """Hides the overlay without interrupting background listening."""
        self._auto_dismiss_timer.stop()
        self.hide()

    def set_state(self, state: str):
        st_clean = state.upper()
        self.viz.set_state(st_clean)
        self.state_badge.setText(st_clean)

        if st_clean == "LISTENING":
            self.state_badge.setStyleSheet("background: rgba(255, 170, 51, 0.18); border: 1px solid #FFAA33; color: #FFAA33; border-radius: 6px; padding: 1px 8px; font-size: 9.5px; font-weight: bold;")
        elif st_clean in ("PROCESSING", "EXECUTING"):
            self.state_badge.setStyleSheet("background: rgba(255, 121, 0, 0.18); border: 1px solid #FF7900; color: #FF7900; border-radius: 6px; padding: 1px 8px; font-size: 9.5px; font-weight: bold;")
        elif st_clean == "SPEAKING":
            self.state_badge.setStyleSheet("background: rgba(34, 197, 94, 0.18); border: 1px solid #22C55E; color: #22C55E; border-radius: 6px; padding: 1px 8px; font-size: 9.5px; font-weight: bold;")
        elif st_clean == "STOPPED":
            self.state_badge.setStyleSheet("background: rgba(239, 68, 68, 0.18); border: 1px solid #EF4444; color: #EF4444; border-radius: 6px; padding: 1px 8px; font-size: 9.5px; font-weight: bold;")
        else:
            self.state_badge.setStyleSheet("background: rgba(255, 121, 0, 0.14); border: 1px solid #FF7900; color: #FFAA33; border-radius: 6px; padding: 1px 8px; font-size: 9.5px; font-weight: bold;")

    def update_interaction(self, user_text: str, response_text: str):
        """Updates query and response labels with action confirmation."""
        self.user_query_lbl.setText(f'"{user_text}"')

        # Format confirmation with green checkmark
        clean_resp = response_text.strip()
        if "is open" in clean_resp.lower() or "searching" in clean_resp.lower() or "done" in clean_resp.lower():
            self.response_lbl.setText(f"✔ {clean_resp}")
            self.response_lbl.setStyleSheet("color: #22C55E; font-size: 11.5px; font-weight: 500;")
        else:
            self.response_lbl.setText(clean_resp)
            self.response_lbl.setStyleSheet("color: #F5F5F5; font-size: 11.5px;")

        # Auto-dismiss after 7 seconds if not pinned
        if not self._is_pinned:
            self._auto_dismiss_timer.start(7000)

    # Mouse drag for moving the overlay
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide_overlay()
            event.accept()
        else:
            super().keyPressEvent(event)
