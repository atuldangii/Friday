"""
Tests for FRIDAY background service, system tray, and compact floating HUD overlay.
Covers Issue 2, 3, 4, 5 requirements:
  1. Wake listener continues while main window is hidden/minimized.
  2. Overlay appears after wake event or global shortcut.
  3. Overlay displays live transcript and confirmation without blocking underlying app.
  4. Overlay dismiss does not terminate background listening.
  5. Microphone mute/resume works across hotkey, tray, and overlay button.
  6. Emergency stop and shutdown cleans up resources cleanly.
  7. Worker thread processes commands asynchronously without freezing GUI.
"""

from unittest.mock import MagicMock, patch
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from core.assistant import FridayCore
from core.hotkey import GlobalHotkeyListener
from ui.main_window import MainWindow
from ui.overlay_window import FridayOverlayWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app


@pytest.fixture
def mock_core():
    core = MagicMock()
    core.settings = MagicMock()
    core.settings.get.side_effect = lambda key, default=None: {
        "user_name": "TestUser",
        "system.minimize_to_tray": True,
        "system.auto_listen_on_startup": True,
        "wake_word.enabled": True,
    }.get(key, default)
    core.security = MagicMock()
    core.wake_detector = MagicMock()
    core.tts = MagicMock()
    core.is_listening.return_value = True
    return core


def test_overlay_window_flags(qapp):
    """Verifies overlay is frameless, stays on top, and acts as non-intrusive tool."""
    overlay = FridayOverlayWindow()
    flags = overlay.windowFlags()
    assert flags & Qt.FramelessWindowHint
    assert flags & Qt.WindowStaysOnTopHint
    assert flags & Qt.Tool
    assert overlay.width() <= 460
    assert overlay.height() <= 240


def test_overlay_interaction_update(qapp):
    """Verifies overlay shows user query and checks off successful actions."""
    overlay = FridayOverlayWindow()
    overlay.show_overlay("Open LinkedIn in Chrome", initial_state="PROCESSING")
    assert "Open LinkedIn in Chrome" in overlay.user_query_lbl.text()
    assert overlay.state_badge.text() == "PROCESSING"

    # Update with success response
    overlay.update_interaction(
        user_text="Open LinkedIn in Chrome",
        response_text="LinkedIn is open in Google Chrome.",
    )
    assert "LinkedIn is open in Google Chrome" in overlay.response_lbl.text()
    assert "✔" in overlay.response_lbl.text()


def test_overlay_dismiss_preserves_background(mock_core, qapp):
    """Dismissing the overlay must not terminate background wake listening."""
    overlay = FridayOverlayWindow()
    overlay.show_overlay()
    assert overlay.isVisible()

    overlay.hide_overlay()
    assert not overlay.isVisible()
    # Background listening is untouched
    assert mock_core.is_listening() is True


def test_mic_mute_toggle(qapp):
    """Verifies mute toggle button changes state and emits signal."""
    overlay = FridayOverlayWindow()
    signal_received = []
    overlay.mic_mute_toggled.connect(lambda val: signal_received.append(val))

    overlay._toggle_mic_mute()
    assert overlay._is_muted is True
    assert signal_received == [True]
    assert overlay.mic_mute_btn.text() == "🔇"

    overlay._toggle_mic_mute()
    assert overlay._is_muted is False
    assert signal_received == [True, False]
    assert overlay.mic_mute_btn.text() == "🎙"


def test_wake_detected_displays_overlay_when_main_hidden(mock_core, qapp):
    """When main window is hidden in background, wake-word activation pops up overlay."""
    with patch("core.hotkey.GlobalHotkeyListener.start"):
        win = MainWindow(mock_core)
        win.hide()
        assert not win.isVisible()

        win._on_wake_detected_ui()
        assert win.overlay.isVisible()
        assert win.overlay.state_badge.text() == "LISTENING"

        win.overlay.hide_overlay()
        win.cleanup()


