"""
Desktop Automation & Screen Control for Windows 11.
Controls keyboard, typing, safe math evaluations, and screenshot capture.
"""

import ast
import ctypes
import math
import operator
import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple
import pyautogui
from PIL import Image

from config.constants import DATA_DIR

# Safe math operators map
_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_ALLOWED_FUNCTIONS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "abs": abs,
    "round": round,
    "pi": math.pi,
    "e": math.e,
}


def _safe_eval_node(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Non-numeric literal in expression")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPERATORS:
            raise ValueError(f"Operator {op_type.__name__} not supported")
        left = _safe_eval_node(node.left)
        right = _safe_eval_node(node.right)
        return _ALLOWED_OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPERATORS:
            raise ValueError(f"Operator {op_type.__name__} not supported")
        operand = _safe_eval_node(node.operand)
        return _ALLOWED_OPERATORS[op_type](operand)
    elif isinstance(node, ast.Name):
        if node.id in _ALLOWED_FUNCTIONS:
            return _ALLOWED_FUNCTIONS[node.id]
        raise ValueError(f"Unknown variable: {node.id}")
    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in _ALLOWED_FUNCTIONS:
            func = _ALLOWED_FUNCTIONS[node.func.id]
            args = [_safe_eval_node(arg) for arg in node.args]
            return func(*args)
        raise ValueError("Unsupported function call")
    else:
        raise ValueError(f"Unsupported syntax: {type(node).__name__}")


class DesktopController:
    def __init__(self):
        # Configure PyAutoGUI safety pauses and disable failsafe to allow typing/hotkeys regardless of mouse position
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.1

    def calculate(self, expression: str) -> Tuple[bool, str]:
        """
        Safely evaluates mathematical expressions without using eval().
        Example: '250 * 48' or 'sqrt(144) + 10'
        """
        expr_clean = expression.replace("multiplied by", "*").replace("times", "*")
        expr_clean = expr_clean.replace("divided by", "/").replace("plus", "+").replace("minus", "-")
        expr_clean = expr_clean.replace("x", "*").replace("^", "**")
        
        try:
            tree = ast.parse(expr_clean.strip(), mode="eval")
            result = _safe_eval_node(tree.body)
            # Format nicely
            if isinstance(result, float) and result.is_integer():
                result = int(result)
            return True, f"{expression.strip()} = {result}"
        except Exception as e:
            return False, f"Could not calculate expression: {e}"

    def type_text(self, text: str, interval: float = 0.02) -> Tuple[bool, str]:
        """
        Types or pastes text into the currently active window.
        Uses clipboard paste (Ctrl+V) via Win32 keybd_event for instant, lossless multi-line text insertion
        (preserving line breaks and special characters), with graceful fallback to pyautogui.
        """
        try:
            # Yield to ensure target window is active and focused
            time.sleep(0.3)

            # 1. Primary method: Clipboard paste via Win32 keybd_event (instant, 100% reliable)
            try:
                import pyperclip
                import ctypes
                pyperclip.copy(text)
                time.sleep(0.08)
                VK_CONTROL = 0x11
                VK_V = 0x56
                KEYEVENTF_KEYUP = 0x0002
                user32 = ctypes.windll.user32
                user32.keybd_event(VK_CONTROL, 0, 0, 0)
                user32.keybd_event(VK_V, 0, 0, 0)
                user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
                user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
                return True, "Typed text into active application."
            except Exception as clip_err:
                logger.debug(f"[DesktopController] Win32 paste fallback: {clip_err}")

            # 2. PyAutoGUI paste fallback
            try:
                pyautogui.FAILSAFE = False
                pyautogui.hotkey("ctrl", "v")
                return True, "Typed text into active application."
            except Exception:
                pass

            # 3. Direct keyboard typing fallback
            pyautogui.write(text, interval=interval)
            return True, "Typed text into active application."
        except Exception as e:
            logger.error(f"[DesktopController] Failed to type text: {e}")
            return False, f"Failed to type text: {e}"

    def media_control(self, command: str) -> Tuple[bool, str]:
        """
        Executes Windows multimedia keyboard actions (play/pause, volume, mute, next/prev).
        Works globally for YouTube in browser, media players, Spotify, etc.
        """
        cmd_clean = (command or "").strip().lower()
        key_map = {
            "play_pause": "playpause",
            "pause": "playpause",
            "play": "playpause",
            "resume": "playpause",
            "volume_up": "volumeup",
            "vol_up": "volumeup",
            "volume_down": "volumedown",
            "vol_down": "volumedown",
            "mute": "volumemute",
            "unmute": "volumemute",
            "next": "nexttrack",
            "next_track": "nexttrack",
            "prev": "prevtrack",
            "previous": "prevtrack",
            "prev_track": "prevtrack",
        }
        key = key_map.get(cmd_clean)
        if not key:
            return False, f"Unknown media command: {command}"

        try:
            # If volume up or down, press 3 times for a noticeable step
            if key in ("volumeup", "volumedown"):
                for _ in range(3):
                    pyautogui.press(key)
            else:
                pyautogui.press(key)

            action_names = {
                "playpause": "Toggled Play/Pause for media playback",
                "volumeup": "Volume increased",
                "volumedown": "Volume decreased",
                "volumemute": "Toggled Audio Mute",
                "nexttrack": "Next track / video",
                "prevtrack": "Previous track / video",
            }
            desc = action_names.get(key, "Media command executed")
            return True, desc
        except Exception as e:
            return False, f"Failed to execute media command: {e}"

    def press_hotkey(self, *keys) -> Tuple[bool, str]:
        """Presses a combination of keys, e.g. ('win', 'd')."""
        try:
            pyautogui.hotkey(*keys)
            return True, f"Pressed hotkey {' + '.join(keys)}."
        except Exception as e:
            return False, f"Failed to press hotkey: {e}"

    def capture_screenshot(self, filename: Optional[str] = None) -> Tuple[bool, Path]:
        """Captures a screenshot and saves it in data/screenshots."""
        screenshots_dir = DATA_DIR / "screenshots"
        screenshots_dir.mkdir(exist_ok=True)
        if not filename:
            filename = f"screen_{int(time.time())}.png"
        file_path = screenshots_dir / filename
        try:
            img = pyautogui.screenshot()
            img.save(file_path)
            return True, file_path
        except Exception as e:
            return False, Path("")

    def get_active_window_title(self) -> str:
        """Returns the title of the active window."""
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            if win and win.title:
                return win.title
        except Exception:
            pass
        return "Unknown"

    def power_control(self, command: str, delay_seconds: int = 0) -> Tuple[bool, str]:
        """
        Executes Windows power management commands.

        Supported commands:
          - shutdown       → Powers off the system
          - restart        → Reboots the system
          - sleep          → Suspends to RAM (S3 sleep / Modern Standby)
          - hibernate      → Suspends to disk (S4 hibernate)
          - lock           → Locks the workstation (no power change)
          - cancel_shutdown → Cancels a pending shutdown or restart

        :param command: One of the supported power command strings.
        :param delay_seconds: Seconds before shutdown/restart executes (0 = immediate).
        :returns: Tuple of (success: bool, message: str)
        """
        import threading
        cmd_clean = (command or "").strip().lower()

        try:
            if cmd_clean == "shutdown":
                # Ensure at least 3 seconds delay so Friday has time to say goodbye
                delay = max(3, int(delay_seconds)) if delay_seconds > 0 else 3
                subprocess.Popen(f"shutdown /s /t {delay}", shell=True)
                if delay_seconds > 0:
                    return True, f"System will shut down in {delay} seconds. Say 'cancel shutdown' to abort."
                return True, "Initiating system shutdown. Goodbye, Sir."

            elif cmd_clean == "restart":
                delay = max(3, int(delay_seconds)) if delay_seconds > 0 else 3
                subprocess.Popen(f"shutdown /r /t {delay}", shell=True)
                if delay_seconds > 0:
                    return True, f"System will restart in {delay} seconds. Say 'cancel shutdown' to abort."
                return True, "Restarting the system now. I will be right back, Sir."

            elif cmd_clean == "sleep":
                def _trigger_sleep():
                    # Wait 1.5 seconds for Friday to complete speaking response
                    time.sleep(1.5)
                    try:
                        # SetSuspendState(bHibernate=False, bForce=True, bWakeupEventsDisabled=False)
                        res = ctypes.windll.powrprof.SetSuspendState(0, 1, 0)
                        if not res:
                            # PowerShell fallback
                            subprocess.run(
                                [
                                    "powershell.exe",
                                    "-NoProfile",
                                    "-NonInteractive",
                                    "-Command",
                                    "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState([System.Windows.Forms.PowerState]::Suspend, $false, $false)",
                                ],
                                capture_output=True,
                                timeout=5,
                            )
                    except Exception as ex:
                        print(f"[DesktopController] Sleep trigger error: {ex}")

                threading.Thread(target=_trigger_sleep, daemon=True).start()
                return True, "Putting the system to sleep. Good night, Sir."

            elif cmd_clean == "hibernate":
                def _trigger_hibernate():
                    time.sleep(1.5)
                    os.system("shutdown /h")

                threading.Thread(target=_trigger_hibernate, daemon=True).start()
                return True, "Hibernating the system. Your session will be saved, Sir."

            elif cmd_clean == "lock":
                def _trigger_lock():
                    time.sleep(0.8)
                    ctypes.windll.user32.LockWorkStation()

                threading.Thread(target=_trigger_lock, daemon=True).start()
                return True, "Workstation locked. See you soon, Sir."

            elif cmd_clean == "cancel_shutdown":
                os.system("shutdown /a")
                return True, "Pending shutdown or restart has been cancelled."

            else:
                return False, f"Unknown power command: '{command}'. Supported: shutdown, restart, sleep, hibernate, lock, cancel_shutdown."

        except Exception as e:
            return False, f"Power control failed: {str(e)}"
