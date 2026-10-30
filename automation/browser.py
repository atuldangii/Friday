"""
Browser Automation & Multi-Browser Control for FRIDAY AI.
Handles targeted URL navigation, session reuse, tab opening, search queries,
and honest verification reporting for Chrome, Edge, Firefox, and default browsers.
"""

import logging
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Dict, Optional, Tuple
import urllib.parse
import webbrowser

import requests

from automation.applications import ApplicationController

logger = logging.getLogger("Friday.Browser")

# Canonical names for display formatting
BROWSER_DISPLAY_NAMES = {
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "edge": "Microsoft Edge",
    "msedge": "Microsoft Edge",
    "microsoft edge": "Microsoft Edge",
    "firefox": "Mozilla Firefox",
    "mozilla firefox": "Mozilla Firefox",
    "brave": "Brave Browser",
    "opera": "Opera",
    "default": "your default browser",
}


WEBSITE_REGISTRY = {
    "linkedin": ("https://www.linkedin.com/", "LinkedIn"),
    "linked in": ("https://www.linkedin.com/", "LinkedIn"),
    "linkedin.com": ("https://www.linkedin.com/", "LinkedIn"),
    "youtube": ("https://www.youtube.com/", "YouTube"),
    "youtube.com": ("https://www.youtube.com/", "YouTube"),
    "gmail": ("https://mail.google.com/", "Gmail"),
    "gmail.com": ("https://mail.google.com/", "Gmail"),
    "github": ("https://github.com/", "GitHub"),
    "github.com": ("https://github.com/", "GitHub"),
    "google": ("https://www.google.com/", "Google"),
    "google.com": ("https://www.google.com/", "Google"),
    "chatgpt": ("https://chatgpt.com/", "ChatGPT"),
    "chatgpt.com": ("https://chatgpt.com/", "ChatGPT"),
    "openai": ("https://chatgpt.com/", "ChatGPT"),
    "openai.com": ("https://chatgpt.com/", "ChatGPT"),
    "wikipedia": ("https://www.wikipedia.org/", "Wikipedia"),
    "wikipedia.org": ("https://www.wikipedia.org/", "Wikipedia"),
}