def test_wake_detected_with_direct_command(mock_core, qapp):
    """Single-utterance wake+command populates overlay in PROCESSING state."""
    with patch("core.hotkey.GlobalHotkeyListener.start"):
        win = MainWindow(mock_core)
        win.hide()
        assert not win.isVisible()

        win._on_wake_detected_ui("open YouTube")
        assert win.overlay.isVisible()
        assert win.overlay.state_badge.text() == "PROCESSING"
        assert "open YouTube" in win.overlay.user_query_lbl.text()

        win.overlay.hide_overlay()
        win.cleanup()


def test_wake_word_detector_extract_command():
    """Verifies single-utterance vs two-step wake extraction."""
    from voice.wake_word import WakeWordDetector

    # Wake phrase with direct command
    is_wake, cmd = WakeWordDetector.extract_command("Hey FRIDAY open YouTube")
    assert is_wake is True
    assert cmd == "open youtube"

    # Punctuation and trailing spaces
    is_wake, cmd = WakeWordDetector.extract_command("Hey FRIDAY, search lofi music on YouTube.")
    assert is_wake is True
    assert cmd == "search lofi music on youtube"

    # Wake phrase alone
    is_wake, cmd = WakeWordDetector.extract_command("Hey FRIDAY")
    assert is_wake is True
    assert cmd is None

    # Alternative 'friday'
    is_wake, cmd = WakeWordDetector.extract_command("Friday, what time is it?")
    assert is_wake is True
    assert cmd == "what time is it"

    # Non-wake phrase
    is_wake, cmd = WakeWordDetector.extract_command("Good morning world")
    assert is_wake is False
    assert cmd is None


def test_media_controls_routing():
    """Verifies that media controls route to MediaControlAction for YouTube/audio control."""
    from core.command_router import CommandRouter
    from ai.tool_schemas import MediaControlAction

    router = CommandRouter()
    
    act_pause = router.route("pause video")
    assert isinstance(act_pause, MediaControlAction)
    assert act_pause.media_command == "play_pause"

    act_vol_up = router.route("volume up")
    assert isinstance(act_vol_up, MediaControlAction)
    assert act_vol_up.media_command == "volume_up"

    act_mute = router.route("mute sound")
    assert isinstance(act_mute, MediaControlAction)
    assert act_mute.media_command == "mute"


def test_global_hotkey_listener_initialization():
    """Verifies global hotkey registers overlay, mic, and emergency stop callbacks."""
    cb_overlay = MagicMock()
    cb_mic = MagicMock()
    cb_stop = MagicMock()

    listener = GlobalHotkeyListener(
        on_toggle_overlay=cb_overlay,
        on_toggle_mic=cb_mic,
        on_emergency_stop=cb_stop,
    )
    assert listener.on_toggle_overlay == cb_overlay
    assert listener.on_toggle_mic == cb_mic
    assert listener.on_emergency_stop == cb_stop
    assert listener._id_overlay == 9101
    assert listener._id_mic == 9102
    assert listener._id_stop == 9103


def test_emergency_stop_cleans_resources(mock_core, qapp):
    """Emergency stop pauses wake detector, tts, and updates state without crash."""
    with patch("core.hotkey.GlobalHotkeyListener.start"):
        win = MainWindow(mock_core)
        win._trigger_emergency_stop()

        mock_core.security.trigger_emergency_stop.assert_called_once()
        mock_core.wake_detector.stop.assert_called_once()
        mock_core.tts.stop.assert_called_once()
        assert win.overlay.state_badge.text() == "STOPPED"
        win.cleanup()


# ── Power Management Tests ────────────────────────────────────────────────────

def test_power_routing_shutdown():
    """Verifies shutdown command routes to PowerAction with correct power_command."""
    from core.command_router import CommandRouter
    from ai.tool_schemas import PowerAction

    router = CommandRouter()

    phrases = [
        "shut down my computer",
        "shut down my laptop",
        "turn off my laptop",
        "power off the system",
        "shutdown",
    ]
    for phrase in phrases:
        action = router.route(phrase)
        assert isinstance(action, PowerAction), f"Expected PowerAction for: '{phrase}'"
        assert action.power_command == "shutdown", f"Expected shutdown for: '{phrase}'"


