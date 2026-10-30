"""
FRIDAY AI — Main HUD Window v1.2.0
Matches reference image & Windows 11 desktop integration:
  - Outer rounded frame with glowing orange border
  - Top header:
      Logo + Title
      Center nav tabs (Home, Commands, Apps, Browser, Files, System, Settings)
      Crisp custom vector window controls: Pin (Always on Top), Minimize, Maximize, Close
  - Left sidebar: STATUS card (mic badge + Active/On/Background/Ready) + QUICK COMMANDS card
  - Center panel: Arc Reactor Core Visualizer (responsive) + 4 control buttons (Start Listening, Pause, Stop, Cancel Task)
  - Right panel: CONVERSATION card with avatar message feed and Clear button
  - Bottom input bar: Guaranteed visible, prominent command input deck (keyboard icon, input field, orange send button, mic button)
  - Bottom status bar: Logo + version + Online status + Global Hotkey hint (Ctrl+Alt+F) + clock
  - Cross-App & Background Invocation:
      1. Background wake-word detection auto-activated
      2. Windows Global Hotkey (Ctrl+Alt+F / Ctrl+Shift+F) to summon FRIDAY from any site or page
      3. Always-on-Top pin mode toggle
"""

from datetime import datetime
from pathlib import Path
import time
from typing import Callable, Optional

from PySide6.QtCore import QObject, QPoint, QPointF, QRectF, QSize, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QIcon,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPushButton,
    QSizePolicy,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from config.constants import (
    APP_NAME,
    APP_SUBTITLE,
    APP_VERSION,
    ASSETS_DIR,
    COLOR_AMBER,
    COLOR_BG_CARD,
    COLOR_BG_DARK,
    COLOR_BG_SECONDARY,
    COLOR_ERROR,
    COLOR_ORANGE,
    COLOR_SUCCESS,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    ICON_PNG,
)
from core.assistant import FridayCore
from core.hotkey import GlobalHotkeyListener
from core.permissions import ActionRequest
from ui.chat_widget import ChatWidget
from ui.core_visualizer import CoreVisualizerWidget
from ui.overlay_window import FridayOverlayWindow
from ui.permission_dialog import PermissionDialog
from ui.settings_dialog import SettingsDialog
from ui.styles import FUTURISTIC_STYLESHEET


# ──────────────────────────────────────────────────────────────────────────────
#  Vector Window Control Button (Min, Max, Close, Pin)
# ──────────────────────────────────────────────────────────────────────────────

class WindowControlBtn(QPushButton):
    """Clean vector-painted window controls guaranteed to be visible on any screen."""

    def __init__(self, kind: str, parent=None):
        super().__init__(parent)
        self.kind = kind  # 'pin', 'min', 'max', 'close'
        self.setFixedSize(30, 30)
        self.setCursor(Qt.PointingHandCursor)
        self.is_pinned = False
        self.is_maximized = False

        if kind == "pin":
            self.setToolTip("Always on Top (Pin above other windows)")
        elif kind == "min":
            self.setToolTip("Minimize (Press Ctrl+Alt+F to restore anytime)")
        elif kind == "max":
            self.setToolTip("Maximize / Restore Window")
        elif kind == "close":
            self.setToolTip("Close FRIDAY")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        is_hover = self.underMouse()

        # Button background
        if is_hover:
            if self.kind == "close":
                bg = QColor(0xEF, 0x44, 0x44)
                sym_col = QColor(0xFF, 0xFF, 0xFF)
            else:
                bg = QColor(0x28, 0x16, 0x06)
                sym_col = QColor(0xFF, 0xAA, 0x33)
        else:
            if self.kind == "pin" and self.is_pinned:
                bg = QColor(0x24, 0x14, 0x04)
                sym_col = QColor(0xFF, 0x79, 0x00)
            else:
                bg = QColor(0x15, 0x15, 0x1B)
                sym_col = QColor(0xD2, 0xD2, 0xDC)

        painter.setBrush(QBrush(bg))
        if is_hover and self.kind != "close":
            painter.setPen(QPen(QColor(0xFF, 0x79, 0x00), 1.2))
        else:
            painter.setPen(QPen(QColor(0x32, 0x32, 0x3E), 1.0))
        painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 6, 6)

        # Vector Icon Glyphs
        pen = QPen(sym_col, 2.0)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        if self.kind == "min":
            # Horizontal line
            painter.drawLine(QPointF(cx - 5.5, cy + 2.5), QPointF(cx + 5.5, cy + 2.5))
        elif self.kind == "max":
            # Square box
            painter.setBrush(Qt.NoBrush)
            pen_box = QPen(sym_col, 1.8)
            painter.setPen(pen_box)
            painter.drawRect(QRectF(cx - 5.0, cy - 5.0, 10.0, 10.0))
        elif self.kind == "close":
            # Diagonal X
            painter.drawLine(QPointF(cx - 4.5, cy - 4.5), QPointF(cx + 4.5, cy + 4.5))
            painter.drawLine(QPointF(cx + 4.5, cy - 4.5), QPointF(cx - 4.5, cy + 4.5))
        elif self.kind == "pin":
            # Pin icon
            painter.drawLine(QPointF(cx - 4.0, cy - 5.0), QPointF(cx + 4.0, cy - 5.0))
            painter.drawLine(QPointF(cx, cy - 5.0), QPointF(cx, cy + 1.0))
            painter.drawLine(QPointF(cx - 4.0, cy + 1.0), QPointF(cx + 4.0, cy + 1.0))
            painter.drawLine(QPointF(cx, cy + 1.0), QPointF(cx, cy + 6.0))


