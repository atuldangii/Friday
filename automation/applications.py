"""
Reliable Application Control & Verification for Windows 11.
Provides centralized executable resolution, safe process execution,
window verification, diagnostic audit logging, and honest response formatting.
"""

from dataclasses import dataclass
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Dict, List, Optional, Tuple
import psutil

from config.constants import AUDIT_LOG_FILE
from config.settings import SettingsManager

logger = logging.getLogger("Friday.Applications")

# Windows App Paths registry keys
APP_PATHS_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"

# Canonical registry of known applications: (canonical_id, display_name, [executable_names])
APP_CANONICAL_MAP: Dict[str, Tuple[str, str, List[str]]] = {
    "edge": ("msedge", "Microsoft Edge", ["msedge.exe", "msedge"]),
    "microsoft edge": ("msedge", "Microsoft Edge", ["msedge.exe", "msedge"]),
    "msedge": ("msedge", "Microsoft Edge", ["msedge.exe", "msedge"]),
    "notepad": ("notepad", "Notepad", ["notepad.exe", "notepad"]),
    "calculator": ("calc", "Calculator", ["calc.exe", "calc"]),
    "calc": ("calc", "Calculator", ["calc.exe", "calc"]),
    "file explorer": ("explorer", "File Explorer", ["explorer.exe", "explorer"]),
    "explorer": ("explorer", "File Explorer", ["explorer.exe", "explorer"]),
    "windows explorer": ("explorer", "File Explorer", ["explorer.exe", "explorer"]),
    "task manager": ("taskmgr", "Task Manager", ["taskmgr.exe", "taskmgr"]),
    "taskmgr": ("taskmgr", "Task Manager", ["taskmgr.exe", "taskmgr"]),
    "paint": ("mspaint", "Paint", ["mspaint.exe", "mspaint"]),
    "mspaint": ("mspaint", "Paint", ["mspaint.exe", "mspaint"]),
    "chrome": ("chrome", "Google Chrome", ["chrome.exe", "chrome"]),
    "google chrome": ("chrome", "Google Chrome", ["chrome.exe", "chrome"]),
    "settings": ("settings", "Settings", ["ms-settings:"]),
    "windows settings": ("settings", "Settings", ["ms-settings:"]),
    "cmd": ("cmd", "Command Prompt", ["cmd.exe", "cmd"]),
    "command prompt": ("cmd", "Command Prompt", ["cmd.exe", "cmd"]),
    "powershell": ("powershell", "PowerShell", ["powershell.exe", "powershell"]),
}


@dataclass
class LaunchResult:
    """Detailed result of an application launch attempt."""
    success: bool
    application: str
    display_name: str
    process_id: Optional[int] = None
    error: Optional[str] = None
    details: str = ""
    window_verified: bool = False
    resolved_path: Optional[str] = None
    launch_method: str = ""
    message: str = ""

    def __iter__(self):
        """Allows unpacking as (success, message) for backward compatibility."""
        return iter((self.success, self.message))


def format_launch_response(result: LaunchResult) -> str:
    """
    Formats the user-facing response strictly adhering to verification results:
    - If Edge/Notepad launches and window verified:
      '[Application] is open.'
    - If application cannot be found:
      'I couldn't find [Application] on your computer. Please check whether it is installed.'
    - If Windows rejects the launch:
      'I couldn't open [Application]. Here is the error: [useful error message].'
    - If launch request succeeds but visible window cannot be verified:
      'The launch request succeeded, but I couldn't confirm that the window appeared.'
    """
    name = result.display_name or result.application
    if result.success:
        if result.window_verified:
            return f"{name} is open."
        else:
            return "The launch request succeeded, but I couldn't confirm that the window appeared."
    else:
        err = (result.error or "").strip()
        if not result.resolved_path or "not found" in err.lower() or "not registered" in err.lower():
            return f"I couldn't find {name} on your computer. Please check whether it is installed."
        else:
            return f"I couldn't open {name}. Here is the error: {err}."