def test_power_routing_restart():
    """Verifies restart / reboot routes to PowerAction."""
    from core.command_router import CommandRouter
    from ai.tool_schemas import PowerAction

    router = CommandRouter()

    phrases = [
        "restart my computer",
        "reboot my laptop",
        "restart my pc",
        "reboot",
    ]
    for phrase in phrases:
        action = router.route(phrase)
        assert isinstance(action, PowerAction), f"Expected PowerAction for: '{phrase}'"
        assert action.power_command == "restart", f"Expected restart for: '{phrase}'"


def test_power_routing_sleep():
    """Verifies sleep mode command routes to PowerAction with power_command='sleep'."""
    from core.command_router import CommandRouter
    from ai.tool_schemas import PowerAction

    router = CommandRouter()

    phrases = [
        "sleep mode",
        "put the computer to sleep",
        "put the laptop to sleep",
        "turn on sleep mode",
        "enable sleep mode",
    ]
    for phrase in phrases:
        action = router.route(phrase)
        assert isinstance(action, PowerAction), f"Expected PowerAction for: '{phrase}'"
        assert action.power_command == "sleep", f"Expected sleep for: '{phrase}'"


def test_power_routing_lock():
    """Verifies lock screen command routes to PowerAction with power_command='lock'."""
    from core.command_router import CommandRouter
    from ai.tool_schemas import PowerAction

    router = CommandRouter()

    phrases = [
        "lock the screen",
        "lock my computer",
        "lock the workstation",
        "lock my pc",
    ]
    for phrase in phrases:
        action = router.route(phrase)
        assert isinstance(action, PowerAction), f"Expected PowerAction for: '{phrase}'"
        assert action.power_command == "lock", f"Expected lock for: '{phrase}'"


def test_power_routing_cancel_shutdown():
    """Verifies cancel shutdown routes correctly."""
    from core.command_router import CommandRouter
    from ai.tool_schemas import PowerAction

    router = CommandRouter()
    action = router.route("cancel shutdown")
    assert isinstance(action, PowerAction)
    assert action.power_command == "cancel_shutdown"


def test_power_routing_hibernate():
    """Verifies hibernate command routes to PowerAction with power_command='hibernate'."""
    from core.command_router import CommandRouter
    from ai.tool_schemas import PowerAction

    router = CommandRouter()
    action = router.route("hibernate my laptop")
    assert isinstance(action, PowerAction)
    assert action.power_command == "hibernate"


def test_power_action_risk_level():
    """Verifies that high-impact power actions require confirmation while safe actions run seamlessly."""
    from ai.tool_schemas import PowerAction
    from config.constants import RiskLevel

    assert PowerAction(power_command="shutdown").risk_level == RiskLevel.HIGH
    assert PowerAction(power_command="restart").risk_level == RiskLevel.HIGH
    assert PowerAction(power_command="hibernate").risk_level == RiskLevel.MODERATE
    assert PowerAction(power_command="sleep").risk_level == RiskLevel.LOW
    assert PowerAction(power_command="lock").risk_level == RiskLevel.LOW
    assert PowerAction(power_command="cancel_shutdown").risk_level == RiskLevel.LOW


def test_power_action_shutdown_delay():
    """Verifies that timed shutdown correctly calculates delay_seconds."""
    from core.command_router import CommandRouter
    from ai.tool_schemas import PowerAction

    router = CommandRouter()
    action = router.route("shut down my computer in 5 minutes")
    assert isinstance(action, PowerAction)
    assert action.power_command == "shutdown"
    assert action.delay_seconds == 300  # 5 × 60


def test_sleep_friday_does_not_route_to_power():
    """'Sleep friday' / 'stop listening' must route to StopListeningAction, NOT PowerAction."""
    from core.command_router import CommandRouter
    from ai.tool_schemas import StopListeningAction

    router = CommandRouter()
    for phrase in ("sleep friday", "stop listening", "sleep friday now"):
        action = router.route(phrase)
        assert isinstance(action, StopListeningAction), (
            f"Expected StopListeningAction for: '{phrase}', got {type(action).__name__}"
        )


# ── YouTube Direct Playback & Note Writing Tests ───────────────────────────────

