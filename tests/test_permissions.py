"""
Unit tests for FRIDAY Security & Permission System.
"""

import pytest
from config.constants import RiskLevel
from core.permissions import ActionRequest, SecurityManager


@pytest.fixture
def security():
    sec = SecurityManager()
    sec.reset_emergency_stop()
    return sec


def test_low_risk_auto_approved(security):
    req = ActionRequest(
        action_type="calculate",
        tool_name="DesktopController",
        description="Calculate 250 * 48",
        risk_level=RiskLevel.LOW,
    )
    assert security.evaluate_permission(req) is True


def test_moderate_risk_requires_handler_or_confirmation(security):
    req = ActionRequest(
        action_type="organize_folder",
        tool_name="FileController",
        description="Organize Downloads folder",
        risk_level=RiskLevel.MODERATE,
    )
    # When no confirmation handler is set, should be rejected for safety
    security.set_confirmation_handler(None)
    assert security.evaluate_permission(req) is False

    # When confirmation handler returns True
    security.set_confirmation_handler(lambda r: True)
    assert security.evaluate_permission(req) is True


def test_emergency_stop_blocks_everything(security):
    security.trigger_emergency_stop()
    assert security.is_emergency_stop_active() is True

    req = ActionRequest(
        action_type="calculate",
        tool_name="DesktopController",
        description="Safe low-risk calc",
        risk_level=RiskLevel.LOW,
    )
    # Blocked because emergency stop is active
    assert security.evaluate_permission(req) is False

    security.reset_emergency_stop()
    assert security.evaluate_permission(req) is True
