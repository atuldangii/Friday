"""
Main Assistant Orchestrator for FRIDAY AI.
Binds voice, command routing, security permissions, automation tools, and memory.
"""

from pathlib import Path
import time
from typing import Callable, Optional, Tuple

from ai.cloud_model import CloudAIClient
from ai.tool_schemas import (
    CalculateAction,
    ClarificationAction,
    ConversationalResponseAction,
    FindFileAction,
    FridayAction,
    LaunchAppAction,
    MediaControlAction,
    NavigateWebsiteAction,
    OpenFolderAction,
    OpenUrlAction,
    OrganizeFolderAction,
    PowerAction,
    ScreenAnalysisAction,
    StopListeningAction,
    WebSearchAction,
    WriteNoteAction,
    YouTubeSearchAction,
)
from automation.applications import ApplicationController
from automation.browser import BrowserController
from automation.desktop import DesktopController
from automation.files import FileController
from config.constants import RiskLevel
from config.settings import SettingsManager
from core.command_router import CommandRouter
from core.memory import MemoryManager
from core.permissions import ActionRequest, SecurityManager
from core.task_planner import TaskPlanner
from voice.speech_recognition import SpeechRecognizer
from voice.text_to_speech import TextToSpeechEngine
from voice.wake_word import WakeWordDetector


def play_wake_chime():
    """Plays a high-tech two-tone HUD activation chime (B5 -> E6)."""
    try:
        import winsound
        winsound.Beep(988, 70)
        winsound.Beep(1318, 110)
    except Exception:
        pass


