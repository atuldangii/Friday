"""
Unit tests for FRIDAY deterministic CommandRouter.
Verifies parsing of MCU inspired and user-specified commands.
"""

import pytest
from core.command_router import CommandRouter
from ai.tool_schemas import (
    CalculateAction,
    FindFileAction,
    LaunchAppAction,
    OpenFolderAction,
    OrganizeFolderAction,
    ScreenAnalysisAction,
    StopListeningAction,
    WebSearchAction,
    WriteNoteAction,
    YouTubeSearchAction,
)


@pytest.fixture
def router():
    return CommandRouter()


def test_launch_chrome(router):
    action = router.route("Hey FRIDAY, open Google Chrome.")
    assert isinstance(action, LaunchAppAction)
    assert "chrome" in action.app_name.lower()


def test_youtube_search(router):
    action = router.route("Open YouTube and search for Python tutorials.")
    assert isinstance(action, YouTubeSearchAction)
    assert "python tutorials" in action.query.lower()


def test_open_downloads(router):
    action = router.route("Open my Downloads folder.")
    assert isinstance(action, OpenFolderAction)
    assert action.folder_name.lower() == "downloads"


def test_find_resume(router):
    action = router.route("Find my resume on my computer.")
    assert isinstance(action, FindFileAction)
    assert "resume" in action.query.lower()


def test_calculate_math(router):
    action = router.route("Open Calculator and calculate 250 multiplied by 48.")
    assert isinstance(action, CalculateAction)
    assert "250" in action.expression
    assert "48" in action.expression


def test_search_web(router):
    action = router.route("Search the web for the latest AI developments.")
    assert isinstance(action, WebSearchAction)
    assert "latest ai developments" in action.query.lower()


def test_write_notepad(router):
    action = router.route("Open Notepad and write a short project plan.")
    assert isinstance(action, WriteNoteAction)
    assert action.app_target == "notepad"
    assert "project plan" in action.content.lower()


def test_screen_understanding(router):
    action = router.route("Explain what is displayed on my screen.")
    assert isinstance(action, ScreenAnalysisAction)


def test_organize_folder(router):
    action = router.route("Organize the files in my Downloads folder by file type, but ask me before moving anything.")
    assert isinstance(action, OrganizeFolderAction)
    assert action.folder_name == "downloads"


def test_stop_listening(router):
    action = router.route("Stop listening, FRIDAY.")
    assert isinstance(action, StopListeningAction)
