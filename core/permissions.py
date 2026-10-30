"""
Security & Permission Architecture for FRIDAY AI.
Validates all actions against defined risk profiles and records an audit log.
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from config.constants import AUDIT_LOG_FILE, RiskLevel
from config.settings import SettingsManager


@dataclass
class ActionRequest:
    action_type: str
    tool_name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW
    preview: Optional[str] = None
    confirmed_by_user: bool = False


class SecurityManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SecurityManager, cls).__new__(cls)
            cls._instance._init_security()
        return cls._instance

    def _init_security(self):
        self.settings = SettingsManager()
        self._emergency_stop_triggered = False
        self._confirmation_handler: Optional[Callable[[ActionRequest], bool]] = None

    def set_confirmation_handler(self, handler: Callable[[ActionRequest], bool]):
        """Handler supplied by UI to prompt user for confirmation."""
        self._confirmation_handler = handler

    def trigger_emergency_stop(self):
        """Emergency stop: halts any pending or executing multi-step action."""
        self._emergency_stop_triggered = True
        self.log_audit("EMERGENCY_STOP", "SECURITY", "Global emergency stop triggered by user", success=True)

    def reset_emergency_stop(self):
        self._emergency_stop_triggered = False

    def is_emergency_stop_active(self) -> bool:
        return self._emergency_stop_triggered

    def evaluate_permission(self, request: ActionRequest) -> bool:
        """
        Evaluates whether an action can proceed based on its risk level and user confirmation.
        """
        if self._emergency_stop_triggered:
            self.log_audit(
                request.action_type,
                request.tool_name,
                f"Blocked action: Emergency stop is active ({request.description})",
                success=False,
            )
            return False

        # Low risk actions are auto-approved
        if request.risk_level == RiskLevel.LOW:
            return True

        # Check settings for moderate / high risk requirements
        req_moderate = self.settings.get("system.require_confirmation_for_moderate", True)
        req_high = self.settings.get("system.require_confirmation_for_high", True)

        if request.risk_level == RiskLevel.MODERATE and not req_moderate:
            return True

        if request.risk_level == RiskLevel.HIGH and not req_high:
            # High risk actions must always require confirmation unless explicitly overridden
            pass

        # If already confirmed by the UI dialog
        if request.confirmed_by_user:
            return True

        # Ask confirmation via handler
        if self._confirmation_handler is not None:
            approved = self._confirmation_handler(request)
            request.confirmed_by_user = approved
            return approved

        # If no UI confirmation handler registered, reject moderate/high risk for safety
        self.log_audit(
            request.action_type,
            request.tool_name,
            f"Blocked action: No confirmation handler registered for {request.risk_level.value} action",
            success=False,
        )
        return False

    def log_audit(self, action_type: str, tool_name: str, details: str, success: bool, parameters: Optional[dict] = None):
        """
        Appends an action entry to the audit log without sensitive data.
        """
        clean_params = {}
        if parameters:
            for k, v in parameters.items():
                if "key" in k.lower() or "token" in k.lower() or "secret" in k.lower() or "password" in k.lower():
                    clean_params[k] = "[REDACTED]"
                else:
                    clean_params[k] = str(v)[:100]

        entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "tool_name": tool_name,
            "details": details,
            "parameters": clean_params,
            "success": success,
        }

        try:
            with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"[SecurityManager] Failed to write audit log: {e}")