class ApplicationController:
    """Centralized Windows Application Launcher and Verifier."""

    def __init__(self):
        self.settings = SettingsManager()

    def get_registered_apps(self) -> Dict[str, str]:
        return self.settings.get("applications", {})

    def resolve_application(self, app_name: str) -> Tuple[Optional[str], str, str, str]:
        """
        Resolves an application name to a verified executable path or protocol URI.
        Returns: (resolved_target, canonical_id, display_name, target_type)
        where target_type is 'exe', 'uri', or 'not_found'.
        """
        clean_name = app_name.strip().rstrip(".,!?;").lower()

        # Check canonical map first
        if clean_name in APP_CANONICAL_MAP:
            canonical_id, display_name, candidates = APP_CANONICAL_MAP[clean_name]
        else:
            # Fuzzy check against canonical map keys
            canonical_id = clean_name
            display_name = app_name.strip().title()
            candidates = [clean_name, f"{clean_name}.exe"]
            for k, (cid, dname, cands) in APP_CANONICAL_MAP.items():
                if k == clean_name or k in clean_name or clean_name in k:
                    canonical_id = cid
                    display_name = dname
                    candidates = cands
                    break

        # 1. Check user-configured override in settings
        reg_apps = self.get_registered_apps()
        configured_path = reg_apps.get(clean_name) or reg_apps.get(canonical_id)
        if configured_path:
            configured_path = configured_path.strip()
            if configured_path.startswith("start "):
                configured_path = configured_path[6:].strip()
            if configured_path.endswith(":"):
                return configured_path, canonical_id, display_name, "uri"
            expanded = os.path.expandvars(configured_path)
            if os.path.exists(expanded) and os.path.isfile(expanded):
                return expanded, canonical_id, display_name, "exe"

        # 2. Check protocol URIs (e.g. Settings)
        if canonical_id in ("settings", "ms-settings") or clean_name in ("settings", "ms-settings"):
            return "ms-settings:", canonical_id, "Settings", "uri"

        # 3. Check known Windows standard installation paths first (guarantees native system binaries)
        standard_path = self._query_standard_paths(canonical_id)
        if standard_path and os.path.exists(standard_path) and os.path.isfile(standard_path):
            return standard_path, canonical_id, display_name, "exe"

        # 4. Query Windows App Paths Registry (HKCU and HKLM), skipping restricted WindowsApps paths
        reg_target = self._query_app_paths_registry(candidates)
        if reg_target and os.path.exists(reg_target) and os.path.isfile(reg_target):
            # Prefer native executables over restricted WindowsApps packaged binaries
            if "windowsapps" not in reg_target.lower():
                return reg_target, canonical_id, display_name, "exe"

        # 5. Check system PATH via shutil.which
        for cand in candidates:
            w_path = shutil.which(cand)
            if w_path and os.path.exists(w_path) and os.path.isfile(w_path):
                return w_path, canonical_id, display_name, "exe"

        return None, canonical_id, display_name, "not_found"

    def _query_app_paths_registry(self, candidates: List[str]) -> Optional[str]:
        """Queries Windows App Paths in HKCU and HKLM."""
        try:
            import winreg
        except ImportError:
            return None

        # Build list of executable names to check
        exe_names = []
        for c in candidates:
            if not c.endswith(":"):
                exe_name = c if c.lower().endswith(".exe") else f"{c}.exe"
                if exe_name not in exe_names:
                    exe_names.append(exe_name)

        for exe_name in exe_names:
            for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                key_path = f"{APP_PATHS_KEY}\\{exe_name}"
                try:
                    with winreg.OpenKey(root, key_path) as k:
                        val, _ = winreg.QueryValueEx(k, "")
                        if val:
                            expanded = os.path.expandvars(val.strip().strip('"'))
                            if os.path.exists(expanded) and os.path.isfile(expanded):
                                return expanded
                except FileNotFoundError:
                    continue
                except Exception as e:
                    logger.debug(f"Error querying registry for {exe_name}: {e}")
        return None

    def _query_standard_paths(self, canonical_id: str) -> Optional[str]:
        """Checks well-known Windows locations for specific applications."""
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local_app_data = os.environ.get("LOCALAPPDATA", "")

        paths_to_check: List[Path] = []

        if canonical_id == "msedge":
            paths_to_check.extend([
                Path(prog_files_x86) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                Path(prog_files) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                Path(local_app_data) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            ])
        elif canonical_id == "chrome":
            paths_to_check.extend([
                Path(prog_files) / "Google" / "Chrome" / "Application" / "chrome.exe",
                Path(prog_files_x86) / "Google" / "Chrome" / "Application" / "chrome.exe",
                Path(local_app_data) / "Google" / "Chrome" / "Application" / "chrome.exe",
            ])
        elif canonical_id == "notepad":
            paths_to_check.extend([
                Path(system_root) / "System32" / "notepad.exe",
                Path(system_root) / "notepad.exe",
                Path(local_app_data) / "Microsoft" / "WindowsApps" / "notepad.exe",
            ])
        elif canonical_id == "calc":
            paths_to_check.extend([
                Path(system_root) / "System32" / "calc.exe",
                Path(local_app_data) / "Microsoft" / "WindowsApps" / "calc.exe",
            ])
        elif canonical_id == "explorer":
            paths_to_check.extend([
                Path(system_root) / "explorer.exe",
            ])
        elif canonical_id == "taskmgr":
            paths_to_check.extend([
                Path(system_root) / "System32" / "taskmgr.exe",
            ])
        elif canonical_id == "mspaint":
            paths_to_check.extend([
                Path(system_root) / "System32" / "mspaint.exe",
                Path(local_app_data) / "Microsoft" / "WindowsApps" / "mspaint.exe",
            ])
        elif canonical_id == "cmd":
            paths_to_check.extend([
                Path(system_root) / "System32" / "cmd.exe",
            ])
        elif canonical_id == "powershell":
            paths_to_check.extend([
                Path(system_root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe",
            ])

        for p in paths_to_check:
            if p.exists() and p.is_file():
                return str(p)

        return None

    def find_running_app_window(self, canonical_id: str, display_name: str) -> Optional[int]:
        """Finds HWND of an already running instance of the application if visible."""
        try:
            import win32gui
            keywords = {canonical_id.lower(), display_name.lower()}
            if canonical_id in ("edge", "msedge"):
                keywords.update(["edge", "microsoft edge"])
            elif canonical_id == "notepad":
                keywords.update(["notepad", "untitled - notepad"])
            elif canonical_id == "calc":
                keywords.update(["calculator"])
            elif canonical_id == "chrome":
                keywords.update(["chrome", "google chrome"])
            elif canonical_id == "explorer":
                keywords.update(["file explorer"])

            found_hwnd = None
            def enum_cb(hwnd, _):
                nonlocal found_hwnd
                if found_hwnd:
                    return
                try:
                    if not win32gui.IsWindowVisible(hwnd):
                        return
                    title = (win32gui.GetWindowText(hwnd) or "").lower().replace("\u200b", "").strip()
                    if title:
                        for kw in keywords:
                            if kw in title:
                                if win32gui.GetParent(hwnd) == 0:
                                    found_hwnd = hwnd
                                    return
                except Exception:
                    pass

            win32gui.EnumWindows(enum_cb, None)
            return found_hwnd
        except Exception:
            return None

    def focus_window(self, hwnd: int) -> bool:
        """Restores and brings a window to the foreground."""
        try:
            import win32gui
            import win32con
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception:
            return False

    def launch_app(
        self,
        app_name: str,
        arguments: Optional[List[str]] = None,
        user_command: Optional[str] = None,
    ) -> LaunchResult:
        """
        Reliably launches an application without unsafe shell execution,
        verifies process startup and visible window presence, records diagnostic logs,
        and returns a validated LaunchResult.
        Reuses existing running instances when safe to avoid duplicate windows.
        """
        raw_cmd = user_command or f"open {app_name}"
        resolved_target, canonical_id, display_name, target_type = self.resolve_application(app_name)

        # 1. Handle unresolvable applications
        if target_type == "not_found" or not resolved_target:
            result = LaunchResult(
                success=False,
                application=canonical_id,
                display_name=display_name,
                error="Executable not found",
                details=f"Could not locate an executable for '{display_name}' on this computer.",
                resolved_path=None,
                launch_method="none",
                window_verified=False,
            )
            result.message = format_launch_response(result)
            self._log_diagnostic(raw_cmd, result)
            return result

        # 1b. Check if already running (reuse running window)
        if not arguments:
            existing_hwnd = self.find_running_app_window(canonical_id, display_name)
            if existing_hwnd:
                self.focus_window(existing_hwnd)
                result = LaunchResult(
                    success=True,
                    application=canonical_id,
                    display_name=display_name,
                    process_id=None,
                    error=None,
                    details=f"Application already running; brought window (HWND {existing_hwnd}) to foreground.",
                    window_verified=True,
                    resolved_path=resolved_target,
                    launch_method="foreground_reuse",
                )
                result.message = format_launch_response(result)
                self._log_diagnostic(raw_cmd, result)
                return result

        # 2. Handle protocol URIs (e.g. Settings)
        if target_type == "uri":
            try:
                os.startfile(resolved_target)
                window_verified = self.verify_window(canonical_id, display_name, timeout=1.5)
                result = LaunchResult(
                    success=True,
                    application=canonical_id,
                    display_name=display_name,
                    process_id=None,
                    error=None,
                    details=f"Launched protocol URI '{resolved_target}'",
                    window_verified=window_verified,
                    resolved_path=resolved_target,
                    launch_method="os.startfile",
                )
                result.message = format_launch_response(result)
                self._log_diagnostic(raw_cmd, result)
                return result
            except Exception as e:
                result = LaunchResult(
                    success=False,
                    application=canonical_id,
                    display_name=display_name,
                    process_id=None,
                    error=str(e),
                    details=f"Failed to launch URI '{resolved_target}': {e}",
                    window_verified=False,
                    resolved_path=resolved_target,
                    launch_method="os.startfile",
                )
                result.message = format_launch_response(result)
                self._log_diagnostic(raw_cmd, result)
                return result

        # 3. Handle Executable launch via subprocess.Popen (shell=False)
        cmd_args = [resolved_target]
        if arguments:
            cmd_args.extend(arguments)

        try:
            # Safe launch without shell=True
            proc = subprocess.Popen(
                cmd_args,
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )

            # Brief pause to verify process didn't terminate immediately with an error
            time.sleep(0.15)
            poll_code = proc.poll()
            if poll_code is not None and poll_code != 0:
                err_text = ""
                try:
                    _, stderr_data = proc.communicate(timeout=0.2)
                    err_text = stderr_data.decode("utf-8", errors="replace").strip()
                except Exception:
                    pass
                result = LaunchResult(
                    success=False,
                    application=canonical_id,
                    display_name=display_name,
                    process_id=proc.pid,
                    error=err_text or f"Process exited immediately with code {poll_code}",
                    details=f"Process exited prematurely: returncode={poll_code}",
                    window_verified=False,
                    resolved_path=resolved_target,
                    launch_method="subprocess.Popen",
                )
                result.message = format_launch_response(result)
                self._log_diagnostic(raw_cmd, result)
                return result

            # Verify visible window presence
            window_verified = self.verify_window(
                canonical_id=canonical_id,
                display_name=display_name,
                pid=proc.pid,
                timeout=2.0,
            )

            result = LaunchResult(
                success=True,
                application=canonical_id,
                display_name=display_name,
                process_id=proc.pid,
                error=None,
                details=f"Process started (PID: {proc.pid}) from '{resolved_target}'",
                window_verified=window_verified,
                resolved_path=resolved_target,
                launch_method="subprocess.Popen",
            )
            result.message = format_launch_response(result)
            self._log_diagnostic(raw_cmd, result)
            return result

        except Exception as e:
            result = LaunchResult(
                success=False,
                application=canonical_id,
                display_name=display_name,
                process_id=None,
                error=str(e),
                details=f"Subprocess launch exception: {e}",
                window_verified=False,
                resolved_path=resolved_target,
                launch_method="subprocess.Popen",
            )
            result.message = format_launch_response(result)
            self._log_diagnostic(raw_cmd, result)
            return result

    def verify_window(
        self,
        canonical_id: str,
        display_name: str,
        pid: Optional[int] = None,
        timeout: float = 1.5,
        poll_interval: float = 0.04,
    ) -> bool:
        """
        Polls for a visible top-level application window using Win32 API and pygetwindow.
        Returns True if a matching visible window is confirmed, False otherwise.
        """
        # Collect candidate search titles
        keywords = {canonical_id.lower(), display_name.lower()}
        if canonical_id == "msedge":
            keywords.update(["edge", "microsoft edge", "microsoft\u200bedge"])
        elif canonical_id == "notepad":
            keywords.update(["notepad", "untitled - notepad"])
        elif canonical_id == "calc":
            keywords.update(["calculator"])
        elif canonical_id == "taskmgr":
            keywords.update(["task manager"])
        elif canonical_id == "mspaint":
            keywords.update(["paint"])
        elif canonical_id == "explorer":
            keywords.update(["file explorer"])
        elif canonical_id == "chrome":
            keywords.update(["chrome", "google chrome"])
        elif canonical_id == "settings":
            keywords.update(["settings"])

        start_time = time.time()
        while time.time() - start_time < timeout:
            # 1. Try win32gui window search
            if self._check_win32_windows(keywords, pid):
                return True

            # 2. Try pygetwindow window search
            if self._check_pygetwindow(keywords):
                return True

            time.sleep(poll_interval)

        return False

    def _check_win32_windows(self, keywords: set, target_pid: Optional[int]) -> bool:
        try:
            import win32gui
            import win32process

            found = False
            child_pids = set()
            if target_pid and psutil.pid_exists(target_pid):
                try:
                    p = psutil.Process(target_pid)
                    child_pids = {c.pid for c in p.children(recursive=True)}
                    child_pids.add(target_pid)
                except Exception:
                    child_pids = {target_pid}

            def enum_cb(hwnd, _):
                nonlocal found
                if found:
                    return
                try:
                    if not win32gui.IsWindowVisible(hwnd):
                        return

                    # Check window title
                    raw_title = win32gui.GetWindowText(hwnd) or ""
                    # Remove zero-width spaces that Edge/Windows 11 may insert
                    clean_title = raw_title.replace("\u200b", "").replace("\ufeff", "").strip().lower()

                    if clean_title:
                        for kw in keywords:
                            if kw in clean_title:
                                found = True
                                return

                    # Check process ID if window has non-empty text or belongs to target pid
                    if child_pids:
                        _, win_pid = win32process.GetWindowThreadProcessId(hwnd)
                        if win_pid in child_pids:
                            # Verify it's a real top-level window
                            if win32gui.GetParent(hwnd) == 0 and clean_title:
                                found = True
                                return
                except Exception:
                    pass

            win32gui.EnumWindows(enum_cb, None)
            return found
        except Exception:
            return False

    def _check_pygetwindow(self, keywords: set) -> bool:
        try:
            import pygetwindow as gw
            windows = gw.getAllWindows()
            for w in windows:
                if w.visible and w.title:
                    clean_title = w.title.replace("\u200b", "").replace("\ufeff", "").strip().lower()
                    for kw in keywords:
                        if kw in clean_title:
                            return True
        except Exception:
            pass
        return False

    def _log_diagnostic(self, user_command: str, result: LaunchResult):
        """Records an auditable diagnostic entry for the launch attempt."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "APPLICATION_LAUNCH",
            "user_command": user_command,
            "application": result.application,
            "display_name": result.display_name,
            "resolved_path": result.resolved_path,
            "launch_method": result.launch_method,
            "process_id": result.process_id,
            "success": result.success,
            "window_verified": result.window_verified,
            "error": result.error,
            "details": result.details,
            "user_message": result.message,
        }
        try:
            AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to record launch diagnostic log: {e}")

    def is_process_running(self, process_name: str) -> bool:
        process_name_clean = process_name.lower()
        for proc in psutil.process_iter(['name']):
            try:
                if process_name_clean in proc.info['name'].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def list_running_windows(self) -> List[str]:
        """Returns visible window titles on Windows."""
        titles = []
        try:
            import pygetwindow as gw
            windows = gw.getAllTitles()
            titles = [w.strip() for w in windows if w.strip()]
        except Exception:
            pass
        return titles
