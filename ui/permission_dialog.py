"""
Permission Confirmation Dialog for FRIDAY AI.
Prompts the user to review and authorize moderate and high-risk desktop actions.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from config.constants import (
    COLOR_BG_CARD,
    COLOR_BG_DARK,
    COLOR_BG_INPUT,
    COLOR_BORDER,
    COLOR_NEON_GREEN,
    COLOR_NEON_RED,
    COLOR_NEON_YELLOW,
    COLOR_PRIMARY_CYAN,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    RiskLevel,
)
from core.permissions import ActionRequest


class PermissionDialog(QDialog):
    def __init__(self, action_request: ActionRequest, parent=None):
        super().__init__(parent)
        self.request = action_request
        self.authorized = False
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("FRIDAY Security Authorization")
        self.setFixedSize(520, 380)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(f"background-color: {COLOR_BG_DARK}; border: 1px solid {COLOR_PRIMARY_CYAN}; border-radius: 12px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header Row: Title & Risk Level Badge
        header_layout = QHBoxLayout()
        title_label = QLabel("SECURITY CONFIRMATION REQUIRED")
        title_label.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {COLOR_PRIMARY_CYAN}; letter-spacing: 1px;")

        risk_col = COLOR_NEON_YELLOW if self.request.risk_level == RiskLevel.MODERATE else COLOR_NEON_RED
        badge_label = QLabel(f" {self.request.risk_level.value} RISK ")
        badge_label.setStyleSheet(
            f"background-color: rgba({int(risk_col[1:3], 16)}, {int(risk_col[3:5], 16)}, {int(risk_col[5:7], 16)}, 0.2); "
            f"border: 1px solid {risk_col}; color: {risk_col}; font-weight: 800; font-size: 11px; border-radius: 6px; padding: 3px 8px;"
        )

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(badge_label)
        layout.addLayout(header_layout)

        # Description
        desc_label = QLabel(self.request.description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"font-size: 13px; color: {COLOR_TEXT_PRIMARY}; font-weight: 600;")
        layout.addWidget(desc_label)

        # Preview Container
        preview_box = QTextEdit()
        preview_box.setReadOnly(True)
        preview_box.setStyleSheet(
            f"background-color: {COLOR_BG_INPUT}; border: 1px solid {COLOR_BORDER}; border-radius: 8px; color: {COLOR_TEXT_SECONDARY}; padding: 8px;"
        )

        preview_text = self.request.preview or "No additional preview details."
        preview_box.setPlainText(f"Action Details:\nTool: {self.request.tool_name}\nType: {self.request.action_type}\n\n{preview_text}")
        layout.addWidget(preview_box)

        # Warning text
        warning_label = QLabel("FRIDAY requires explicit permission before performing this system action.")
        warning_label.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_SECONDARY}; font-style: italic;")
        layout.addWidget(warning_label)

        # Action Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        reject_btn = QPushButton("Reject / Cancel")
        reject_btn.setStyleSheet(
            f"background-color: rgba(255, 42, 95, 0.15); border: 1px solid {COLOR_NEON_RED}; color: {COLOR_NEON_RED}; padding: 10px 20px; font-weight: 700; border-radius: 8px;"
        )
        reject_btn.clicked.connect(self._on_reject)

        approve_btn = QPushButton("Authorize Action")
        approve_btn.setStyleSheet(
            f"background-color: rgba(0, 255, 157, 0.2); border: 1px solid {COLOR_NEON_GREEN}; color: {COLOR_NEON_GREEN}; padding: 10px 20px; font-weight: 700; border-radius: 8px;"
        )
        approve_btn.clicked.connect(self._on_approve)

        button_layout.addStretch()
        button_layout.addWidget(reject_btn)
        button_layout.addWidget(approve_btn)
        layout.addLayout(button_layout)

    def _on_approve(self):
        self.authorized = True
        self.accept()

    def _on_reject(self):
        self.authorized = False
        self.reject()
