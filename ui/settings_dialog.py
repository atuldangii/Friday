"""
Comprehensive Settings Dialog for FRIDAY AI.
Provides user-friendly controls for Voice, AI models, Permissions, App Registry, and Memory.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config.constants import COLOR_NEON_GREEN, COLOR_NEON_RED, COLOR_PRIMARY_CYAN
from config.settings import SettingsManager
from core.memory import MemoryManager
from voice.speech_recognition import SpeechRecognizer
from voice.text_to_speech import TextToSpeechEngine


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = SettingsManager()
        self.memory = MemoryManager()
        self.tts = TextToSpeechEngine()
        self.recognizer = SpeechRecognizer()

        self.setWindowTitle("FRIDAY System Settings")
        self.resize(650, 520)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Tab Widget
        tabs = QTabWidget()
        tabs.addTab(self._create_voice_tab(), "Voice & Audio")
        tabs.addTab(self._create_ai_tab(), "AI & Intelligence")
        tabs.addTab(self._create_apps_tab(), "App Registry")
        tabs.addTab(self._create_security_tab(), "Security & Permissions")
        tabs.addTab(self._create_memory_tab(), "Memory & Data")

        main_layout.addWidget(tabs)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save_settings)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        main_layout.addLayout(btn_layout)

    def _create_voice_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)

        # Group: Voice Synthesis
        tts_group = QGroupBox("Spoken Responses (Text-to-Speech)")
        tts_layout = QFormLayout(tts_group)

        self.enable_voice_cb = QCheckBox("Enable Voice Output")
        self.enable_voice_cb.setChecked(self.settings.get("voice.enabled", True))
        tts_layout.addRow(self.enable_voice_cb)

        # Voice Selector
        self.voice_combo = QComboBox()
        voices = self.tts.list_available_voices()
        current_voice = self.settings.get("voice.voice_id", "")
        for idx, v in enumerate(voices):
            self.voice_combo.addItem(v["name"], v["id"])
            if v["id"] == current_voice:
                self.voice_combo.setCurrentIndex(idx)
        tts_layout.addRow("Voice Character:", self.voice_combo)

        # Rate Slider
        self.rate_slider = QSlider(Qt.Horizontal)
        self.rate_slider.setRange(100, 260)
        self.rate_slider.setValue(self.settings.get("voice.rate", 185))
        tts_layout.addRow("Speaking Rate (WPM):", self.rate_slider)

        # Volume Slider
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(10, 100)
        self.volume_slider.setValue(int(self.settings.get("voice.volume", 1.0) * 100))
        tts_layout.addRow("Speech Volume:", self.volume_slider)

        layout.addWidget(tts_group)

        # Group: Wake-word & Input
        input_group = QGroupBox("Wake-Word & Audio Input")
        input_layout = QFormLayout(input_group)

        self.wake_phrase_edit = QLineEdit(self.settings.get("wake_word.phrase", "hey friday"))
        input_layout.addRow("Wake Phrase:", self.wake_phrase_edit)

        # Mic Device Selector
        self.mic_combo = QComboBox()
        self.mic_combo.addItem("Default System Microphone", -1)
        mics = self.recognizer.list_microphones()
        current_mic_idx = self.settings.get("wake_word.input_device_index", -1)
        for idx, m in enumerate(mics):
            self.mic_combo.addItem(f"{idx}: {m}", idx)
            if idx == current_mic_idx:
                self.mic_combo.setCurrentIndex(idx + 1)
        input_layout.addRow("Microphone Device:", self.mic_combo)

        self.auto_listen_cb = QCheckBox("Start Wake-Word Listening automatically on application launch")
        self.auto_listen_cb.setChecked(self.settings.get("system.auto_listen_on_startup", False))
        input_layout.addRow(self.auto_listen_cb)

        layout.addWidget(input_group)
        layout.addStretch()
        return w

    def _create_ai_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)

        cloud_group = QGroupBox("Cloud AI Integration (Optional)")
        cloud_layout = QFormLayout(cloud_group)

        self.enable_cloud_cb = QCheckBox("Enable Cloud AI Intelligence (Gemini / OpenAI)")
        self.enable_cloud_cb.setChecked(self.settings.get("ai.enable_cloud_ai", False))
        cloud_layout.addRow(self.enable_cloud_cb)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["gemini", "openai"])
        self.provider_combo.setCurrentText(self.settings.get("ai.provider", "gemini"))
        cloud_layout.addRow("AI Provider:", self.provider_combo)

        self.gemini_key_edit = QLineEdit(self.settings.get("ai.gemini_api_key", ""))
        self.gemini_key_edit.setEchoMode(QLineEdit.Password)
        self.gemini_key_edit.setPlaceholderText("Enter GEMINI_API_KEY")
        cloud_layout.addRow("Gemini API Key:", self.gemini_key_edit)

        self.enable_vision_cb = QCheckBox("Enable Multimodal Screen Understanding (Vision)")
        self.enable_vision_cb.setChecked(self.settings.get("ai.enable_vision", True))
        cloud_layout.addRow(self.enable_vision_cb)

        info_label = QLabel("Note: FRIDAY works offline using local deterministic routing even if Cloud AI is disabled.")
        info_label.setStyleSheet("color: #8b949e; font-size: 11px; font-style: italic;")
        cloud_layout.addRow(info_label)

        layout.addWidget(cloud_group)
        layout.addStretch()
        return w

    def _create_apps_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        desc = QLabel("Registered applications that FRIDAY can launch:")
        layout.addWidget(desc)

        self.apps_table = QTableWidget()
        self.apps_table.setColumnCount(2)
        self.apps_table.setHorizontalHeaderLabels(["App Name", "Command / Path"])
        self.apps_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._populate_apps_table()
        layout.addWidget(self.apps_table)

        # Add row controls
        add_layout = QHBoxLayout()
        self.new_app_name = QLineEdit()
        self.new_app_name.setPlaceholderText("App alias (e.g. spotify)")
        self.new_app_cmd = QLineEdit()
        self.new_app_cmd.setPlaceholderText("Executable command (e.g. spotify.exe)")
        add_btn = QPushButton("Add App")
        add_btn.clicked.connect(self._add_app)

        del_btn = QPushButton("Remove Selected")
        del_btn.clicked.connect(self._remove_selected_app)

        add_layout.addWidget(self.new_app_name)
        add_layout.addWidget(self.new_app_cmd)
        add_layout.addWidget(add_btn)
        add_layout.addWidget(del_btn)
        layout.addLayout(add_layout)

        return w

    def _populate_apps_table(self):
        apps = self.settings.get("applications", {})
        self.apps_table.setRowCount(len(apps))
        for row, (name, cmd) in enumerate(apps.items()):
            self.apps_table.setItem(row, 0, QTableWidgetItem(name))
            self.apps_table.setItem(row, 1, QTableWidgetItem(cmd))

    def _add_app(self):
        name = self.new_app_name.text().strip().lower()
        cmd = self.new_app_cmd.text().strip()
        if name and cmd:
            self.settings.register_application(name, cmd)
            self._populate_apps_table()
            self.new_app_name.clear()
            self.new_app_cmd.clear()

    def _remove_selected_app(self):
        selected = self.apps_table.currentRow()
        if selected >= 0:
            name_item = self.apps_table.item(selected, 0)
            if name_item:
                self.settings.remove_application(name_item.text())
                self._populate_apps_table()

    def _create_security_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(14)

        sec_group = QGroupBox("Action Authorization Policies")
        sec_layout = QFormLayout(sec_group)

        self.confirm_moderate_cb = QCheckBox("Require confirmation for Moderate-Risk actions (moving files, typing in apps)")
        self.confirm_moderate_cb.setChecked(self.settings.get("system.require_confirmation_for_moderate", True))
        sec_layout.addRow(self.confirm_moderate_cb)

        self.confirm_high_cb = QCheckBox("Require confirmation for High-Risk actions (system modifications, deletions)")
        self.confirm_high_cb.setChecked(self.settings.get("system.require_confirmation_for_high", True))
        sec_layout.addRow(self.confirm_high_cb)

        layout.addWidget(sec_group)
        layout.addStretch()
        return w

    def _create_memory_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Stored Personal Preferences & History:"))
        clear_btn = QPushButton("Clear All Memory")
        clear_btn.setStyleSheet(f"color: {COLOR_NEON_RED}; border-color: {COLOR_NEON_RED};")
        clear_btn.clicked.connect(self._clear_memory)
        header_layout.addStretch()
        header_layout.addWidget(clear_btn)
        layout.addLayout(header_layout)

        self.memory_table = QTableWidget()
        self.memory_table.setColumnCount(3)
        self.memory_table.setHorizontalHeaderLabels(["Category", "Key", "Value"])
        self.memory_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._populate_memory_table()
        layout.addWidget(self.memory_table)

        return w

    def _populate_memory_table(self):
        items = self.memory.list_all_memories()
        self.memory_table.setRowCount(len(items))
        for row, item in enumerate(items):
            self.memory_table.setItem(row, 0, QTableWidgetItem(item["category"]))
            self.memory_table.setItem(row, 1, QTableWidgetItem(item["key"]))
            self.memory_table.setItem(row, 2, QTableWidgetItem(str(item["value"])))

    def _clear_memory(self):
        reply = QMessageBox.question(
            self,
            "Clear Memory",
            "Are you sure you want to delete all stored memories and history?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.memory.clear_all()
            self._populate_memory_table()

    def _save_settings(self):
        # Voice
        self.settings.set("voice.enabled", self.enable_voice_cb.isChecked(), auto_save=False)
        self.settings.set("voice.voice_id", self.voice_combo.currentData(), auto_save=False)
        self.settings.set("voice.rate", self.rate_slider.value(), auto_save=False)
        self.settings.set("voice.volume", self.volume_slider.value() / 100.0, auto_save=False)

        # Wake Word
        self.settings.set("wake_word.phrase", self.wake_phrase_edit.text().strip().lower(), auto_save=False)
        self.settings.set("wake_word.input_device_index", self.mic_combo.currentData(), auto_save=False)
        self.settings.set("system.auto_listen_on_startup", self.auto_listen_cb.isChecked(), auto_save=False)

        # AI
        self.settings.set("ai.enable_cloud_ai", self.enable_cloud_cb.isChecked(), auto_save=False)
        self.settings.set("ai.provider", self.provider_combo.currentText(), auto_save=False)
        self.settings.set("ai.gemini_api_key", self.gemini_key_edit.text().strip(), auto_save=False)
        self.settings.set("ai.enable_vision", self.enable_vision_cb.isChecked(), auto_save=False)

        # Security
        self.settings.set("system.require_confirmation_for_moderate", self.confirm_moderate_cb.isChecked(), auto_save=False)
        self.settings.set("system.require_confirmation_for_high", self.confirm_high_cb.isChecked(), auto_save=False)

        self.settings.save()
        self.accept()
