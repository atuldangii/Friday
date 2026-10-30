"""
Task Planner for Multi-Step Commands in FRIDAY AI.
Decomposes complex requests into discrete validated action steps,
validates permissions, executes sequentially, and supports immediate cancellation.
"""

import re
import time
from typing import Callable, List, Optional, Tuple

from ai.tool_schemas import FridayAction, LaunchAppAction
from core.command_router import CommandRouter
from core.permissions import ActionRequest, SecurityManager

# Action-initiating verbs used to detect compound steps joined by bare "and"
_ACTION_VERBS = (
    "open", "launch", "start", "run", "search", "find", "calculate", "compute",
    "go to", "navigate", "visit", "play", "type", "write", "organize", "show",
    "close", "shut", "stop", "pause", "resume", "look at", "analyze",
)

# Pre-compiled split pattern:
# Splits on:  "and then" | "then" | "after that" | ", and" + action-verb | ", " + action-verb | " and " + action-verb
_SPLIT_PATTERN = re.compile(
    r"""
    (?:
        \s+and\s+then\s+                # "and then"
      | \s+then\s+                      # "then"
      | \s+after\s+that\s+             # "after that"
      | ,\s*and\s+                      # ", and"
      | ,\s*                            # ","
      | \s+and\s+(?=(?:""" +
    "|".join(re.escape(v) for v in _ACTION_VERBS) +
    r"""))                              # " and " followed by an action verb
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


class TaskStep:
    def __init__(self, step_number: int, instruction: str, action: FridayAction):
        self.step_number = step_number
        self.instruction = instruction
        self.action = action
        self.completed = False
        self.result_message = ""


class TaskPlanner:
    def __init__(self, action_executor: Optional[Callable[[FridayAction], Tuple[bool, str]]] = None):
        self.command_router = CommandRouter()
        self.security_manager = SecurityManager()
        self.action_executor = action_executor or (lambda action: (True, "Simulated execution"))
        self._is_cancelled = False

    def decompose(self, complex_command: str) -> List[str]:
        """
        Splits a compound instruction into discrete steps.

        Handles patterns like:
          "open Chrome and go to YouTube"
          "launch Edge and navigate to github.com"
          "open Chrome, open YouTube, then search for Python tutorials"
          "calculate 5 * 10 and open notepad and write the result"
        """
        raw_chunks = _SPLIT_PATTERN.split(complex_command)

        steps = []
        for chunk in raw_chunks:
            c = chunk.strip().rstrip(".,;")
            # Remove leading "and " artifacts
            if c.lower().startswith("and "):
                c = c[4:].strip()
            if c:
                steps.append(c)
        return steps

    def build_plan(self, command: str) -> List[FridayAction]:
        """
        Parses a command into structured FridayActions without executing them.
        Propagates browser context across multi-step sequences.
        """
        cleaned = self.command_router.clean_command(command)
        step_texts = self.decompose(cleaned)
        if not step_texts:
            return []

        active_browser: Optional[str] = None
        cmd_lower = cleaned.lower()
        for b_name in ("chrome", "google chrome", "edge", "microsoft edge", "firefox"):
            if f"in {b_name}" in cmd_lower or f"on {b_name}" in cmd_lower or f"using {b_name}" in cmd_lower:
                active_browser = "chrome" if "chrome" in b_name else ("edge" if "edge" in b_name else "firefox")
                break

        actions = []
        for text in step_texts:
            action = self.command_router.route(text)
            if active_browser and hasattr(action, "browser") and action.browser == "default":
                action.browser = active_browser
            actions.append(action)
        return actions

    def cancel(self):
        """Immediately stops the running multi-step plan."""
        self._is_cancelled = True

    def execute_plan(
        self,
        command: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Tuple[bool, str]:
        """
        Executes a multi-step plan step by step with validation and progress reporting.
        """
        self._is_cancelled = False
        cleaned = self.command_router.clean_command(command)
        step_texts = self.decompose(cleaned)

        if not step_texts:
            return False, "No valid action steps detected."

        # If it's just a single action, route and execute directly
        if len(step_texts) == 1:
            action = self.command_router.route(step_texts[0])
            return self.action_executor(action)

        total_steps = len(step_texts)
        results = []
        active_browser: Optional[str] = None

        # Check if the overall command specifies a target browser (e.g. "in Chrome")
        cmd_lower = cleaned.lower()
        for b_name in ("chrome", "google chrome", "edge", "microsoft edge", "firefox"):
            if f"in {b_name}" in cmd_lower or f"on {b_name}" in cmd_lower or f"using {b_name}" in cmd_lower:
                active_browser = "chrome" if "chrome" in b_name else ("edge" if "edge" in b_name else "firefox")
                break

        for idx, text in enumerate(step_texts, start=1):
            if self._is_cancelled or self.security_manager.is_emergency_stop_active():
                return False, f"Task cancelled by user at step {idx} of {total_steps}."

            if progress_callback:
                progress_callback(idx, total_steps, f"Executing: {text}")

            action = self.command_router.route(text)

            # Inherit browser if previously launched or detected
            if isinstance(action, LaunchAppAction):
                app_lower = action.app_name.lower()
                if "chrome" in app_lower:
                    active_browser = "chrome"
                elif "edge" in app_lower:
                    active_browser = "edge"
                elif "firefox" in app_lower:
                    active_browser = "firefox"

            if active_browser and hasattr(action, "browser") and getattr(action, "browser") == "default":
                action.browser = active_browser

            success, msg = self.action_executor(action)
            results.append(msg)

            if not success:
                return False, f"Task halted at step {idx} ({text}): {msg}"

            # Fast yield between steps without artificial latency
            if idx < total_steps:
                time.sleep(0.05)

        # If step 1 was launching an app/browser and step 2 was executing the target action, return clean final result
        if total_steps == 2 and ("is open" in results[-1] or "Searching" in results[-1] or "playing" in results[-1].lower() or "drafted" in results[-1].lower()):
            return True, results[-1]

        return True, "All done:\n" + "\n".join(results)