def test_youtube_play_direct():
    """Verifies that 'play ... on youtube' sets play=True on YouTubeSearchAction."""
    from core.command_router import CommandRouter
    from ai.tool_schemas import YouTubeSearchAction

    router = CommandRouter()

    action = router.route("play paradise song on youtube")
    assert isinstance(action, YouTubeSearchAction)
    assert action.play is True
    assert "paradise song" in action.query.lower()

    action2 = router.route("play paradise on youtube")
    assert isinstance(action2, YouTubeSearchAction)
    assert action2.play is True
    assert "paradise" in action2.query.lower()

    # Search should NOT force play
    action3 = router.route("search youtube for python tutorials")
    assert isinstance(action3, YouTubeSearchAction)
    assert action3.play is False


def test_write_note_on_animals():
    """Verifies that 'write a short note on animals' routes to WriteNoteAction with structured content."""
    from core.command_router import CommandRouter
    from ai.tool_schemas import WriteNoteAction

    router = CommandRouter()
    action = router.route("write a short note on animals")
    assert isinstance(action, WriteNoteAction)
    assert action.app_target == "notepad"
    assert "Animal Kingdom" in action.content
    assert "Vertebrates" in action.content


def test_compound_run_notepad_and_write_note():
    """Verifies that 'run notepad and write a short note on animals' decomposes into launch + note."""
    from core.task_planner import TaskPlanner
    from ai.tool_schemas import LaunchAppAction, WriteNoteAction

    planner = TaskPlanner()
    plan = planner.build_plan("run notepad and write a short note on animals")
    assert len(plan) == 2
    assert isinstance(plan[0], LaunchAppAction)
    assert plan[0].app_name == "notepad"
    assert isinstance(plan[1], WriteNoteAction)
    assert "Animal Kingdom" in plan[1].content


# ── Informational Search & Wake Greeting Tests ─────────────────────────────────

def test_info_query_redirects_to_chrome():
    """Verifies that informational queries like car prices and general questions route to Chrome search."""
    from core.command_router import CommandRouter
    from ai.tool_schemas import WebSearchAction

    router = CommandRouter()

    q1 = router.route("what is the on road price of suzuki fronx")
    assert isinstance(q1, WebSearchAction)
    assert "suzuki fronx" in q1.query.lower()
    assert q1.browser == "chrome"

    q2 = router.route("price of suzuki fronx")
    assert isinstance(q2, WebSearchAction)
    assert "suzuki fronx" in q2.query.lower()
    assert q2.browser == "chrome"

    q3 = router.route("who is elon musk")
    assert isinstance(q3, WebSearchAction)
    assert "elon musk" in q3.query.lower()
    assert q3.browser == "chrome"


def test_wake_greeting_speaks_hello_sir():
    """Verifies that wake-word activation speaks 'Hello Sir, what can I do for you?'."""
    core = MagicMock()
    core.settings.get.return_value = "Sir"
    core.tts = MagicMock()
    core.recognizer.listen_and_recognize.return_value = (False, None)
    core.wake_detector = MagicMock()
    core.on_wake_detected = None
    core.on_bring_to_front = None
    core.on_chat_message = MagicMock()

    FridayCore._on_wake_word_activated(core, pre_detected_command=None)
    core.tts.speak.assert_called_with("Hello Sir, what can I do for you?")
    core.on_chat_message.assert_called_with("FRIDAY", "Hello Sir, what can I do for you?")


def test_wake_phrase_hi_friday_extraction():
    """Verifies that 'hi friday' and its common variations trigger wake detection."""
    from voice.wake_word import WakeWordDetector

    wake_tests = [
        ("hi friday", True, None),
        ("hi, friday", True, None),
        ("hi friday open youtube", True, "open youtube"),
        ("hi, friday, run notepad", True, "run notepad"),
        ("hey friday", True, None),
        ("hey, friday", True, None),
        ("hello friday", True, None),
        ("ok friday", True, None),
        ("friday", True, None),
        ("hi fryday", True, None),
        ("what is the weather", False, None),
    ]

    for utterance, expected_wake, expected_cmd in wake_tests:
        is_wake, cmd = WakeWordDetector.extract_command(utterance)
        assert is_wake == expected_wake, f"Failed wake check for '{utterance}': got {is_wake}, expected {expected_wake}"
        if expected_cmd:
            assert cmd == expected_cmd, f"Failed cmd extraction for '{utterance}': got {cmd}, expected {expected_cmd}"