class BrowserController:
    """Controls browser navigation, multi-browser targeting, and web searches."""

    def __init__(self, app_controller: Optional[ApplicationController] = None):
        self.app_ctrl = app_controller or ApplicationController()

    def resolve_destination(self, site_query: str) -> Tuple[str, str]:
        """Resolves common site names and aliases to their canonical URL and display name."""
        q_clean = (site_query or "").strip().lower()
        if q_clean in WEBSITE_REGISTRY:
            return WEBSITE_REGISTRY[q_clean]
        if q_clean.startswith("http://") or q_clean.startswith("https://"):
            return q_clean, self._extract_domain_name(q_clean)
        if "." in q_clean:
            return f"https://{q_clean}/", q_clean
        return f"https://{q_clean}.com/", q_clean.title()

    def resolve_browser(self, browser_name: str) -> Tuple[Optional[str], str, str]:
        """
        Resolves a browser identifier to its executable path, canonical ID, and display name.
        """
        b_clean = (browser_name or "default").strip().lower()
        if b_clean in ("default", "browser", "web browser", "my browser"):
            # Check for Google Chrome first (preferred default browser)
            chrome_target, cid, dname, _ = self.app_ctrl.resolve_application("chrome")
            if chrome_target and Path(chrome_target).exists():
                return chrome_target, "chrome", "Google Chrome"
            # Fallback to Microsoft Edge
            edge_target, cid, dname, _ = self.app_ctrl.resolve_application("msedge")
            if edge_target and Path(edge_target).exists():
                return edge_target, "msedge", "Microsoft Edge"
            return None, "default", "your default browser"

        resolved_target, canonical_id, display_name, target_type = self.app_ctrl.resolve_application(b_clean)
        display = BROWSER_DISPLAY_NAMES.get(canonical_id, display_name)
        return resolved_target, canonical_id, display

    def open_url(
        self,
        url: str,
        browser: str = "default",
        site_name: Optional[str] = None,
        browser_name: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Navigates to a URL in the specified browser.
        Reuses existing running browser instances (opening in a new tab) or launches the browser.
        Verifies navigation and returns an honest, action-specific response.
        """
        target_browser = browser_name or browser or "default"
        if not url:
            return False, "No destination URL provided."

        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        resolved_exe, canonical_id, browser_display = self.resolve_browser(target_browser)
        site_display = site_name or self._extract_domain_name(url)

        # ── Targeted Browser Execution (Chrome, Edge, Firefox, etc.) ─────────
        if resolved_exe and Path(resolved_exe).exists():
            try:
                # Check if browser is already running
                existing_hwnd = self.app_ctrl.find_running_app_window(canonical_id, browser_display)

                # Passing [url] to the browser executable on Windows either:
                # 1. Launches the browser with the URL, or
                # 2. Instructs the already-running instance to open a new tab with the URL.
                proc = subprocess.Popen(
                    [resolved_exe, url],
                    shell=False,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )

                # Short yield for window to focus or process to accept command
                time.sleep(0.2)

                # Bring window to foreground if it was already running
                if existing_hwnd:
                    self.app_ctrl.focus_window(existing_hwnd)
                else:
                    # Adaptive check: wait up to 1.5s for browser window to appear
                    self.app_ctrl.verify_window(canonical_id, browser_display, pid=proc.pid, timeout=1.5)

                return True, f"{site_display} is open in {browser_display}."

            except Exception as e:
                logger.error(f"[BrowserController] Error launching {resolved_exe}: {e}")
                # Fallback to standard webbrowser module
                try:
                    if webbrowser.open(url):
                        return True, f"{site_display} opened in {browser_display} via system fallback."
                    else:
                        return False, f"I couldn't navigate to {site_display}. Here is the reason: {e}"
                except Exception as fb_err:
                    return False, f"I couldn't navigate to {site_display}. Here is the reason: {fb_err}"

        # ── Default Browser Fallback ──────────────────────────────────────────
        try:
            opened = webbrowser.open(url)
            if opened:
                if browser != "default":
                    return True, f"{site_display} is open (opened in default browser as {browser} was not found)."
                return True, f"{site_display} is open in your browser."
            else:
                return False, f"I couldn't navigate to {site_display}. The system browser failed to respond."
        except Exception as e:
            return False, f"I couldn't navigate to {site_display}. Here is the reason: {e}"

    def search_web(
        self,
        query: str,
        engine: str = "google",
        browser: str = "default",
    ) -> Tuple[bool, str]:
        """Searches Google, DuckDuckGo, or Bing using the specified browser."""
        if not query or not query.strip():
            return False, "Search query is empty."

        clean_query = query.strip()
        encoded = urllib.parse.quote(clean_query)
        eng_lower = engine.lower()

        if eng_lower == "duckduckgo":
            url = f"https://duckduckgo.com/?q={encoded}"
            eng_display = "DuckDuckGo"
        elif eng_lower == "bing":
            url = f"https://www.bing.com/search?q={encoded}"
            eng_display = "Bing"
        else:
            url = f"https://www.google.com/search?q={encoded}"
            eng_display = "Google"

        _, _, browser_display = self.resolve_browser(browser)
        site_name = f"{eng_display} search for '{clean_query}'"
        success, msg = self.open_url(url, browser=browser, site_name=site_name)
        if success:
            return True, f"Searching {eng_display} for '{clean_query}' in {browser_display}."
        return success, msg

    def _fetch_top_youtube_video_id(self, query: str) -> Optional[str]:
        """Fetches the videoId of the top search result on YouTube."""
        try:
            encoded = urllib.parse.quote(query)
            url = f"https://www.youtube.com/results?search_query={encoded}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                # 1. Look for /watch?v=xxxxxxxxxxx
                ids = re.findall(r"/watch\?v=([a-zA-Z0-9_-]{11})", resp.text)
                if not ids:
                    # 2. Look for "videoId":"xxxxxxxxxxx" in ytInitialData
                    ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', resp.text)
                if ids:
                    return ids[0]
        except Exception as e:
            logger.debug(f"[BrowserController] Error resolving YouTube video ID: {e}")
        return None

    def play_youtube(
        self,
        query: str,
        browser: str = "default",
    ) -> Tuple[bool, str]:
        """
        Directly finds and plays the top video match on YouTube.
        Scrapes the top video ID and navigates directly to watch?v=...
        Falls back to search results if video resolution fails.
        """
        if not query or not query.strip():
            return False, "YouTube query is empty."

        clean_query = query.strip()
        encoded = urllib.parse.quote(clean_query)
        video_id = self._fetch_top_youtube_video_id(clean_query)

        _, _, browser_display = self.resolve_browser(browser)

        if video_id:
            watch_url = f"https://www.youtube.com/watch?v={video_id}"
            success, msg = self.open_url(watch_url, browser=browser, site_name=f"'{clean_query}' on YouTube")
            if success:
                return True, f"Playing '{clean_query}' on YouTube in {browser_display}."
            return success, msg
        else:
            # Fallback to search results
            search_url = f"https://www.youtube.com/results?search_query={encoded}"
            success, msg = self.open_url(search_url, browser=browser, site_name=f"YouTube search for '{clean_query}'")
            if success:
                return True, f"Searching YouTube for '{clean_query}' in {browser_display}."
            return success, msg

    def search_youtube(
        self,
        query: str,
        browser: str = "default",
        play: bool = False,
    ) -> Tuple[bool, str]:
        """Searches or plays YouTube for a topic or video using the specified browser."""
        if play:
            return self.play_youtube(query, browser=browser)

        if not query or not query.strip():
            return False, "YouTube search query is empty."

        clean_query = query.strip()
        encoded = urllib.parse.quote(clean_query)
        url = f"https://www.youtube.com/results?search_query={encoded}"

        _, _, browser_display = self.resolve_browser(browser)
        site_name = f"YouTube search for '{clean_query}'"
        success, msg = self.open_url(url, browser=browser, site_name=site_name)
        if success:
            return True, f"Searching YouTube for '{clean_query}' in {browser_display}."
        return success, msg

    def fetch_web_summary(self, query: str) -> Optional[str]:
        """
        Uses DuckDuckGo Instant Answer API for a quick factual summary.
        """
        try:
            endpoint = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
            headers = {"User-Agent": "FridayAI/1.2 (Windows NT 10.0; Win64; x64)"}
            resp = requests.get(endpoint, headers=headers, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                abstract = data.get("AbstractText")
                if abstract:
                    return abstract
                related = data.get("RelatedTopics", [])
                for topic in related:
                    if isinstance(topic, dict) and "Text" in topic:
                        return topic["Text"]
        except Exception as e:
            logger.debug(f"[BrowserController] Quick summary lookup error: {e}")
        return None

    def _extract_domain_name(self, url: str) -> str:
        """Extracts a human-readable title from a URL (e.g. 'https://www.linkedin.com' -> 'LinkedIn')."""
        try:
            parsed = urllib.parse.urlparse(url)
            host = parsed.netloc.lower()
            if host.startswith("www."):
                host = host[4:]
            parts = host.split(".")
            if len(parts) >= 2:
                name = parts[0]
                return name.capitalize()
            return host or url
        except Exception:
            return url
