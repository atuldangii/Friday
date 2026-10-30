"""
Settings and Configuration Manager for FRIDAY AI.
Loads settings from .env and a persistent JSON settings file.
"""

import json
import os
import threading
from typing import Any, Dict
from dotenv import load_dotenv

from .constants import SETTINGS_FILE, BASE_DIR

# Load .env file if available
load_dotenv(BASE_DIR / ".env")

DEFAULT_SETTINGS = {
    "user_name": os.getenv("FRIDAY_USER_NAME", "Sir"),
    "voice": {
        "rate": int(os.getenv("FRIDAY_VOICE_RATE", "168")),
        "volume": float(os.getenv("FRIDAY_VOICE_VOLUME", "1.0")),
        "voice_id": "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech\\Voices\\Tokens\\TTS_MS_EN-US_DAVID_11.0",
        "enabled": True,
    },
    "wake_word": {
        "enabled": True,
        "phrase": os.getenv("FRIDAY_WAKE_WORD", "hey friday").lower(),
        "sensitivity": 0.5,
        "input_device_index": -1,  # Default system mic
    },
    "ai": {
        "enable_cloud_ai": os.getenv("FRIDAY_ENABLE_CLOUD_AI", "false").lower() in ("1", "true", "yes"),
        "provider": "gemini",
        "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
        "gemini_model": "gemini-2.5-flash",
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "openai_base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "openai_model": "gpt-4o",
        "enable_vision": os.getenv("FRIDAY_ENABLE_VISION", "true").lower() in ("1", "true", "yes"),
    },
    "applications": {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "file explorer": "explorer.exe",
        "explorer": "explorer.exe",
        "settings": "start ms-settings:",
        "task manager": "taskmgr.exe",
        "paint": "mspaint.exe",
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "edge": "msedge.exe",
        "microsoft edge": "msedge.exe",
        "cmd": "cmd.exe",
        "command prompt": "cmd.exe",
        "powershell": "powershell.exe",
    },
    "system": {
        "minimize_to_tray": True,
        "auto_listen_on_startup": True,
        "play_chimes": True,
        "require_confirmation_for_moderate": True,
        "require_confirmation_for_high": True,
    },
}


class SettingsManager:
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SettingsManager, cls).__new__(cls)
                cls._instance._init_settings()
            return cls._instance

    def _init_settings(self):
        self._settings: Dict[str, Any] = json.loads(json.dumps(DEFAULT_SETTINGS))
        self._load()

    def _load(self):
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self._deep_update(self._settings, saved)
            except Exception as e:
                print(f"[SettingsManager] Error loading settings file: {e}")

    def _deep_update(self, target: dict, source: dict):
        for k, v in source.items():
            if isinstance(v, dict) and k in target and isinstance(target[k], dict):
                self._deep_update(target[k], v)
            else:
                target[k] = v

    def save(self):
        with self._lock:
            try:
                with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                    json.dump(self._settings, f, indent=4)
            except Exception as e:
                print(f"[SettingsManager] Error saving settings: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        keys = key_path.split(".")
        val = self._settings
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def set(self, key_path: str, value: Any, auto_save: bool = True):
        keys = key_path.split(".")
        val = self._settings
        for k in keys[:-1]:
            if k not in val or not isinstance(val[k], dict):
                val[k] = {}
            val = val[k]
        val[keys[-1]] = value
        if auto_save:
            self.save()

    def get_all(self) -> Dict[str, Any]:
        return self._settings

    def register_application(self, app_name: str, app_command: str):
        apps = self._settings.get("applications", {})
        apps[app_name.lower().strip()] = app_command.strip()
        self.set("applications", apps)

    def remove_application(self, app_name: str):
        apps = self._settings.get("applications", {})
        key = app_name.lower().strip()
        if key in apps:
            del apps[key]
            self.set("applications", apps)