# ──────────────────────────────────────────────────────────────────────────────
#  Worker thread
# ──────────────────────────────────────────────────────────────────────────────

class AssistantWorker(QObject):
    finished        = Signal()
    chat_message    = Signal(str, str)
    state_change    = Signal(str)
    task_progress   = Signal(int, int, str)
    request_confirmation = Signal(object)

    def __init__(self, core: FridayCore):
        super().__init__()
        self.core = core

    @Slot(str)
    def handle_command(self, text: str):
        self.core.process_command(text)
        self.finished.emit()

    @Slot()
    def handle_voice_listen(self):
        self.state_change.emit("LISTENING")
        success, text = self.core.recognizer.listen_and_recognize(timeout=5.0, phrase_time_limit=8.0)
        if success and text:
            self.core.process_command(text, is_voice=True)
        else:
            self.state_change.emit("IDLE")
        self.finished.emit()


# ──────────────────────────────────────────────────────────────────────────────
#  Main Window
# ──────────────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    confirm_action_signal = Signal(object)

    def __init__(self, core: FridayCore):
        super().__init__()
        self.core = core

        # Worker thread
        self.worker_thread = QThread()
        self.worker        = AssistantWorker(self.core)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.start()

        # Floating HUD Overlay for background/cross-app interaction
        self.overlay = FridayOverlayWindow()
        self.overlay.command_submitted.connect(self.worker.handle_command)
        self.overlay.emergency_stop_triggered.connect(self._trigger_emergency_stop)
        self.overlay.expand_main_window_requested.connect(self.bring_to_front)
        self.overlay.mic_mute_toggled.connect(self._on_overlay_mic_mute_toggled)

        # Wire core callbacks
        self.core.on_chat_message   = lambda s, m: self.worker.chat_message.emit(s, m)
        self.core.on_state_change   = lambda st:   self.worker.state_change.emit(st)
        self.core.on_task_progress  = lambda c, t, d: self.worker.task_progress.emit(c, t, d)
        self.core.security.set_confirmation_handler(self._ask_user_permission)
        self.core.on_bring_to_front = lambda: QTimer.singleShot(0, self.bring_to_front)
        self.core.on_wake_detected  = lambda *args: QTimer.singleShot(0, lambda: self._on_wake_detected_ui(*args))

        self._force_quit = False
        self._drag_pos = None

        self._init_ui()
        self._init_tray()
        self._init_shortcuts()
        self._init_global_hotkey()

        # Connect signals
        self.worker.chat_message.connect(self._on_chat_message)
        self.worker.state_change.connect(self._on_state_change)
        self.worker.task_progress.connect(self._on_task_progress)
        self.confirm_action_signal.connect(self._show_permission_dialog)

        # Initial conversation welcome
        user_name = self.core.settings.get("user_name", "Sir")
        self.chat_widget.add_message(
            "FRIDAY",
            f"Good day, {user_name}. FRIDAY MARK VII online and ready.\n"
            "What can I assist you with today?",
        )

        # Automatically start background wake-word listening so commands work from any app/site
        self.core.start_background_services()

    # ──────────────────────────────────────────────────────────────────────────
    #  UI Construction
    # ──────────────────────────────────────────────────────────────────────────

    def _init_ui(self):
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")

        # Responsive window sizing adapted to the user's screen resolution
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            target_w = min(1140, int(avail.width() * 0.90))
            target_h = min(660, int(avail.height() * 0.88))
            self.resize(target_w, target_h)
            self.move(
                avail.x() + (avail.width() - target_w) // 2,
                avail.y() + (avail.height() - target_h) // 2,
            )
        else:
            self.resize(1080, 620)

        self.setMinimumSize(880, 500)
        self.setStyleSheet(FUTURISTIC_STYLESHEET)

        # Frameless window with custom sci-fi border & title bar
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        if ICON_PNG.exists():
            self.setWindowIcon(QIcon(str(ICON_PNG)))

        # Outer background wrapper with glowing rounded border
        central = QWidget()
        self.setCentralWidget(central)
        central_lay = QVBoxLayout(central)
        central_lay.setContentsMargins(6, 6, 6, 6)

        self.outer_frame = QFrame()
        self.outer_frame.setObjectName("outerFrame")
        self.outer_frame.setStyleSheet("""
            QFrame#outerFrame {
                background-color: #0A0A0C;
                border: 1.5px solid #FF7900;
                border-radius: 16px;
            }
        """)

        frame_lay = QVBoxLayout(self.outer_frame)
        frame_lay.setContentsMargins(14, 10, 14, 10)
        frame_lay.setSpacing(8)

        # 1. Top Header Bar (Logo, Nav Tabs, Vector Window Controls)
        frame_lay.addWidget(self._build_top_header(), 0)

        # 2. Body Area (Sidebar | Center Reactor | Conversation Panel)
        body = QHBoxLayout()
        body.setContentsMargins(0, 2, 0, 2)
        body.setSpacing(12)

        body.addWidget(self._build_sidebar(), 0)
        body.addWidget(self._build_centre(), 1)
        body.addWidget(self._build_chat_panel(), 0)

        frame_lay.addLayout(body, 1)

        # 3. Bottom Command Input Deck (ALWAYS VISIBLE & PROMINENT)
        frame_lay.addWidget(self._build_command_deck(), 0)

        # 4. Bottom Status Bar
        frame_lay.addWidget(self._build_status_bar(), 0)

        central_lay.addWidget(self.outer_frame)

    # ── 1. Top Header Bar ─────────────────────────────────────────────────────

    def _build_top_header(self) -> QWidget:
        header = QFrame()
        header.setFixedHeight(50)
        header.setStyleSheet("background: transparent;")
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(2, 0, 2, 0)
        hlay.setSpacing(12)

        # Brand Logo (Diamond Emblem + Title)
        brand = QHBoxLayout()
        brand.setSpacing(10)

        logo_lbl = QLabel()
        if ICON_PNG.exists():
            pix = QPixmap(str(ICON_PNG)).scaled(34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_lbl.setPixmap(pix)
        else:
            logo_lbl.setText("🔶")
            logo_lbl.setStyleSheet("font-size: 22px; color: #FF7900;")
        brand.addWidget(logo_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        t1 = QLabel(APP_NAME)
        t1.setStyleSheet("color: #FF7900; font-size: 16px; font-weight: 800; letter-spacing: 2px;")
        t2 = QLabel(APP_SUBTITLE)
        t2.setStyleSheet("color: #8C8C96; font-size: 8.5px; font-weight: 600; letter-spacing: 1.5px;")
        title_box.addWidget(t1)
        title_box.addWidget(t2)
        brand.addLayout(title_box)

        hlay.addLayout(brand)
        hlay.addStretch(1)

        # Navigation Bar Tabs (Home, Commands, Apps, Browser, Files, System, Settings)
        nav_box = QHBoxLayout()
        nav_box.setSpacing(4)

        tabs = [
            ("🏠", "Home"),
            ("⊞", "Commands"),
            ("🖥", "Apps"),
            ("🌐", "Browser"),
            ("📁", "Files"),
            ("⚙", "System"),
            ("🎛", "Settings"),
        ]
        self._nav_buttons = []
        for icon, label in tabs:
            btn = QPushButton(f"{icon}  {label}")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(32)
            if label == "Home":
                btn.setChecked(True)
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 121, 0, 0.16);
                        border: 1.5px solid #FF7900;
                        border-radius: 8px;
                        color: #FFAA33;
                        font-weight: bold;
                        font-size: 11.5px;
                        padding: 3px 12px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: 1px solid transparent;
                        border-radius: 8px;
                        color: #A6A6B0;
                        font-weight: 500;
                        font-size: 11.5px;
                        padding: 3px 10px;
                    }
                    QPushButton:hover {
                        background: rgba(255, 255, 255, 0.05);
                        border: 1px solid rgba(255, 121, 0, 0.3);
                        color: #F5F5F5;
                    }
                    QPushButton:checked {
                        background: rgba(255, 121, 0, 0.16);
                        border: 1.5px solid #FF7900;
                        color: #FFAA33;
                    }
                """)
            if label == "Settings":
                btn.clicked.connect(self._open_settings)
            elif label == "Commands":
                btn.clicked.connect(lambda: self._quick_command("what commands can you do"))
            elif label == "Browser":
                btn.clicked.connect(lambda: self._quick_command("open chrome"))
            elif label == "Files":
                btn.clicked.connect(lambda: self._quick_command("open file explorer"))
            elif label == "System":
                btn.clicked.connect(lambda: self._quick_command("system status"))
            btn.clicked.connect(lambda _, b=btn: self._on_tab_clicked(b))
            self._nav_buttons.append(btn)
            nav_box.addWidget(btn)

        hlay.addLayout(nav_box)
        hlay.addStretch(1)

        # Clear vector-painted Window Controls (Pin, Minimize, Maximize, Close)
        win_ctrl = QHBoxLayout()
        win_ctrl.setSpacing(6)

        self.btn_pin = WindowControlBtn("pin")
        self.btn_pin.clicked.connect(self._toggle_always_on_top)

        self.btn_min = WindowControlBtn("min")
        self.btn_min.clicked.connect(self.showMinimized)

        self.btn_max = WindowControlBtn("max")
        self.btn_max.clicked.connect(self._toggle_maximize)

        self.btn_close = WindowControlBtn("close")
        self.btn_close.clicked.connect(self.close)

        win_ctrl.addWidget(self.btn_pin)
        win_ctrl.addWidget(self.btn_min)
        win_ctrl.addWidget(self.btn_max)
        win_ctrl.addWidget(self.btn_close)

        hlay.addLayout(win_ctrl)
        return header

    def _toggle_always_on_top(self):
        """Pins FRIDAY above all other windows (e.g. while web browsing)."""
        flags = self.windowFlags()
        if flags & Qt.WindowStaysOnTopHint:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
            self.btn_pin.is_pinned = False
        else:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
            self.btn_pin.is_pinned = True
        self.show()
        self.btn_pin.update()

    def _on_tab_clicked(self, clicked_btn: QPushButton):
        for btn in self._nav_buttons:
            if btn != clicked_btn:
                btn.setChecked(False)
        clicked_btn.setChecked(True)

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.btn_max.is_maximized = False
        else:
            self.showMaximized()
            self.btn_max.is_maximized = True
        self.btn_max.update()

    # Window drag handler for frameless window
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.position().y() <= 54:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

    # ── 2. Left Sidebar (STATUS + QUICK COMMANDS cards) ───────────────────────

    def _build_sidebar(self) -> QWidget:
        side = QWidget()
        side.setFixedWidth(220)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        # ── Card 1: STATUS ──
        status_card = QFrame()
        status_card.setStyleSheet("""
            QFrame {
                background-color: #121216;
                border: 1px solid rgba(255, 121, 0, 0.22);
                border-radius: 12px;
            }
        """)
        sc_lay = QVBoxLayout(status_card)
        sc_lay.setContentsMargins(12, 10, 12, 10)
        sc_lay.setSpacing(8)

        st_title = QLabel("STATUS")
        st_title.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 800; letter-spacing: 1.5px;")
        sc_lay.addWidget(st_title)

        # Listening circle indicator
        mic_box = QHBoxLayout()
        mic_box.setSpacing(10)

        self.mic_badge = QLabel("🎙")
        self.mic_badge.setFixedSize(44, 44)
        self.mic_badge.setAlignment(Qt.AlignCenter)
        self.mic_badge.setStyleSheet("""
            QLabel {
                background: rgba(255, 121, 0, 0.12);
                border: 2px solid #FF7900;
                border-radius: 22px;
                color: #FF7900;
                font-size: 20px;
            }
        """)
        mic_box.addWidget(self.mic_badge)

        mic_text_lay = QVBoxLayout()
        mic_text_lay.setSpacing(1)
        l_for = QLabel("Listening for")
        l_for.setStyleSheet("color: #8C8C96; font-size: 10px;")
        self.wake_phrase_lbl = QLabel('"Hey FRIDAY"')
        self.wake_phrase_lbl.setStyleSheet("color: #FFAA33; font-size: 13px; font-weight: bold;")
        mic_text_lay.addWidget(l_for)
        mic_text_lay.addWidget(self.wake_phrase_lbl)
        mic_box.addLayout(mic_text_lay)
        sc_lay.addLayout(mic_box)

        # 4 Status rows
        sc_lay.addWidget(self._build_status_row("🎙", "Wake Word:", "Active (24/7)"))
        sc_lay.addWidget(self._build_status_row("🎙", "Microphone:", "Always On"))
        sc_lay.addWidget(self._build_status_row("⚡", "Mode:", "Background Active"))
        self._status_ready_val = QLabel("● Ready")
        self._status_ready_val.setStyleSheet("color: #22C55E; font-size: 10.5px; font-weight: bold;")
        sc_lay.addWidget(self._build_status_row("⚙", "Status:", "Ready", custom_val=self._status_ready_val))

        lay.addWidget(status_card)

        # ── Card 2: QUICK COMMANDS ──
        qc_card = QFrame()
        qc_card.setStyleSheet("""
            QFrame {
                background-color: #121216;
                border: 1px solid rgba(255, 121, 0, 0.22);
                border-radius: 12px;
            }
        """)
        qc_lay = QVBoxLayout(qc_card)
        qc_lay.setContentsMargins(12, 10, 12, 10)
        qc_lay.setSpacing(6)

        qc_title = QLabel("QUICK COMMANDS")
        qc_title.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 800; letter-spacing: 1.5px;")
        qc_lay.addWidget(qc_title)

        quick_commands = [
            ("▶", "#FF0000", "Open YouTube",       "open YouTube"),
            ("◉", "#4285F4", "Open Chrome",        "open Chrome"),
            ("📝", "#FF7900", "Open Notepad",       "open Notepad"),
            ("🔢", "#FFAA33", "Open Calculator",    "open Calculator"),
            ("📁", "#FFCC00", "Open File Explorer", "open File Explorer"),
            ("🔍", "#A6A6A6", "Search the Web",     "search the web for "),
        ]
        for icon, col, label, cmd in quick_commands:
            btn = QPushButton(f"  {icon}   {label}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: #17171C;
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 7px;
                    color: #E2E2E6;
                    text-align: left;
                    padding-left: 10px;
                    font-size: 11.5px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background: #201E22;
                    border: 1px solid rgba(255, 121, 0, 0.35);
                    color: #FFAA33;
                }}
            """)
            btn.clicked.connect(lambda _, c=cmd: self._quick_command(c))
            qc_lay.addWidget(btn)

        lay.addWidget(qc_card)
        lay.addStretch(1)
        return side

    def _build_status_row(self, icon: str, label: str, value_text: str, custom_val=None) -> QWidget:
        row = QWidget()
        rlay = QHBoxLayout(row)
        rlay.setContentsMargins(0, 0, 0, 0)
        rlay.setSpacing(6)

        ic = QLabel(icon)
        ic.setStyleSheet("color: #FF7900; font-size: 11px;")
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #8C8C96; font-size: 10.5px;")

        rlay.addWidget(ic)
        rlay.addWidget(lbl)
        rlay.addStretch()

        if custom_val:
            rlay.addWidget(custom_val)
        else:
            val = QLabel(f"● {value_text}")
            val.setStyleSheet("color: #22C55E; font-size: 10.5px; font-weight: bold;")
            rlay.addWidget(val)

        return row

    # ── 3. Center Panel (Arc Reactor + 4 Action Buttons) ───────────────────────

    def _build_centre(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        # Core Visualizer Reactor (Scales smoothly to avoid cutting off bottom input deck)
        self.visualizer = CoreVisualizerWidget()
        self.visualizer.setMinimumSize(220, 220)
        self.visualizer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay.addWidget(self.visualizer, 1, Qt.AlignCenter)

        # 4 Action Control Buttons Row matching reference image:
        # [ Start Listening | Pause | Stop | Cancel Task ]
        ctrl = QHBoxLayout()
        ctrl.setSpacing(8)
        ctrl.setContentsMargins(6, 0, 6, 0)

        self.listen_btn = QPushButton("🎙  Listening (Always Active)")
        self.listen_btn.setCursor(Qt.PointingHandCursor)
        self.listen_btn.setFixedHeight(36)
        self.listen_btn.setToolTip("Background wake-word is active 24/7. Say 'Hey FRIDAY' anytime, or click for manual push-to-talk.")
        self.listen_btn.setStyleSheet("""
            QPushButton {
                background: rgba(34, 197, 94, 0.12);
                border: 1.5px solid #22C55E;
                border-radius: 8px;
                color: #22C55E;
                font-weight: bold;
                font-size: 11.5px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background: rgba(34, 197, 94, 0.22);
                color: #FFFFFF;
            }
        """)
        self.listen_btn.clicked.connect(self._toggle_voice_input)

        pause_btn = QPushButton("⏸  Pause")
        pause_btn.setCursor(Qt.PointingHandCursor)
        pause_btn.setFixedHeight(36)
        pause_btn.setStyleSheet(self._control_btn_style())
        pause_btn.clicked.connect(lambda: self.core.wake_detector.pause())

        stop_btn = QPushButton("⏹  Stop")
        stop_btn.setCursor(Qt.PointingHandCursor)
        stop_btn.setFixedHeight(36)
        stop_btn.setStyleSheet(self._control_btn_style())
        stop_btn.clicked.connect(lambda: self.core.wake_detector.stop())

        cancel_btn = QPushButton("✕  Cancel Task")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFixedHeight(36)
        cancel_btn.setStyleSheet(self._control_btn_style())
        cancel_btn.clicked.connect(self._trigger_emergency_stop)

        ctrl.addWidget(self.listen_btn)
        ctrl.addWidget(pause_btn)
        ctrl.addWidget(stop_btn)
        ctrl.addWidget(cancel_btn)

        lay.addLayout(ctrl)
        return panel

    def _control_btn_style(self) -> str:
        return """
            QPushButton {
                background: #17171C;
                border: 1px solid rgba(255, 255, 255, 0.09);
                border-radius: 8px;
                color: #C5C5CE;
                font-weight: 600;
                font-size: 11.5px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background: #22222A;
                border: 1px solid rgba(255, 121, 0, 0.35);
                color: #FFFFFF;
            }
        """

    # ── 4. Right Conversation Panel ───────────────────────────────────────────

    def _build_chat_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFixedWidth(360)
        panel.setStyleSheet("""
            QFrame {
                background-color: #121216;
                border: 1px solid rgba(255, 121, 0, 0.22);
                border-radius: 12px;
            }
        """)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(6)

        # Header: Hexagon Icon + CONVERSATION | Clear button
        head = QHBoxLayout()
        head.setContentsMargins(4, 0, 4, 2)

        icon_lbl = QLabel("🔶")
        icon_lbl.setStyleSheet("color: #FF7900; font-size: 12px;")
        t_lbl = QLabel("CONVERSATION")
        t_lbl.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 800; letter-spacing: 1.5px;")

        clear_btn = QPushButton("🗑 Clear")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                color: #8C8C96;
                font-size: 10.5px;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background: rgba(255, 121, 0, 0.15);
                border: 1px solid #FF7900;
                color: #FFAA33;
            }
        """)
        clear_btn.clicked.connect(self._clear_chat)

        head.addWidget(icon_lbl)
        head.addWidget(t_lbl)
        head.addStretch()
        head.addWidget(clear_btn)

        lay.addLayout(head)

        # Chat widget with message cards
        self.chat_widget = ChatWidget()
        lay.addWidget(self.chat_widget, 1)

        return panel

    # ── 5. Bottom Command Input Deck (ALWAYS PROMINENT) ───────────────────────

    def _build_command_deck(self) -> QWidget:
        deck = QFrame()
        deck.setFixedHeight(50)
        deck.setObjectName("commandDeck")
        deck.setStyleSheet("""
            QFrame#commandDeck {
                background-color: #111116;
                border: 1.5px solid rgba(255, 121, 0, 0.38);
                border-radius: 12px;
            }
        """)
        lay = QHBoxLayout(deck)
        lay.setContentsMargins(14, 4, 8, 4)
        lay.setSpacing(10)

        # Keyboard icon on left
        kb_icon = QLabel("⌨")
        kb_icon.setStyleSheet("color: #FF7900; font-size: 16px;")
        lay.addWidget(kb_icon)

        # Input line with explicit text color & styling
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText('Type your command here or say "Hey FRIDAY" (Global Hotkey: Ctrl+Alt+F)...')
        self.cmd_input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 500;
                selection-background-color: #FF7900;
            }
            QLineEdit::placeholder {
                color: #72727C;
                font-style: italic;
            }
        """)
        self.cmd_input.returnPressed.connect(self._send_typed_command)
        lay.addWidget(self.cmd_input, 1)

        # Bright solid orange Send button [ ➤ ]
        self.send_btn = QPushButton("➤")
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setToolTip("Send Command (Enter)")
        self.send_btn.setFixedSize(38, 38)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: #FF7900;
                border: none;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #FFAA33;
            }
            QPushButton:pressed {
                background: #E06000;
            }
        """)
        self.send_btn.clicked.connect(self._send_typed_command)
        lay.addWidget(self.send_btn)

        # Mic button [ 🎙 ]
        self.mic_btn = QPushButton("🎙")
        self.mic_btn.setCursor(Qt.PointingHandCursor)
        self.mic_btn.setToolTip("Voice Input (or speak 'Hey FRIDAY')")
        self.mic_btn.setFixedSize(38, 38)
        self.mic_btn.setStyleSheet("""
            QPushButton {
                background: #18181F;
                border: 1px solid rgba(255, 121, 0, 0.40);
                border-radius: 8px;
                color: #FF7900;
                font-size: 16px;
            }
            QPushButton:hover {
                background: rgba(255, 121, 0, 0.22);
                border: 1px solid #FF7900;
                color: #FFAA33;
            }
        """)
        self.mic_btn.clicked.connect(self._toggle_voice_input)
        lay.addWidget(self.mic_btn)

        return deck

    # ── 6. Bottom Status Bar ──────────────────────────────────────────────────

    def _build_status_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(24)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(4, 0, 4, 0)
        lay.setSpacing(12)

        # Left: Logo + Version
        v_box = QHBoxLayout()
        v_box.setSpacing(6)
        diamond_mini = QLabel("🔶")
        diamond_mini.setStyleSheet("color: #FF7900; font-size: 10px;")
        ver_lbl = QLabel(f"{APP_NAME} v{APP_VERSION}")
        ver_lbl.setStyleSheet("color: #8C8C96; font-size: 10.5px;")
        v_box.addWidget(diamond_mini)
        v_box.addWidget(ver_lbl)
        lay.addLayout(v_box)

        # Middle: Global Hotkey hint
        hotkey_hint = QLabel('⌨ Global Hotkey: <span style="color:#FFAA33;">Ctrl+Alt+F</span> | Background Wake: <span style="color:#FFAA33;">"Hey FRIDAY"</span>')
        hotkey_hint.setStyleSheet("color: #72727C; font-size: 10px;")
        lay.addStretch(1)
        lay.addWidget(hotkey_hint)
        lay.addStretch(1)

        # Right: Online dot + Mic + Volume + Terminal + Clock
        r_box = QHBoxLayout()
        r_box.setSpacing(12)

        online_lbl = QLabel("● Online")
        online_lbl.setStyleSheet("color: #22C55E; font-size: 10.5px; font-weight: bold;")
        r_box.addWidget(online_lbl)

        mic_ico = QLabel("🎙")
        mic_ico.setStyleSheet("color: #8C8C96; font-size: 10.5px;")
        r_box.addWidget(mic_ico)

        vol_ico = QLabel("🔊")
        vol_ico.setStyleSheet("color: #8C8C96; font-size: 10.5px;")
        r_box.addWidget(vol_ico)

        self._clock_lbl = QLabel(datetime.now().strftime("%I:%M %p  |  %m/%d/%Y"))
        self._clock_lbl.setStyleSheet("color: #8C8C96; font-size: 10.5px;")
        r_box.addWidget(self._clock_lbl)

        # Update clock every 30s
        clk_timer = QTimer(self)
        clk_timer.timeout.connect(lambda: self._clock_lbl.setText(datetime.now().strftime("%I:%M %p  |  %m/%d/%Y")))
        clk_timer.start(30000)

        lay.addLayout(r_box)
        return bar

    # ──────────────────────────────────────────────────────────────────────────
    #  Cross-Application & Background Invocation
    # ──────────────────────────────────────────────────────────────────────────

    def _init_global_hotkey(self):
        """Initializes global system hotkeys (Ctrl+Alt+F, Ctrl+Alt+M, Ctrl+Alt+X)."""
        try:
            self.hotkey_listener = GlobalHotkeyListener(
                on_toggle_overlay=self._on_global_hotkey_triggered,
                on_toggle_mic=self._toggle_mic_from_hotkey,
                on_emergency_stop=self._trigger_emergency_stop,
            )
            self.hotkey_listener.start()
        except Exception as e:
            print(f"[MainWindow] Hotkey listener notice: {e}")

    def _on_global_hotkey_triggered(self):
        """Invoked when user presses Ctrl+Alt+F (or Ctrl+Shift+F) anywhere in Windows."""
        QTimer.singleShot(0, self._handle_toggle_overlay_hotkey)

    def _handle_toggle_overlay_hotkey(self):
        if self.overlay.isVisible():
            self.overlay.hide_overlay()
            self.bring_to_front()
        elif not self.isVisible() or self.isMinimized():
            self.overlay.show_overlay()
        else:
            self.bring_to_front()

    def _toggle_mic_from_hotkey(self):
        """Invoked when user presses Ctrl+Alt+M anywhere in Windows."""
        QTimer.singleShot(0, self._handle_toggle_mic_hotkey)

    def _handle_toggle_mic_hotkey(self):
        is_listening = self.core.toggle_listening()
        self.overlay.set_mic_muted(not is_listening)
        if hasattr(self, "_status_ready_val") and self._status_ready_val:
            if is_listening:
                self._status_ready_val.setText("● Ready")
                self._status_ready_val.setStyleSheet("color: #22C55E; font-size: 10.5px; font-weight: bold;")
            else:
                self._status_ready_val.setText("● Mic Paused")
                self._status_ready_val.setStyleSheet("color: #EF4444; font-size: 10.5px; font-weight: bold;")

    def _on_overlay_mic_mute_toggled(self, is_muted: bool):
        if is_muted:
            self.core.pause_listening()
        else:
            self.core.resume_listening()

    def _on_wake_detected_ui(self, command: Optional[str] = None):
        """Called on GUI thread when wake-word is detected while user is in any other application."""
        if self.isVisible() and not self.isMinimized() and self.isActiveWindow():
            self.visualizer.set_state("PROCESSING" if command else "LISTENING")
        else:
            self.overlay.show_overlay(user_text=command or None, initial_state="PROCESSING" if command else "LISTENING")

    def bring_to_front(self):
        """Restores and surfaces FRIDAY to the foreground from any browser, website, or app."""
        if self.overlay.isVisible():
            self.overlay.hide_overlay()

        if self.isMinimized():
            self.showNormal()
        else:
            self.show()

        self.raise_()
        self.activateWindow()

        # Force Windows 11 foreground activation
        try:
            import win32gui
            import win32con
            hwnd = int(self.winId())
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass

        self.cmd_input.setFocus()
        self.cmd_input.selectAll()

    # ──────────────────────────────────────────────────────────────────────────
    #  Slots & Handlers
    # ──────────────────────────────────────────────────────────────────────────

    def _quick_command(self, cmd_text: str):
        if cmd_text.endswith(" "):
            self.cmd_input.setText(cmd_text)
            self.cmd_input.setFocus()
            self.cmd_input.setCursorPosition(len(cmd_text))
        else:
            self._execute_text(cmd_text)

    def _send_typed_command(self):
        text = self.cmd_input.text().strip()
        if text:
            self.cmd_input.clear()
            self._execute_text(text)

    def _execute_text(self, text: str):
        self.worker.handle_command(text)

    def _toggle_voice_input(self):
        if not self.core.is_listening():
            self._enable_listening()
        else:
            self.worker.handle_voice_listen()

    def _trigger_emergency_stop(self):
        self.core.security.trigger_emergency_stop()
        self.core.wake_detector.stop()
        self.core.tts.stop()
        self.visualizer.set_state("STOPPED")
        self.overlay.set_state("STOPPED")
        self.chat_widget.add_message("SYSTEM", "EMERGENCY STOP ACTIVATED. All background tasks paused.")

    def _clear_chat(self):
        self.chat_widget.clear()

    def _open_settings(self):
        dlg = SettingsDialog(self.core.settings, self)
        dlg.exec()

    @Slot(str, str)
    def _on_chat_message(self, sender: str, text: str):
        self.chat_widget.add_message(sender, text)
        if sender == "USER":
            if not self.isVisible() or self.isMinimized() or not self.isActiveWindow():
                self.overlay.show_overlay(user_text=text, initial_state="PROCESSING")
            else:
                self.overlay.user_query_lbl.setText(f'"{text}"')
        elif sender == "FRIDAY":
            query_text = self.overlay.user_query_lbl.text().replace('"', '')
            self.overlay.update_interaction(user_text=query_text, response_text=text)

    @Slot(str)
    def _on_state_change(self, state: str):
        self.visualizer.set_state(state)
        self.overlay.set_state(state)
        st_clean = state.upper()
        if hasattr(self, "listen_btn") and self.listen_btn:
            if st_clean in ("LISTENING", "SPEAKING"):
                self.listen_btn.setText("🎙  Listening...")
                self.listen_btn.setStyleSheet("background: rgba(255, 170, 51, 0.18); border: 1.5px solid #FFAA33; border-radius: 8px; color: #FFAA33; font-weight: bold; font-size: 11.5px; padding: 0 14px;")
            elif st_clean in ("PROCESSING", "EXECUTING"):
                self.listen_btn.setText("⚡  Executing...")
                self.listen_btn.setStyleSheet("background: rgba(255, 121, 0, 0.18); border: 1.5px solid #FF7900; border-radius: 8px; color: #FF7900; font-weight: bold; font-size: 11.5px; padding: 0 14px;")
            elif st_clean == "STOPPED":
                self.listen_btn.setText("⏸  Mic Paused (Click to Resume)")
                self.listen_btn.setStyleSheet("background: rgba(239, 68, 68, 0.18); border: 1.5px solid #EF4444; border-radius: 8px; color: #EF4444; font-weight: bold; font-size: 11.5px; padding: 0 14px;")
            else:
                self.listen_btn.setText("🎙  Listening (Always Active)")
                self.listen_btn.setStyleSheet("background: rgba(34, 197, 94, 0.12); border: 1.5px solid #22C55E; border-radius: 8px; color: #22C55E; font-weight: bold; font-size: 11.5px; padding: 0 14px;")

        if self._status_ready_val:
            if st_clean in ("LISTENING", "SPEAKING"):
                self._status_ready_val.setText(f"● {st_clean.title()}")
                self._status_ready_val.setStyleSheet("color: #FFAA33; font-size: 10.5px; font-weight: bold;")
            elif st_clean in ("PROCESSING", "EXECUTING"):
                self._status_ready_val.setText(f"● {st_clean.title()}")
                self._status_ready_val.setStyleSheet("color: #FF7900; font-size: 10.5px; font-weight: bold;")
            elif st_clean == "STOPPED":
                self._status_ready_val.setText("● Stopped")
                self._status_ready_val.setStyleSheet("color: #EF4444; font-size: 10.5px; font-weight: bold;")
            else:
                self._status_ready_val.setText("● Ready")
                self._status_ready_val.setStyleSheet("color: #22C55E; font-size: 10.5px; font-weight: bold;")

    @Slot(int, int, str)
    def _on_task_progress(self, current: int, total: int, desc: str):
        pass

    def _ask_user_permission(self, req: ActionRequest) -> bool:
        self.confirm_action_signal.emit(req)
        return True

    @Slot(object)
    def _show_permission_dialog(self, req: ActionRequest):
        dlg = PermissionDialog(req, self)
        dlg.exec()

    # ──────────────────────────────────────────────────────────────────────────
    #  Tray / Lifecycle
    # ──────────────────────────────────────────────────────────────────────────

    def _init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("FRIDAY Assistant (Ctrl+Alt+F)")
        if ICON_PNG.exists():
            self.tray_icon.setIcon(QIcon(str(ICON_PNG)))

        menu = QMenu()
        menu.addAction("Show FRIDAY", self.bring_to_front)
        menu.addAction("Hide FRIDAY", self.hide)
        menu.addAction("Show Overlay", lambda: self.overlay.show_overlay())
        menu.addSeparator()
        menu.addAction("Enable listening", self._enable_listening)
        menu.addAction("Pause listening", self._pause_listening)
        menu.addAction("Stop the current task", self._trigger_emergency_stop)
        menu.addSeparator()
        menu.addAction("Settings", self._open_settings)
        menu.addSeparator()
        menu.addAction("Exit FRIDAY completely", self.exit_application)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    def _enable_listening(self):
        self.core.resume_listening()
        self.overlay.set_mic_muted(False)
        if hasattr(self, "listen_btn") and self.listen_btn:
            self.listen_btn.setText("🎙  Listening (Always Active)")
            self.listen_btn.setStyleSheet("background: rgba(34, 197, 94, 0.12); border: 1.5px solid #22C55E; border-radius: 8px; color: #22C55E; font-weight: bold; font-size: 11.5px; padding: 0 14px;")
        if self._status_ready_val:
            self._status_ready_val.setText("● Ready")
            self._status_ready_val.setStyleSheet("color: #22C55E; font-size: 10.5px; font-weight: bold;")

    def _pause_listening(self):
        self.core.pause_listening()
        self.overlay.set_mic_muted(True)
        if hasattr(self, "listen_btn") and self.listen_btn:
            self.listen_btn.setText("⏸  Mic Paused (Click to Resume)")
            self.listen_btn.setStyleSheet("background: rgba(239, 68, 68, 0.18); border: 1.5px solid #EF4444; border-radius: 8px; color: #EF4444; font-weight: bold; font-size: 11.5px; padding: 0 14px;")
        if self._status_ready_val:
            self._status_ready_val.setText("● Mic Paused")
            self._status_ready_val.setStyleSheet("color: #EF4444; font-size: 10.5px; font-weight: bold;")

    def _init_shortcuts(self):
        QShortcut(QKeySequence("Escape"), self).activated.connect(self._trigger_emergency_stop)
        QShortcut(QKeySequence("Alt+X"), self).activated.connect(self._trigger_emergency_stop)

    def exit_application(self):
        self._force_quit = True
        self.cleanup()
        QApplication.quit()

    def cleanup(self):
        try:
            if hasattr(self, "overlay"):
                self.overlay.hide_overlay()
            if hasattr(self, "hotkey_listener"):
                self.hotkey_listener.stop()
            self.core.wake_detector.stop()
            self.core.tts.stop()
            self.worker_thread.quit()
            self.worker_thread.wait(400)
        except Exception:
            pass

    def closeEvent(self, event):
        if self._force_quit or not self.core.settings.get("system.minimize_to_tray", True):
            self.cleanup()
            event.accept()
        else:
            event.ignore()
            self.hide()