class FridayCore:
    def __init__(self):
        self.settings = SettingsManager()
        self.security = SecurityManager()
        self.memory = MemoryManager()

        # Tools
        self.app_ctrl = ApplicationController()
        self.browser_ctrl = BrowserController()
        self.desktop_ctrl = DesktopController()
        self.file_ctrl = FileController()

        # AI & Routing
        self.router = CommandRouter()
        self.cloud_ai = CloudAIClient()
        self.planner = TaskPlanner(self.execute_action)

        # Voice
        self.tts = TextToSpeechEngine()
        self.recognizer = SpeechRecognizer()
        self.wake_detector = WakeWordDetector(on_wake_detected=self._on_wake_word_activated)

        # UI Callbacks
        self.on_state_change: Optional[Callable[[str], None]] = None
        self.on_chat_message: Optional[Callable[[str, str], None]] = None
        self.on_task_progress: Optional[Callable[[int, int, str], None]] = None
        self.on_bring_to_front: Optional[Callable[[], None]] = None
        self.on_wake_detected: Optional[Callable[[], None]] = None

    def start_background_services(self):
        """Starts background wake-word listening so commands work from any app/site."""
        auto_listen = self.settings.get("system.auto_listen_on_startup", True)
        if auto_listen:
            self.wake_detector.start()

    def pause_listening(self):
        """Pauses background wake-word audio capture."""
        self.wake_detector.pause()

    def resume_listening(self):
        """Resumes background wake-word audio capture."""
        self.wake_detector.resume()

    def is_listening(self) -> bool:
        """Returns True if wake-word detection is running and unpaused."""
        return self.wake_detector.is_running()

    def toggle_listening(self) -> bool:
        """Toggles listening pause/resume. Returns new listening state."""
        if self.is_listening():
            self.pause_listening()
            return False
        else:
            self.resume_listening()
            return True

    def _set_state(self, state_name: str):
        if self.on_state_change:
            self.on_state_change(state_name)

    def _on_wake_word_activated(self, pre_detected_command: Optional[str] = None):
        """Called by WakeWordDetector when 'Hey Friday' is heard."""
        # Notify UI (e.g. show floating overlay above active third-party app)
        if self.on_wake_detected:
            try:
                self.on_wake_detected(pre_detected_command)
            except TypeError:
                self.on_wake_detected()
            except Exception:
                pass
        elif self.on_bring_to_front:
            try:
                self.on_bring_to_front()
            except Exception:
                pass

        try:
            if pre_detected_command:
                # User spoke wake-word and command in a single utterance (e.g. "Hey FRIDAY open YouTube")
                self.process_command(pre_detected_command, is_voice=True)
                return

            self._set_state("LISTENING")
            user_name = self.settings.get("user_name", "Sir")
            greeting = f"Hello {user_name}, what can I do for you?"
            if self.on_chat_message:
                self.on_chat_message("FRIDAY", greeting)

            # Speak: "Hello Sir, what can I do for you?"
            self.tts.speak(greeting)
            self.tts.wait_until_done(timeout=3.0)

            # Listen for the actual command (increased timeout for comfortable speech)
            success, text = self.recognizer.listen_and_recognize(timeout=6.0, phrase_time_limit=10.0)
            if success and text:
                self.process_command(text, is_voice=True)
            else:
                self._set_state("IDLE")
        finally:
            # Guarantee that background wake-word detection ALWAYS resumes for the next command
            if self.wake_detector._running:
                self.wake_detector.resume()

    def process_command(self, raw_command: str, is_voice: bool = False) -> str:
        """
        Main entry point for incoming user commands (voice or typed).
        Includes performance timing instrumentation.
        """
        if not raw_command or not raw_command.strip():
            return ""

        clean_text = raw_command.strip()
        t_start = time.perf_counter()

        if self.on_chat_message:
            self.on_chat_message("USER", clean_text)

        self._set_state("PROCESSING")

        # Check emergency stop reset if user says "resume" or "clear stop"
        if "clear stop" in clean_text.lower() or "reset emergency" in clean_text.lower():
            self.security.reset_emergency_stop()
            msg = "Emergency stop cleared. Systems are online."
            if self.on_chat_message:
                self.on_chat_message("FRIDAY", msg)
            self.tts.speak(msg)
            self._set_state("IDLE")
            return msg

        # Execute multi-step or single step via planner
        self._set_state("EXECUTING")
        success, response_message = self.planner.execute_plan(
            clean_text,
            progress_callback=self.on_task_progress,
        )

        t_end = time.perf_counter()
        elapsed_ms = (t_end - t_start) * 1000
        # Audit log the execution duration
        self.security.log_audit("COMMAND_EXECUTION", "process_command", f"{clean_text} [{elapsed_ms:.1f}ms]", success=success)

        # Log memory of interaction
        self.memory.log_interaction(clean_text, response_message)

        # Output response
        if self.on_chat_message:
            self.on_chat_message("FRIDAY", response_message)

        self._set_state("SPEAKING")
        self.tts.speak(response_message)
        if is_voice:
            self.tts.wait_until_done(timeout=7.0)
        self._set_state("IDLE")

        # Automatically resume wake-word detection for the NEXT command
        if self.wake_detector._running:
            self.wake_detector.resume()

        return response_message

    def execute_action(self, action: FridayAction) -> Tuple[bool, str]:
        """
        Validates permissions and dispatches action to appropriate controller.
        """
        # Create ActionRequest for permission validation
        req = ActionRequest(
            action_type=action.action_type,
            tool_name=type(action).__name__,
            description=f"Executing {action.action_type}",
            risk_level=action.risk_level,
            parameters=action.model_dump(),
        )

        # Permission check
        if not self.security.evaluate_permission(req):
            self.security.log_audit(req.action_type, req.tool_name, "Action rejected by security/user", success=False)
            return False, "Action cancelled or not approved."

        # Dispatch action
        action_type = action.action_type
        success = False
        message = ""

        try:
            if action_type == "launch_app":
                assert isinstance(action, LaunchAppAction)
                launch_res = self.app_ctrl.launch_app(action.app_name, action.arguments, user_command=req.description)
                success = launch_res.success
                message = launch_res.message

            elif action_type == "web_search":
                assert isinstance(action, WebSearchAction)
                browser_id = getattr(action, "browser", "default")
                # First check if DuckDuckGo has an instant summary
                summary = self.browser_ctrl.fetch_web_summary(action.query)
                success, browser_msg = self.browser_ctrl.search_web(action.query, engine=action.engine, browser=browser_id)
                if summary:
                    message = f"{summary} ({browser_msg})"
                else:
                    message = browser_msg

            elif action_type == "youtube_search":
                assert isinstance(action, YouTubeSearchAction)
                browser_id = getattr(action, "browser", "default")
                should_play = getattr(action, "play", False)
                if should_play:
                    success, message = self.browser_ctrl.play_youtube(action.query, browser=browser_id)
                else:
                    success, message = self.browser_ctrl.search_youtube(action.query, browser=browser_id)

            elif action_type == "navigate_website":
                assert isinstance(action, NavigateWebsiteAction)
                browser_id = getattr(action, "browser", "default")
                site = getattr(action, "site_name", None)
                success, message = self.browser_ctrl.open_url(action.url, browser=browser_id, site_name=site)

            elif action_type == "open_url":
                assert isinstance(action, OpenUrlAction)
                success, message = self.browser_ctrl.open_url(action.url)

            elif action_type == "calculate":
                assert isinstance(action, CalculateAction)
                success, message = self.desktop_ctrl.calculate(action.expression)

            elif action_type == "open_folder":
                assert isinstance(action, OpenFolderAction)
                success, message = self.file_ctrl.open_path(action.folder_name)

            elif action_type == "find_file":
                assert isinstance(action, FindFileAction)
                files = self.file_ctrl.search_file(action.query)
                if files:
                    found_names = [f.name for f in files]
                    success = True
                    message = f"Found {len(files)} matching file(s): {', '.join(found_names)}."
                    self.file_ctrl.open_path(str(files[0].parent))
                else:
                    success = False
                    message = f"I could not locate any files matching '{action.query}' in your user folders."

            elif action_type == "write_note":
                assert isinstance(action, WriteNoteAction)
                # First check if Notepad is already open (e.g. from prior step in compound plan)
                target_hwnd = self.app_ctrl.find_running_app_window("notepad", "Notepad")
                if not target_hwnd:
                    launch_res = self.app_ctrl.launch_app("notepad", user_command="Open Notepad and write note")
                    if not launch_res.success:
                        return False, f"Could not open Notepad to write the note. {launch_res.error or ''}".strip()
                    # Poll up to 1.5 seconds for window to be ready
                    for _ in range(15):
                        time.sleep(0.1)
                        target_hwnd = self.app_ctrl.find_running_app_window("notepad", "Notepad")
                        if target_hwnd:
                            break

                if target_hwnd:
                    self.app_ctrl.focus_window(target_hwnd)
                    time.sleep(0.3)
                else:
                    time.sleep(0.5)

                type_ok, type_err = self.desktop_ctrl.type_text(action.content)
                if type_ok:
                    success = True
                    message = "Opened Notepad and drafted your note, Sir."
                else:
                    success = False
                    message = f"Opened Notepad, but typing failed: {type_err}"

            elif action_type == "organize_folder":
                assert isinstance(action, OrganizeFolderAction)
                folder_path = self.file_ctrl.get_standard_folder(action.folder_name)
                if not folder_path or not folder_path.exists():
                    return False, f"Folder '{action.folder_name}' could not be located."

                preview = self.file_ctrl.preview_organize_folder_by_type(folder_path)
                total_files = sum(len(fnames) for fnames in preview.values())
                if total_files == 0:
                    return True, f"The {action.folder_name} folder has no files to organize."

                # Require confirmation with preview
                preview_summary = ", ".join([f"{cat} ({len(files)} files)" for cat, files in preview.items() if files])
                req.preview = f"Organizing {total_files} files into: {preview_summary}."
                req.description = f"Move {total_files} files in {folder_path.name} into categorised folders"
                
                # Check confirmation again with preview details
                if not self.security.evaluate_permission(req):
                    return False, f"Organization of {folder_path.name} was cancelled by user."

                success, message = self.file_ctrl.execute_organize_folder(folder_path, preview)

            elif action_type == "screen_analysis":
                assert isinstance(action, ScreenAnalysisAction)
                # Capture screenshot
                cap_ok, img_path = self.desktop_ctrl.capture_screenshot()
                if not cap_ok:
                    return False, "Failed to capture desktop screenshot."

                if self.cloud_ai.is_configured():
                    success, vision_explanation = self.cloud_ai.analyze_screen(img_path, action.prompt)
                    message = vision_explanation
                else:
                    # Local fallback explanation based on active window title
                    active_title = self.desktop_ctrl.get_active_window_title()
                    success = True
                    message = f"Screenshot captured. You currently have '{active_title}' active in the foreground. (Configure your GEMINI_API_KEY in Settings for deep AI visual analysis)."

            elif action_type == "media_control":
                assert isinstance(action, MediaControlAction)
                success, message = self.desktop_ctrl.media_control(action.media_command)

            elif action_type == "power_action":
                assert isinstance(action, PowerAction)
                success, message = self.desktop_ctrl.power_control(
                    action.power_command, action.delay_seconds
                )

            elif action_type == "stop_listening":
                self.wake_detector.pause()
                success = True
                message = "Voice listening paused. Click the microphone button or type 'resume' to re-enable."

            elif action_type == "clarification":
                assert isinstance(action, ClarificationAction)
                success = True
                message = action.question

            elif action_type == "chat_response":
                assert isinstance(action, ConversationalResponseAction)
                if action.response_text:
                    success = True
                    message = action.response_text
                elif self.cloud_ai.is_configured():
                    # Query cloud AI for conversational answer or structured tool call
                    ai_res = self.cloud_ai.understand_command(req.parameters.get("response_text", ""))
                    if ai_res and isinstance(ai_res, dict):
                        if ai_res.get("action_type") == "launch_app":
                            app_to_launch = ai_res.get("app_name", "")
                            launch_res = self.app_ctrl.launch_app(app_to_launch, ai_res.get("arguments"), user_command=req.description)
                            success = launch_res.success
                            message = launch_res.message
                        elif "response_text" in ai_res:
                            success = True
                            message = ai_res["response_text"]
                        else:
                            success = True
                            message = "I processed your request, Sir."
                    else:
                        success = True
                        message = "I processed your request, Sir."
                else:
                    success = True
                    message = "Command received, Sir."

            else:
                success = False
                message = f"Unknown action type: {action_type}"

        except Exception as e:
            success = False
            message = f"Execution error: {str(e)}"

        self.security.log_audit(req.action_type, req.tool_name, message, success=success, parameters=req.parameters)
        return success, message
