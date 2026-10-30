"""
Global System-Wide Hotkey Listener for FRIDAY AI.
Allows the user to trigger FRIDAY from ANY active website, browser tab, or application.
Default hotkey: Ctrl + Alt + F (fallback: Ctrl + Shift + F).
"""

import ctypes
from ctypes import wintypes
import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger("Friday.Hotkey")

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312


class GlobalHotkeyListener:
    """
    Listens for global hotkeys across the entire Windows operating system.
    Runs on a low-overhead background thread using Windows RegisterHotKey.
    Supported shortcuts:
      - Ctrl + Alt + F (fallback: Ctrl + Shift + F) -> Toggle Overlay / Show FRIDAY
      - Ctrl + Alt + M (fallback: Ctrl + Shift + M) -> Mute / Unmute Microphone
      - Ctrl + Alt + X (fallback: Ctrl + Shift + X) -> Emergency Stop / Cancel Task
    """

    def __init__(
        self,
        on_hotkey_triggered: Optional[Callable[[], None]] = None,
        on_toggle_overlay: Optional[Callable[[], None]] = None,
        on_toggle_mic: Optional[Callable[[], None]] = None,
        on_emergency_stop: Optional[Callable[[], None]] = None,
    ):
        self.on_toggle_overlay = on_toggle_overlay or on_hotkey_triggered
        self.on_toggle_mic = on_toggle_mic
        self.on_emergency_stop = on_emergency_stop

        self._running = False
        self._thread: Optional[threading.Thread] = None

        self._id_overlay = 9101
        self._id_mic = 9102
        self._id_stop = 9103

    def start(self):
        """Starts the background hotkey listener."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="FridayGlobalHotkey")
        self._thread.start()

    def stop(self):
        """Stops the hotkey listener."""
        self._running = False

    def _register(self, user32, hotkey_id: int, mod: int, vk: int, fallback_mod: int) -> bool:
        reg = user32.RegisterHotKey(None, hotkey_id, mod | MOD_NOREPEAT, vk)
        if not reg and fallback_mod:
            reg = user32.RegisterHotKey(None, hotkey_id, fallback_mod | MOD_NOREPEAT, vk)
        return bool(reg)

    def _loop(self):
        user32 = ctypes.windll.user32

        # 1. Overlay toggle: Ctrl+Alt+F (0x46), fallback Ctrl+Shift+F
        reg_overlay = self._register(user32, self._id_overlay, MOD_CONTROL | MOD_ALT, 0x46, MOD_CONTROL | MOD_SHIFT)
        # 2. Mic mute toggle: Ctrl+Alt+M (0x4D), fallback Ctrl+Shift+M
        reg_mic = self._register(user32, self._id_mic, MOD_CONTROL | MOD_ALT, 0x4D, MOD_CONTROL | MOD_SHIFT)
        # 3. Emergency stop: Ctrl+Alt+X (0x58), fallback Ctrl+Shift+X
        reg_stop = self._register(user32, self._id_stop, MOD_CONTROL | MOD_ALT, 0x58, MOD_CONTROL | MOD_SHIFT)

        logger.info(
            f"[GlobalHotkeyListener] Hotkeys registered: Overlay={reg_overlay}, Mic={reg_mic}, Stop={reg_stop}"
        )

        msg = wintypes.MSG()
        while self._running:
            if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):  # PM_REMOVE = 1
                if msg.message == WM_HOTKEY:
                    hid = msg.wParam
                    try:
                        if hid == self._id_overlay and self.on_toggle_overlay:
                            self.on_toggle_overlay()
                        elif hid == self._id_mic and self.on_toggle_mic:
                            self.on_toggle_mic()
                        elif hid == self._id_stop and self.on_emergency_stop:
                            self.on_emergency_stop()
                    except Exception as e:
                        logger.error(f"[GlobalHotkeyListener] Error handling hotkey {hid}: {e}")
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            time.sleep(0.02)

        for hid in (self._id_overlay, self._id_mic, self._id_stop):
            try:
                user32.UnregisterHotKey(None, hid)
            except Exception:
                pass

