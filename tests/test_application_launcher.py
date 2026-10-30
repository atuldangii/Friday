"""
Comprehensive unit and integration tests for ApplicationController.
Tests application resolution, missing executable handling, process creation,
launch exceptions, verified response formatting, and voice/text consistency.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from automation.applications import ApplicationController, LaunchResult, format_launch_response
from core.command_router import CommandRouter
from ai.tool_schemas import LaunchAppAction


@pytest.fixture
def app_controller():
    return ApplicationController()


@pytest.fixture
def command_router():
    return CommandRouter()


def test_edge_resolution_locates_executable(app_controller):
    """Verifies that Microsoft Edge resolves to an existing executable on Windows."""
    resolved_path, canonical_id, display_name, target_type = app_controller.resolve_application("microsoft edge")
    assert canonical_id == "msedge"
    assert display_name == "Microsoft Edge"
    assert target_type == "exe"
    assert resolved_path is not None
    assert Path(resolved_path).exists()
    assert resolved_path.lower().endswith("msedge.exe")


def test_notepad_resolution_locates_executable(app_controller):
    """Verifies that Notepad resolves to an existing executable on Windows."""
    resolved_path, canonical_id, display_name, target_type = app_controller.resolve_application("notepad")
    assert canonical_id == "notepad"
    assert display_name == "Notepad"
    assert target_type == "exe"
    assert resolved_path is not None
    assert Path(resolved_path).exists()
    assert resolved_path.lower().endswith("notepad.exe")


def test_missing_executable_handling(app_controller):
    """Verifies that non-existent applications fail gracefully with a helpful message."""
    result = app_controller.launch_app("non_existent_app_xyz")
    assert result.success is False
    assert result.process_id is None
    assert "not found" in result.error.lower()
    assert "couldn't find" in result.message.lower()
    assert "non_existent_app_xyz" in result.message.lower()


def test_launch_response_formatting_success_verified():
    """Verifies response text when application is open and window is verified."""
    res = LaunchResult(
        success=True,
        application="msedge",
        display_name="Microsoft Edge",
        process_id=1234,
        window_verified=True,
    )
    msg = format_launch_response(res)
    assert msg == "Microsoft Edge is open."


def test_launch_response_formatting_success_unverified_window():
    """Verifies honest response when process launched but window could not be verified."""
    res = LaunchResult(
        success=True,
        application="msedge",
        display_name="Microsoft Edge",
        process_id=1234,
        window_verified=False,
    )
    msg = format_launch_response(res)
    assert msg == "The launch request succeeded, but I couldn't confirm that the window appeared."


def test_launch_response_formatting_rejection():
    """Verifies response when OS rejects launch."""
    res = LaunchResult(
        success=False,
        application="notepad",
        display_name="Notepad",
        error="Access is denied [Error 5]",
        resolved_path=r"C:\Windows\notepad.exe",
    )
    msg = format_launch_response(res)
    assert msg == "I couldn't open Notepad. Here is the error: Access is denied [Error 5]."


def test_launch_exception_handling(app_controller):
    """Verifies handling when subprocess.Popen raises an exception."""
    with patch("subprocess.Popen", side_effect=PermissionError("Permission denied")):
        result = app_controller.launch_app("notepad")
        assert result.success is False
        assert "Permission denied" in result.error
        assert "couldn't open" in result.message.lower()


def test_command_consistency_edge(command_router):
    """Verifies that different phrasings of Edge commands resolve to the exact same action."""
    variations = [
        "Open Microsoft Edge.",
        "Launch Edge.",
        "Start Microsoft Edge.",
        "Hey FRIDAY, open Microsoft Edge",
        "open edge",
    ]
    for cmd in variations:
        action = command_router.route(cmd)
        assert isinstance(action, LaunchAppAction), f"Failed on command: {cmd}"
        assert action.app_name in ("microsoft edge", "edge")


def test_command_consistency_notepad(command_router):
    """Verifies that different phrasings of Notepad commands resolve to the exact same action."""
    variations = [
        "Open Notepad.",
        "Launch Notepad.",
        "Start Notepad.",
        "Hey FRIDAY, launch notepad",
    ]
    for cmd in variations:
        action = command_router.route(cmd)
        assert isinstance(action, LaunchAppAction), f"Failed on command: {cmd}"
        assert action.app_name == "notepad"
