"""
Tool Schemas and Action Definitions for FRIDAY AI.
Enforces structured action execution and prevents arbitrary code execution.
"""

from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field

from config.constants import RiskLevel


class BaseToolAction(BaseModel):
    action_type: str
    risk_level: RiskLevel = RiskLevel.LOW
    preview: Optional[str] = None


class LaunchAppAction(BaseToolAction):
    action_type: Literal["launch_app"] = "launch_app"
    app_name: str = Field(description="Name of the application to launch (e.g., chrome, notepad, calc)")
    arguments: Optional[List[str]] = Field(default=None, description="Optional command-line arguments")
    risk_level: RiskLevel = RiskLevel.LOW


class WebSearchAction(BaseToolAction):
    action_type: Literal["web_search"] = "web_search"
    query: str = Field(description="Search terms for Google / DuckDuckGo")
    engine: str = Field(default="google", description="Search engine to use")
    browser: str = Field(default="chrome", description="Browser to use (chrome, edge, default)")
    risk_level: RiskLevel = RiskLevel.LOW


class YouTubeSearchAction(BaseToolAction):
    action_type: Literal["youtube_search"] = "youtube_search"
    query: str = Field(description="Video search query on YouTube")
    browser: str = Field(default="chrome", description="Browser to use (chrome, edge, default)")
    play: bool = Field(default=False, description="Whether to directly play the top video match")
    risk_level: RiskLevel = RiskLevel.LOW


class NavigateWebsiteAction(BaseToolAction):
    action_type: Literal["navigate_website"] = "navigate_website"
    url: str = Field(description="Target website URL")
    browser: str = Field(default="chrome", description="Browser to navigate in (chrome, edge, default)")
    site_name: Optional[str] = Field(default=None, description="Human readable name of the site")
    new_tab: bool = Field(default=False, description="Whether to open in a new tab")
    risk_level: RiskLevel = RiskLevel.LOW


class OpenUrlAction(BaseToolAction):
    action_type: Literal["open_url"] = "open_url"
    url: str = Field(description="Target website URL")
    risk_level: RiskLevel = RiskLevel.LOW


class CalculateAction(BaseToolAction):
    action_type: Literal["calculate"] = "calculate"
    expression: str = Field(description="Mathematical expression to evaluate")
    risk_level: RiskLevel = RiskLevel.LOW


class OpenFolderAction(BaseToolAction):
    action_type: Literal["open_folder"] = "open_folder"
    folder_name: str = Field(description="Standard folder (downloads, documents, desktop) or path")
    risk_level: RiskLevel = RiskLevel.LOW


class FindFileAction(BaseToolAction):
    action_type: Literal["find_file"] = "find_file"
    query: str = Field(description="File name or keyword (e.g., resume)")
    risk_level: RiskLevel = RiskLevel.LOW


class WriteNoteAction(BaseToolAction):
    action_type: Literal["write_note"] = "write_note"
    app_target: str = Field(default="notepad", description="Target application (e.g., notepad)")
    content: str = Field(description="Text to write into the document")
    risk_level: RiskLevel = RiskLevel.LOW


class OrganizeFolderAction(BaseToolAction):
    action_type: Literal["organize_folder"] = "organize_folder"
    folder_name: str = Field(description="Folder to organize by file type (e.g. downloads)")
    risk_level: RiskLevel = RiskLevel.MODERATE


class ScreenAnalysisAction(BaseToolAction):
    action_type: Literal["screen_analysis"] = "screen_analysis"
    prompt: str = Field(default="Explain what is currently displayed on my screen.", description="Question about screen")
    risk_level: RiskLevel = RiskLevel.LOW


class StopListeningAction(BaseToolAction):
    action_type: Literal["stop_listening"] = "stop_listening"
    risk_level: RiskLevel = RiskLevel.LOW


class MediaControlAction(BaseToolAction):
    action_type: Literal["media_control"] = "media_control"
    media_command: str = Field(description="Media command: play_pause, volume_up, volume_down, mute, next_track, prev_track")
    risk_level: RiskLevel = RiskLevel.LOW


class PowerAction(BaseToolAction):
    """Controls system power state: shutdown, restart, sleep, hibernate, lock.

    Risk levels:
      - lock            → LOW    (no data loss, instantly reversible with password)
      - sleep           → LOW    (RAM preserved, reversible instantly)
      - cancel_shutdown → LOW    (cancels a pending action, always safe)
      - hibernate       → MODERATE (saves to disk, non-destructive)
      - shutdown        → HIGH   (closes apps, requires physical power button)
      - restart         → HIGH   (closes all apps, reboots system)
    """
    action_type: Literal["power_action"] = "power_action"
    power_command: str = Field(
        description="Power command: shutdown, restart, sleep, hibernate, lock, cancel_shutdown"
    )
    delay_seconds: int = Field(
        default=0,
        description="Delay in seconds before executing shutdown/restart (0 = immediate)"
    )
    risk_level: RiskLevel = RiskLevel.LOW

    def model_post_init(self, __context):
        if self.power_command in ("shutdown", "restart"):
            self.risk_level = RiskLevel.HIGH
        elif self.power_command == "hibernate":
            self.risk_level = RiskLevel.MODERATE
        else:
            self.risk_level = RiskLevel.LOW


class ClarificationAction(BaseToolAction):
    action_type: Literal["clarification"] = "clarification"
    question: str = Field(description="Clarification question to ask the user")
    risk_level: RiskLevel = RiskLevel.LOW


class ConversationalResponseAction(BaseToolAction):
    action_type: Literal["chat_response"] = "chat_response"
    response_text: str = Field(description="Direct conversational answer")
    risk_level: RiskLevel = RiskLevel.LOW


FridayAction = Union[
    LaunchAppAction,
    WebSearchAction,
    YouTubeSearchAction,
    NavigateWebsiteAction,
    OpenUrlAction,
    CalculateAction,
    OpenFolderAction,
    FindFileAction,
    WriteNoteAction,
    OrganizeFolderAction,
    ScreenAnalysisAction,
    StopListeningAction,
    MediaControlAction,
    PowerAction,
    ClarificationAction,
    ConversationalResponseAction,
]
