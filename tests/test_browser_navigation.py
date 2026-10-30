"""
Comprehensive unit and integration tests for FRIDAY website navigation and browser control.
Covers Issue 1 requirements:
  1. "Open LinkedIn in Chrome" launches or reuses Chrome and navigates to LinkedIn.
  2. "Open YouTube in Chrome" navigates correctly.
  3. Existing Chrome window reuse vs new launch.
  4. Browser startup failure reporting (accurate reason, no false success).
  5. Navigation failure handling.
  6. Website registry resolution with natural aliases.
  7. Multi-step actions in sequence ("Open LinkedIn and then YouTube in Chrome").
"""

import subprocess
from unittest.mock import MagicMock, patch
import pytest

from ai.tool_schemas import NavigateWebsiteAction, WebSearchAction, YouTubeSearchAction
from automation.browser import BrowserController
from core.command_router import CommandRouter
from core.task_planner import TaskPlanner


@pytest.fixture
def router():
    return CommandRouter()


@pytest.fixture
def planner():
    return TaskPlanner()


@pytest.fixture
def browser():
    return BrowserController()


# ──────────────────────────────────────────────────────────────────────────────
#  1. Command Parsing & Intent Recognition
# ──────────────────────────────────────────────────────────────────────────────

def test_open_linkedin_in_chrome(router):
    cmd = "Open LinkedIn in Chrome."
    action = router.route(cmd)
    assert isinstance(action, NavigateWebsiteAction)
    assert action.url == "https://www.linkedin.com/"
    assert action.browser == "chrome"
    assert "linkedin" in action.site_name.lower()


def test_open_youtube_in_chrome(router):
    cmd = "Open YouTube in Chrome."
    action = router.route(cmd)
    assert isinstance(action, NavigateWebsiteAction)
    assert action.url == "https://www.youtube.com/"
    assert action.browser == "chrome"


def test_launch_chrome_and_go_to_linkedin(router):
    cmd = "Launch Chrome and go to LinkedIn."
    action = router.route(cmd)
    assert isinstance(action, NavigateWebsiteAction)
    assert action.url == "https://www.linkedin.com/"
    assert action.browser == "chrome"


def test_open_google_chrome_and_navigate_to_domain(router):
    cmd = "Open Google Chrome and navigate to linkedin.com."
    action = router.route(cmd)
    assert isinstance(action, NavigateWebsiteAction)
    assert "linkedin.com" in action.url
    assert action.browser == "chrome"


def test_open_gmail_in_edge(router):
    cmd = "Open Gmail in Edge."
    action = router.route(cmd)
    assert isinstance(action, NavigateWebsiteAction)
    assert action.url == "https://mail.google.com/"
    assert action.browser == "edge"


def test_open_github_in_browser(router):
    cmd = "Open GitHub in my browser."
    action = router.route(cmd)
    assert isinstance(action, NavigateWebsiteAction)
    assert action.url == "https://github.com/"


def test_search_google_in_chrome(router):
    cmd = "Open Chrome and search Google for software engineering jobs."
    action = router.route(cmd)
    assert isinstance(action, WebSearchAction)
    assert "software engineering jobs" in action.query.lower()
    assert action.browser == "chrome"


def test_search_youtube_for_python(router):
    cmd = "Search YouTube for Python tutorials."
    action = router.route(cmd)
    assert isinstance(action, YouTubeSearchAction)
    assert "python tutorials" in action.query.lower()


def test_website_registry_aliases(browser):
    # Test normalization of common variations
    url, name = browser.resolve_destination("LinkedIn")
    assert url == "https://www.linkedin.com/"

    url, name = browser.resolve_destination("Linked In")
    assert url == "https://www.linkedin.com/"

    url, name = browser.resolve_destination("ChatGPT")
    assert url == "https://chatgpt.com/"

    url, name = browser.resolve_destination("wikipedia")
    assert url == "https://www.wikipedia.org/"


# ──────────────────────────────────────────────────────────────────────────────
#  2. Browser Automation & Execution Logic
# ──────────────────────────────────────────────────────────────────────────────

def test_browser_reuse_existing_window(browser):
    """Verifies that an existing browser instance is reused and opened in new tab."""
    with patch("psutil.process_iter") as mock_piter, \
         patch("subprocess.Popen") as mock_popen, \
         patch("winreg.OpenKey"), \
         patch("winreg.QueryValueEx", return_value=(r"C:\Program Files\Google\Chrome\Application\chrome.exe", 1)):

        # Mock Chrome running in processes
        mock_proc = MagicMock()
        mock_proc.info = {"name": "chrome.exe", "pid": 1234}
        mock_piter.return_value = [mock_proc]

        success, msg = browser.open_url("https://www.linkedin.com/", browser_name="chrome", site_name="LinkedIn")
        assert success is True
        assert "LinkedIn is open in Google Chrome" in msg
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert "https://www.linkedin.com/" in args


def test_browser_launch_when_closed(browser):
    """Verifies launching browser with destination when browser is not currently running."""
    with patch("psutil.process_iter", return_value=[]), \
         patch("subprocess.Popen") as mock_popen, \
         patch("winreg.OpenKey"), \
         patch("winreg.QueryValueEx", return_value=(r"C:\Program Files\Google\Chrome\Application\chrome.exe", 1)):

        success, msg = browser.open_url("https://www.youtube.com/", browser_name="chrome", site_name="YouTube")
        assert success is True
        assert "YouTube is open in Google Chrome" in msg
        mock_popen.assert_called_once()


def test_browser_startup_failure_reporting(browser):
    """Accurately reports browser startup failure without claiming success."""
    with patch("psutil.process_iter", return_value=[]), \
         patch("subprocess.Popen", side_effect=OSError("Browser binary corrupted or missing")), \
         patch("winreg.OpenKey"), \
         patch("winreg.QueryValueEx", return_value=(r"C:\Fake\chrome.exe", 1)), \
         patch("webbrowser.open", return_value=False):

        success, msg = browser.open_url("https://www.linkedin.com/", browser_name="chrome", site_name="LinkedIn")
        assert success is False
        assert "couldn't navigate to" in msg.lower()
        assert "is open" not in msg


def test_multi_step_compound_plan(planner):
    """Verifies sequential compound command execution."""
    cmd = "Open LinkedIn and then YouTube in Chrome."
    plan = planner.build_plan(cmd)
    assert len(plan) == 2
    assert any("linkedin" in str(step.model_dump()).lower() for step in plan)
    assert any("youtube" in str(step.model_dump()).lower() for step in plan)
