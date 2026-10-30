"""
FRIDAY AI — Orange Sci-Fi Futuristic Stylesheet v1.2.0
Premium dark orange-and-black design system.
"""

from config.constants import (
    COLOR_AMBER,
    COLOR_BG_CARD,
    COLOR_BG_DARK,
    COLOR_BG_INPUT,
    COLOR_BG_SECONDARY,
    COLOR_BORDER,
    COLOR_BORDER_FOCUS,
    COLOR_ERROR,
    COLOR_ORANGE,
    COLOR_ORANGE_DIM,
    COLOR_ORANGE_PALE,
    COLOR_SUCCESS,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_WARNING,
)

FUTURISTIC_STYLESHEET = f"""
/* ══════════════════════════════════════════════════
   GLOBAL BASE
══════════════════════════════════════════════════ */
QMainWindow, QDialog, QWidget {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_PRIMARY};
    font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
    font-size: 13px;
}}

/* ══════════════════════════════════════════════════
   PANEL CARDS
══════════════════════════════════════════════════ */
QFrame#panelCard {{
    background-color: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
}}

QFrame#sidebarCard {{
    background-color: {COLOR_BG_SECONDARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
}}

/* ══════════════════════════════════════════════════
   HEADER
══════════════════════════════════════════════════ */
QLabel#headerTitle {{
    font-size: 20px;
    font-weight: 800;
    color: {COLOR_ORANGE};
    letter-spacing: 3px;
}}

QLabel#headerSubtitle {{
    font-size: 10px;
    font-weight: 500;
    color: {COLOR_TEXT_SECONDARY};
    letter-spacing: 1.5px;
}}

QLabel#statusBadge {{
    background-color: rgba(255,121,0,0.12);
    border: 1px solid {COLOR_ORANGE};
    border-radius: 10px;
    padding: 4px 14px;
    font-weight: 700;
    font-size: 10px;
    letter-spacing: 2px;
    color: {COLOR_ORANGE};
}}

/* ══════════════════════════════════════════════════
   NAVIGATION BAR
══════════════════════════════════════════════════ */
QFrame#navBar {{
    background-color: {COLOR_BG_SECONDARY};
    border-bottom: 1px solid {COLOR_BORDER};
    border-radius: 0px;
}}

QPushButton#navButton {{
    background-color: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0px;
    color: {COLOR_TEXT_SECONDARY};
    font-size: 11px;
    font-weight: 600;
    padding: 10px 16px 8px 16px;
    letter-spacing: 0.5px;
}}

QPushButton#navButton:hover {{
    color: {COLOR_TEXT_PRIMARY};
    border-bottom: 2px solid rgba(255,121,0,0.5);
}}

QPushButton#navButton:checked {{
    color: {COLOR_ORANGE};
    border-bottom: 2px solid {COLOR_ORANGE};
    background-color: rgba(255,121,0,0.08);
}}

/* ══════════════════════════════════════════════════
   INPUT FIELD
══════════════════════════════════════════════════ */
QLineEdit#commandInput {{
    background-color: {COLOR_BG_INPUT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 22px;
    padding: 12px 20px;
    color: {COLOR_TEXT_PRIMARY};
    font-size: 14px;
    selection-background-color: {COLOR_ORANGE};
    selection-color: #000;
}}

QLineEdit#commandInput:focus {{
    border: 1.5px solid {COLOR_ORANGE};
    background-color: #1e1206;
}}

/* ══════════════════════════════════════════════════
   BUTTONS — BASE
══════════════════════════════════════════════════ */
QPushButton {{
    background-color: rgba(255,121,0,0.1);
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 8px 16px;
    color: {COLOR_TEXT_SECONDARY};
    font-weight: 600;
    letter-spacing: 0.5px;
}}

QPushButton:hover {{
    background-color: rgba(255,121,0,0.18);
    border: 1px solid {COLOR_ORANGE};
    color: {COLOR_TEXT_PRIMARY};
}}

QPushButton:pressed {{
    background-color: rgba(255,121,0,0.35);
}}

/* ══════════════════════════════════════════════════
   SEND / EXECUTE BUTTON
══════════════════════════════════════════════════ */
QPushButton#primaryButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLOR_ORANGE}, stop:1 {COLOR_AMBER});
    color: #0A0A0C;
    font-weight: 800;
    border: none;
    border-radius: 22px;
    min-width: 44px;
    max-width: 44px;
    min-height: 44px;
    max-height: 44px;
    font-size: 18px;
    padding: 0px;
}}

QPushButton#primaryButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLOR_AMBER}, stop:1 #FFD08A);
}}

/* ══════════════════════════════════════════════════
   MIC BUTTON
══════════════════════════════════════════════════ */
QPushButton#micButton {{
    background-color: rgba(255,121,0,0.12);
    border: 1.5px solid {COLOR_ORANGE};
    border-radius: 22px;
    min-width: 44px;
    max-width: 44px;
    min-height: 44px;
    max-height: 44px;
    font-size: 18px;
    color: {COLOR_ORANGE};
    padding: 0px;
}}

QPushButton#micButton:hover {{
    background-color: rgba(255,121,0,0.25);
}}

QPushButton#micButton:checked, QPushButton#micButtonActive {{
    background-color: {COLOR_ORANGE};
    border: 2px solid {COLOR_AMBER};
    color: #000;
}}

/* ══════════════════════════════════════════════════
   CONTROL BUTTONS (Listen, Pause, Stop, Cancel)
══════════════════════════════════════════════════ */
QPushButton#listenButton {{
    background-color: {COLOR_ORANGE};
    border: none;
    border-radius: 8px;
    color: #000;
    font-weight: 700;
    font-size: 11px;
    padding: 8px 14px;
}}

QPushButton#listenButton:hover {{
    background-color: {COLOR_AMBER};
}}

QPushButton#pauseButton, QPushButton#stopButton {{
    background-color: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 8px;
    color: {COLOR_TEXT_SECONDARY};
    font-weight: 600;
    font-size: 11px;
    padding: 8px 14px;
}}

QPushButton#pauseButton:hover, QPushButton#stopButton:hover {{
    background-color: rgba(255,121,0,0.15);
    border-color: {COLOR_ORANGE};
    color: {COLOR_TEXT_PRIMARY};
}}

QPushButton#cancelButton {{
    background-color: rgba(239,68,68,0.1);
    border: 1px solid rgba(239,68,68,0.35);
    border-radius: 8px;
    color: {COLOR_ERROR};
    font-weight: 600;
    font-size: 11px;
    padding: 8px 14px;
}}

QPushButton#cancelButton:hover {{
    background-color: {COLOR_ERROR};
    color: white;
}}

/* ══════════════════════════════════════════════════
   EMERGENCY STOP
══════════════════════════════════════════════════ */
QPushButton#emergencyStopButton {{
    background-color: rgba(239,68,68,0.1);
    border: 1px solid {COLOR_ERROR};
    color: {COLOR_ERROR};
    font-weight: 700;
    border-radius: 8px;
    padding: 6px 14px;
}}

QPushButton#emergencyStopButton:hover {{
    background-color: {COLOR_ERROR};
    color: white;
}}

/* ══════════════════════════════════════════════════
   QUICK COMMAND BUTTONS (Sidebar)
══════════════════════════════════════════════════ */
QPushButton#quickCmdButton {{
    background-color: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,121,0,0.15);
    border-radius: 8px;
    color: {COLOR_TEXT_PRIMARY};
    font-weight: 500;
    font-size: 12px;
    padding: 10px 14px;
    text-align: left;
}}

QPushButton#quickCmdButton:hover {{
    background-color: rgba(255,121,0,0.12);
    border: 1px solid {COLOR_ORANGE};
    color: {COLOR_ORANGE};
}}

/* ══════════════════════════════════════════════════
   STATUS INDICATORS
══════════════════════════════════════════════════ */
QLabel#statusLabel {{
    font-size: 11px;
    color: {COLOR_TEXT_SECONDARY};
    font-weight: 500;
}}

QLabel#statusValue {{
    font-size: 11px;
    color: {COLOR_SUCCESS};
    font-weight: 700;
}}

QLabel#statusTitle {{
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 2px;
    color: {COLOR_ORANGE};
}}

QLabel#sectionTitle {{
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 2px;
    color: {COLOR_TEXT_SECONDARY};
    padding: 8px 0px 4px 0px;
}}

/* ══════════════════════════════════════════════════
   SCROLLBARS
══════════════════════════════════════════════════ */
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 4px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: rgba(255,121,0,0.3);
    min-height: 20px;
    border-radius: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLOR_ORANGE};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    height: 0px;
}}

/* ══════════════════════════════════════════════════
   TAB WIDGET
══════════════════════════════════════════════════ */
QTabWidget::pane {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    background: {COLOR_BG_CARD};
    padding: 10px;
}}

QTabBar::tab {{
    background: transparent;
    color: {COLOR_TEXT_SECONDARY};
    padding: 8px 16px;
    font-weight: 600;
    border-bottom: 2px solid transparent;
}}

QTabBar::tab:selected {{
    color: {COLOR_ORANGE};
    border-bottom: 2px solid {COLOR_ORANGE};
}}

QTabBar::tab:hover {{
    color: {COLOR_TEXT_PRIMARY};
}}

/* ══════════════════════════════════════════════════
   FORM CONTROLS
══════════════════════════════════════════════════ */
QComboBox, QSpinBox {{
    background-color: {COLOR_BG_INPUT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    color: {COLOR_TEXT_PRIMARY};
}}

QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {COLOR_BORDER_FOCUS};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QCheckBox {{
    color: {COLOR_TEXT_PRIMARY};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    background-color: {COLOR_BG_INPUT};
}}

QCheckBox::indicator:checked {{
    background-color: {COLOR_ORANGE};
    border-color: {COLOR_ORANGE};
}}

/* ══════════════════════════════════════════════════
   PROGRESS BANNER
══════════════════════════════════════════════════ */
QLabel#progressBanner {{
    background-color: rgba(255,121,0,0.08);
    border: 1px dashed {COLOR_ORANGE};
    color: {COLOR_ORANGE};
    padding: 6px 14px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 12px;
}}

/* ══════════════════════════════════════════════════
   STATUS BAR (Bottom)
══════════════════════════════════════════════════ */
QStatusBar {{
    background-color: {COLOR_BG_SECONDARY};
    border-top: 1px solid {COLOR_BORDER};
    color: {COLOR_TEXT_SECONDARY};
    font-size: 11px;
}}

QLabel#versionLabel {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 11px;
    font-weight: 600;
}}

/* ══════════════════════════════════════════════════
   CONVERSATION PANEL HEADER
══════════════════════════════════════════════════ */
QLabel#chatPanelTitle {{
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 2px;
    color: {COLOR_TEXT_SECONDARY};
}}

QPushButton#clearChatButton {{
    background: transparent;
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    color: {COLOR_TEXT_SECONDARY};
    font-size: 11px;
    padding: 4px 10px;
}}

QPushButton#clearChatButton:hover {{
    border-color: {COLOR_ORANGE};
    color: {COLOR_ORANGE};
}}

/* ══════════════════════════════════════════════════
   ONLINE INDICATOR DOT
══════════════════════════════════════════════════ */
QLabel#onlineDot {{
    color: {COLOR_SUCCESS};
    font-size: 18px;
}}

QLabel#onlineText {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 11px;
}}
"""
