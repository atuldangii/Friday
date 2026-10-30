"""
Deterministic Command Router for FRIDAY AI.
Interprets natural language commands locally using regex patterns and semantic heuristics.
Ensures zero-latency offline command execution without requiring any cloud API.
"""

import datetime
import os
import re
from typing import List, Optional, Tuple
import psutil

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
from config.constants import RiskLevel
from config.settings import SettingsManager

# Mapping of well-known site names to canonical URLs
SITE_URL_MAP = {
    "youtube": "https://www.youtube.com/",
    "youtube.com": "https://www.youtube.com/",
    "google": "https://www.google.com/",
    "google.com": "https://www.google.com/",
    "gmail": "https://mail.google.com/",
    "gmail.com": "https://mail.google.com/",
    "github": "https://github.com/",
    "github.com": "https://github.com/",
    "linkedin": "https://www.linkedin.com/",
    "linked in": "https://www.linkedin.com/",
    "linkedin.com": "https://www.linkedin.com/",
    "chatgpt": "https://chatgpt.com/",
    "chatgpt.com": "https://chatgpt.com/",
    "openai": "https://chatgpt.com/",
    "openai.com": "https://chatgpt.com/",
    "wikipedia": "https://www.wikipedia.org/",
    "wikipedia.org": "https://www.wikipedia.org/",
    "facebook": "https://www.facebook.com/",
    "facebook.com": "https://www.facebook.com/",
    "twitter": "https://www.twitter.com/",
    "twitter.com": "https://www.twitter.com/",
    "x.com": "https://www.x.com/",
    "instagram": "https://www.instagram.com",
    "instagram.com": "https://www.instagram.com",
    "reddit": "https://www.reddit.com",
    "reddit.com": "https://www.reddit.com",
    "netflix": "https://www.netflix.com",
    "netflix.com": "https://www.netflix.com",
    "amazon": "https://www.amazon.com",
    "amazon.com": "https://www.amazon.com",
    "whatsapp": "https://web.whatsapp.com",
    "whatsapp.com": "https://web.whatsapp.com",
    "bing": "https://www.bing.com",
    "bing.com": "https://www.bing.com",
    "spotify": "https://open.spotify.com",
    "spotify.com": "https://open.spotify.com",
    "twitch": "https://www.twitch.tv",
    "twitch.tv": "https://www.twitch.tv",
    "stackoverflow": "https://stackoverflow.com",
    "stackoverflow.com": "https://stackoverflow.com",
    "maps": "https://maps.google.com",
    "google maps": "https://maps.google.com",
    "drive": "https://drive.google.com",
    "google drive": "https://drive.google.com",
}

# Known browser names to canonical IDs
BROWSER_NAMES = {
    "google chrome": "chrome",
    "chrome": "chrome",
    "microsoft edge": "edge",
    "edge": "edge",
    "msedge": "edge",
    "mozilla firefox": "firefox",
    "firefox": "firefox",
    "brave browser": "brave",
    "brave": "brave",
    "opera": "opera",
    "my browser": "default",
    "the browser": "default",
    "default browser": "default",
    "browser": "default",
}


def _resolve_site_url(site_name: str) -> Optional[str]:
    """Looks up a site name or domain in the known site map."""
    if not site_name:
        return None
    key = site_name.strip().rstrip(".,!?;: ").lower()
    # Normalize common spacing (e.g. "linked in" -> "linkedin")
    if key in SITE_URL_MAP:
        return SITE_URL_MAP[key]
    key_no_spaces = key.replace(" ", "")
    if key_no_spaces in SITE_URL_MAP:
        return SITE_URL_MAP[key_no_spaces]
    # If it already looks like a URL or domain
    if re.match(r"^[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}(/.*)?$", key):
        return f"https://{key}" if not key.startswith("http") else key
    return None


def _detect_browser(text: str) -> Optional[str]:
    """Extracts a browser name from text, returns canonical ID or None."""
    if not text:
        return None
    text_lower = text.strip().rstrip(".,!?;: ").lower()
    # Longest match first
    for bname in sorted(BROWSER_NAMES.keys(), key=len, reverse=True):
        if re.search(r"\b" + re.escape(bname) + r"\b", text_lower):
            return BROWSER_NAMES[bname]
    return None


class CommandRouter:
    def __init__(self):
        self.settings = SettingsManager()

    def _generate_note_content(self, topic: str) -> str:
        """
        Generates high-quality, structured note content for a given topic or text.
        If topic is a recognized theme (e.g. animals, project plan, technology),
        produces an informative structured summary. Otherwise formats the raw note nicely.
        """
        clean_topic = (topic or "").strip().rstrip(".,!?;: ")
        t_lower = clean_topic.lower()
        now_str = datetime.datetime.now().strftime("%A, %B %d, %Y - %I:%M %p")

        if not clean_topic:
            return (
                f"=== FRIDAY Note ===\n\n"
                f"Date: {now_str}\n\n"
                f"- General Memo\n"
                f"- Status: Active\n"
            )

        if "animal" in t_lower:
            return (
                f"=== Note: The Animal Kingdom ===\n\n"
                f"Date: {now_str}\n\n"
                f"Key Highlights:\n"
                f"• Diversity: Millions of distinct animal species inhabit planet Earth across land, air, and marine ecosystems.\n"
                f"• Major Groups:\n"
                f"  - Vertebrates: Mammals, birds, reptiles, amphibians, and fish.\n"
                f"  - Invertebrates: Insects, arachnids, mollusks, and crustaceans (representing over 95% of animal life).\n"
                f"• Adaptations: Species have developed specialized traits (camouflage, echolocation, migration) to thrive in extreme climates.\n"
                f"• Ecological Importance: Animals sustain life systems through pollination, seed dispersal, nutrient recycling, and food web balance.\n"
                f"• Conservation: Protecting global habitats and endangered species is essential for environmental stability.\n\n"
                f"Recorded by FRIDAY AI Assistant."
            )

        if "project plan" in t_lower or "project" in t_lower:
            return (
                f"=== FRIDAY PROJECT PLAN ===\n\n"
                f"Date: {now_str}\n\n"
                f"1. Objective & Scope Definition\n"
                f"2. Architecture & Security Review\n"
                f"3. Core Implementation & Testing\n"
                f"4. Windows 11 Deployment & Validation\n\n"
                f"Status: Active and Ready for execution."
            )

        if any(kw in t_lower for kw in ["tech", "ai", "artificial intelligence", "computer", "software"]):
            return (
                f"=== Note: Technology & Artificial Intelligence ===\n\n"
                f"Date: {now_str}\n\n"
                f"Key Insights:\n"
                f"• Machine Intelligence: Deep learning models and neural networks driving transformation across industries.\n"
                f"• Core Capabilities: Natural language processing, computer vision, automated workflow orchestration.\n"
                f"• Edge Computing: Transition to fast, private, on-device offline processing.\n"
                f"• Future Impact: Amplifying human productivity and engineering innovation.\n\n"
                f"Recorded by FRIDAY AI Assistant."
            )

        if any(kw in t_lower for kw in ["science", "space", "physics", "universe"]):
            return (
                f"=== Note: Science & Exploration ===\n\n"
                f"Date: {now_str}\n\n"
                f"Key Topics:\n"
                f"• Cosmic Exploration: James Webb Space Telescope and deep space astrophysics uncovering early galactic formation.\n"
                f"• Fundamental Physics: Quantum mechanics and gravitational wave research expanding boundaries of knowledge.\n"
                f"• Renewable Energy: Advances in battery density, nuclear fusion, and solar conversion.\n\n"
                f"Recorded by FRIDAY AI Assistant."
            )

        title_words = clean_topic.title()
        return (
            f"=== Note: {title_words} ===\n\n"
            f"Date: {now_str}\n\n"
            f"Content:\n"
            f"• {clean_topic}\n\n"
            f"Recorded by FRIDAY AI Assistant."
        )

    def clean_command(self, text: str) -> str:
        """Removes wake phrases, polite filler words, and trailing punctuation."""
        if not text:
            return ""
        cleaned = text.strip().rstrip(".,!?;: ")
        wake_words = ["hey friday", "friday", "ok friday", "hello friday", "hi friday"]
        for ww in wake_words:
            if cleaned.lower().startswith(ww):
                cleaned = cleaned[len(ww):].strip(", !.? ")

        # Remove leading request prefixes
        prefixes = [
            "can you please",
            "could you please",
            "can you",
            "could you",
            "please",
            "would you",
            "i want you to",
            "tell me",
        ]
        lower_cleaned = cleaned.lower()
        for p in prefixes:
            if lower_cleaned.startswith(p):
                cleaned = cleaned[len(p):].strip(", !.? ")
                break

        return cleaned.strip().rstrip(".,!?;: ")

    def route(self, raw_input: str) -> FridayAction:
        """
        Parses text and maps it to a validated typed action schema.
        """
        cmd = self.clean_command(raw_input)
        cmd_lower = cmd.lower()

        # 0. Power Management (shutdown / restart / sleep / hibernate / lock)
        # Cancel pending shutdown first
        if re.search(r"\b(?:cancel|abort|stop)\s+(?:shutdown|restart|reboot)\b", cmd_lower):
            return PowerAction(power_command="cancel_shutdown")

        # Sleep / Suspend patterns — checked BEFORE generic shutdown so "turn on sleep mode" is never confused
        if re.search(
            r"\b(?:go\s+to\s+)?sleep\s+(?:mode|mood)\b"
            r"|\b(?:turn\s+on|enable|activate|switch\s+to|enter)\s+sleep\s+(?:mode|mood)\b"
            r"|\bput\s+(?:the\s+|my\s+)?(?:computer|pc|laptop|system|machine)\s+to\s+sleep\b"
            r"|\bsend\s+(?:the\s+|my\s+)?(?:computer|pc|laptop|system|machine)?\s*to\s+sleep\b"
            r"|\bsleep\s+(?:the\s+|my\s+)?(?:computer|pc|laptop|system|machine)\b"
            r"|\b(?:computer|pc|laptop|system|machine)\s+sleep\b",
            cmd_lower
        ):
            return PowerAction(power_command="sleep")

        # Shutdown / Turn off patterns
        if re.search(
            r"\b(?:shut\s*down|power\s+off|turn\s+off)\b.*\b(?:computer|pc|laptop|system|machine)\b"
            r"|\b(?:computer|pc|laptop|system|machine)\b.*\b(?:shut\s*down|power\s+off|turn\s+off)\b"
            r"|^(?:shut\s*down|power\s+off|shutdown)$"
            r"|^turn\s+off\s+(?:my\s+|the\s+)?(?:laptop|pc|computer|system)$",
            cmd_lower
        ):
            delay = 0
            delay_match = re.search(r"in\s+(\d+)\s+(second|minute|min)s?", cmd_lower)
            if delay_match:
                n, unit = int(delay_match.group(1)), delay_match.group(2)
                delay = n * 60 if "min" in unit else n
            return PowerAction(power_command="shutdown", delay_seconds=delay)

        # Restart / Reboot patterns
        if re.search(
            r"\b(?:restart|reboot|re-boot)\b.*\b(?:computer|pc|laptop|system|machine)\b"
            r"|\b(?:computer|pc|laptop|system|machine)\b.*\b(?:restart|reboot|re-boot)\b"
            r"|^(?:restart|reboot)$",
            cmd_lower
        ) and not re.search(r"\brestart\s+(?:the\s+)?app\b", cmd_lower):
            delay = 0
            delay_match = re.search(r"in\s+(\d+)\s+(second|minute|min)s?", cmd_lower)
            if delay_match:
                n, unit = int(delay_match.group(1)), delay_match.group(2)
                delay = n * 60 if "min" in unit else n
            return PowerAction(power_command="restart", delay_seconds=delay)

        # Hibernate patterns
        if re.search(r"\bhibernate\b|\bhibernation\b", cmd_lower):
            return PowerAction(power_command="hibernate")

        # Lock screen patterns
        if re.search(
            r"\block\s+(?:the\s+|my\s+)?(?:screen|computer|pc|laptop|workstation|system)\b"
            r"|\bsecure\s+(?:the\s+|my\s+)?(?:screen|computer|workstation)\b"
            r"|^lock(?:\s+the\s+screen|\s+screen)?$",
            cmd_lower
        ):
            return PowerAction(power_command="lock")

        # 1. Stop Listening / Pause Wake Word
        if any(kw in cmd_lower for kw in ["stop listening", "pause listening", "mute mic", "mute microphone", "go to sleep", "sleep friday", "stop voice"]):
            return StopListeningAction()

        # 1b. Media Controls (YouTube, browser audio, volume, playback)
        if cmd_lower in ("pause", "pause video", "pause music", "pause playback", "pause youtube", "stop music", "stop video"):
            return MediaControlAction(media_command="play_pause")
        if cmd_lower in ("play", "resume", "play video", "resume video", "resume playback", "start playback"):
            return MediaControlAction(media_command="play_pause")
        if re.search(r"\b(?:turn\s+)?volume\s+up\b|\bincrease\s+volume\b|\blouder\b", cmd_lower):
            return MediaControlAction(media_command="volume_up")
        if re.search(r"\b(?:turn\s+)?volume\s+down\b|\bdecrease\s+volume\b|\blower\s+volume\b|\bquieter\b", cmd_lower):
            return MediaControlAction(media_command="volume_down")
        if re.search(r"^(?:mute|unmute|mute\s+audio|mute\s+sound|mute\s+volume|toggle\s+mute)$", cmd_lower):
            return MediaControlAction(media_command="mute")
        if re.search(r"\b(?:next\s+track|next\s+song|next\s+video|skip\s+song|skip\s+video|skip)\b", cmd_lower):
            return MediaControlAction(media_command="next_track")
        if re.search(r"\b(?:previous\s+track|previous\s+song|previous\s+video|prev\s+track)\b", cmd_lower):
            return MediaControlAction(media_command="prev_track")

        # 2. Screen understanding
        if any(phrase in cmd_lower for phrase in [
            "what is on my screen",
            "what's on my screen",
            "explain what is displayed on my screen",
            "explain my screen",
            "analyze my screen",
            "look at my screen",
            "what am i looking at"
        ]):
            return ScreenAnalysisAction(prompt=cmd)

        # 3. Organize folder
        organize_match = re.search(r"organize (?:the )?(?:files in )?(?:my )?([a-zA-Z0-9_\-\s]+?)(?: folder)? by (?:file )?type", cmd_lower)
        if organize_match or ("organize" in cmd_lower and "folder" in cmd_lower):
            folder = "downloads"
            if organize_match:
                extracted = organize_match.group(1).strip()
                if extracted in ["downloads", "documents", "desktop"]:
                    folder = extracted
            elif "desktop" in cmd_lower:
                folder = "desktop"
            elif "documents" in cmd_lower:
                folder = "documents"
            return OrganizeFolderAction(folder_name=folder)

        # ── Browser-compound & Website Patterns ────────────────────────────────
        # Pattern A: "Launch/Open <browser> and (then )?<action>"
        # e.g. "Launch Chrome and go to LinkedIn"
        #      "Open Chrome and navigate to linkedin.com"
        #      "Open Chrome and search Google for software engineering jobs"
        #      "Open Chrome and search for Python tutorials"
        browser_and_action = re.search(
            r"^(?:open|launch|start|run)\s+([a-zA-Z\s]+?)\s+and\s+(?:then\s+)?(.+)$",
            cmd_lower
        )
        if browser_and_action:
            raw_b = browser_and_action.group(1).strip()
            rest = browser_and_action.group(2).strip()
            browser_id = _detect_browser(raw_b)
            if browser_id:
                # 1. Search query: "search (google for|the web for|for) <query>"
                search_sub = re.search(r"^search\s+(?:google\s+for|the\s+web\s+for|for)\s+(.+)$", rest)
                if search_sub:
                    return WebSearchAction(query=search_sub.group(1).strip(), browser=browser_id)

                # 2. YouTube search: "search youtube for <query>"
                yt_sub = re.search(r"^search\s+youtube\s+for\s+(.+)$", rest)
                if yt_sub:
                    return YouTubeSearchAction(query=yt_sub.group(1).strip(), browser=browser_id)

                # 3. Site navigation: "go to <site>", "navigate to <site>", "open <site>", "<site>"
                nav_sub = re.search(r"^(?:go\s+to|navigate\s+to|visit|open|run)\s+(.+)$", rest)
                target_site = nav_sub.group(1).strip() if nav_sub else rest
                url = _resolve_site_url(target_site)
                if url:
                    return NavigateWebsiteAction(url=url, browser=browser_id, site_name=target_site.title())

        # Pattern B: "<site> in/on/using/with <browser>"
        # e.g. "Open LinkedIn in Chrome"
        #      "Open YouTube in Chrome"
        #      "Open Gmail in Edge"
        #      "Open GitHub in my browser"
        #      "Open LinkedIn on Chrome"
        #      "Open LinkedIn using Google Chrome"
        site_in_browser = re.search(
            r"^(?:open|launch|go\s+to|navigate\s+to|visit)?\s*(.+?)\s+(?:in|on|using|with)\s+([a-zA-Z\s]+)$",
            cmd_lower
        )
        if site_in_browser:
            raw_site = site_in_browser.group(1).strip()
            raw_browser = site_in_browser.group(2).strip()
            url = _resolve_site_url(raw_site)
            browser = _detect_browser(raw_browser) or BROWSER_NAMES.get(raw_browser)
            if url and browser:
                return NavigateWebsiteAction(url=url, browser=browser, site_name=raw_site.title())

        # Pattern C: YouTube search or direct playback
        # e.g. "Search YouTube for Python tutorials"
        #      "Search Python tutorials on YouTube"
        #      "Play paradise song on YouTube"
        #      "Play lofi music on YouTube"
        yt_search_match = re.search(
            r"(?:search(?:\s+for)?\s+(.+?)\s+on\s+youtube|search\s+youtube\s+for\s+(.+)|play\s+(.+?)\s+on\s+youtube)",
            cmd_lower
        )
        if yt_search_match:
            groups = [g for g in yt_search_match.groups() if g]
            query = groups[0].strip() if groups else ""
            b_id = _detect_browser(cmd_lower) or "chrome"
            is_play = "play" in cmd_lower
            if query:
                return YouTubeSearchAction(query=query, browser=b_id, play=is_play)

        # Pattern C2: Direct play command (e.g. "Play paradise song", "Play coldplay paradise")
        if cmd_lower.startswith("play ") and not any(kw in cmd_lower for kw in ["play video", "play music", "play playback", "resume"]):
            song_query = re.sub(r"^play\s+", "", cmd, flags=re.IGNORECASE).strip().rstrip(".,!?;")
            song_query = re.sub(r"\s+on\s+youtube$", "", song_query, flags=re.IGNORECASE).strip()
            if song_query:
                b_id = _detect_browser(cmd_lower) or "chrome"
                return YouTubeSearchAction(query=song_query, browser=b_id, play=True)

        # Pattern D: "Open YouTube and search for <query>" or "Open YouTube and play <query>"
        yt_open_search = re.search(
            r"(?:open\s+youtube\s+and\s+search(?:\s+for)?|open\s+youtube\s+and\s+play)\s+(.+)",
            cmd_lower
        )
        if yt_open_search:
            query = yt_open_search.group(1).strip()
            b_id = _detect_browser(cmd_lower) or "chrome"
            is_play = "play" in cmd_lower
            return YouTubeSearchAction(query=query, browser=b_id, play=is_play)

        # Pattern E: "go to <site>", "navigate to <site>", "visit <site>"
        goto_match = re.search(
            r"(?:go\s+to|navigate\s+to|visit|open\s+website|open\s+site)\s+([a-zA-Z0-9\.\-\/\:]+(?:\.[a-zA-Z]{2,}[^\s]*)?)",
            cmd_lower
        )
        if goto_match:
            raw_target = goto_match.group(1).strip()
            url = _resolve_site_url(raw_target)
            b_id = _detect_browser(cmd_lower) or "default"
            if url:
                return NavigateWebsiteAction(url=url, browser=b_id, site_name=raw_target.title())
            if "." in raw_target:
                full_url = f"https://{raw_target}" if not raw_target.startswith("http") else raw_target
                return NavigateWebsiteAction(url=full_url, browser=b_id, site_name=raw_target)

        # Pattern F: Direct known site opening (e.g. "Open LinkedIn", "Open YouTube", "Open Gmail")
        # Check this BEFORE application launching so sites are never mistaken for apps!
        known_site_match = re.search(r"^(?:open|launch|go\s+to|visit)\s+([a-zA-Z0-9\.\-\s]+)$", cmd_lower)
        if known_site_match:
            raw_site = known_site_match.group(1).strip()
            url = _resolve_site_url(raw_site)
            if url:
                b_id = _detect_browser(cmd_lower) or "default"
                return NavigateWebsiteAction(url=url, browser=b_id, site_name=raw_site.title())

        # Pattern G: "Search Google for <query>" or "Search the web for <query>"
        google_search_match = re.search(
            r"(?:search\s+(?:the\s+web\s+)?(?:for|on\s+google\s+for)|search\s+google\s+for|^google\s+for)\s+(.*)",
            cmd_lower
        )
        if google_search_match:
            query = google_search_match.group(1).strip().rstrip(".")
            b_id = _detect_browser(cmd_lower) or "default"
            return WebSearchAction(query=query, browser=b_id)

        # ── End Browser Patterns ──────────────────────────────────────────────

        # 5. Open Notepad and write text / Take note
        note_match = re.search(
            r"^(?:(?:open|run|launch|start)\s+notepad\s+and\s+)?(?:write|take|draft|type|create)\s+(?:a\s+)?(?:short\s+)?note\s*(?:on|about|for|:)?\s*(.*)$"
            r"|^(?:write|type|draft)\s+(?:a\s+)?note\s*(?:on|about|for|:)?\s*(.*)$"
            r"|^(?:take\s+a\s+note|make\s+a\s+note)\s*(?:on|about|for|:)?\s*(.*)$"
            r"|^notepad\s+(?:write|type|draft)\s+(.*)$",
            cmd_lower
        )
        if note_match:
            raw_topic = [g for g in note_match.groups() if g is not None][-1].strip()
            content = self._generate_note_content(raw_topic)
            return WriteNoteAction(app_target="notepad", content=content)

        if "notepad" in cmd_lower and any(w in cmd_lower for w in ["write", "type", "draft", "create"]):
            content_match = re.search(r"(?:write|type|draft|create)\s+(?:a\s+)?(.*)", cmd, re.IGNORECASE)
            raw_topic = content_match.group(1).strip() if content_match else ""
            content = self._generate_note_content(raw_topic)
            return WriteNoteAction(app_target="notepad", content=content)

        # 6. Calculate math expressions
        calc_match = re.search(r"(?:calculate|what is|compute|solve)?\s*([0-9\.\s\+\-\*\/\^\(\)]*(?:multiplied by|times|divided by|plus|minus|\bx\b)[0-9\.\s\+\-\*\/\^\(\)]+)", cmd_lower)
        if calc_match and any(op in calc_match.group(1) for op in ["*", "/", "+", "-", "multiplied", "times", "divided", "plus", "minus", "x"]):
            return CalculateAction(expression=calc_match.group(1).strip())
        elif re.search(r"\b(?:calculate|compute|solve)\b", cmd_lower):
            expr = re.sub(r"^(?:calculate|compute|solve)\s*", "", cmd_lower).strip()
            if expr:
                return CalculateAction(expression=expr)
            return LaunchAppAction(app_name="calculator")

        # 7. Find file
        find_match = re.search(r"(?:find|search for|locate)\s+(?:my\s+)?([a-zA-Z0-9_\-\.\s]+?)(?:\s+on\s+my\s+computer)?\.?$", cmd_lower)
        if find_match and not any(kw in cmd_lower for kw in ["web", "google", "youtube", "linkedin", "browser"]):
            q = find_match.group(1).strip().rstrip(".")
            return FindFileAction(query=q)

        # 8. Open folder
        folder_match = re.search(r"(?:open|show|go to)\s+(?:my\s+)?(downloads|documents|desktop|pictures|videos|music)(?:\s+folder)?\.?", cmd_lower)
        if folder_match:
            return OpenFolderAction(folder_name=folder_match.group(1))

        # 9. Launch Application
        app_match = re.search(r"(?:open|launch|start|run)\s+(?:the\s+)?([a-zA-Z0-9\s_\-\.]+)", cmd_lower)
        if app_match:
            raw_target = app_match.group(1).strip().rstrip(".,!?;")

            # Check if target is a known website
            url = _resolve_site_url(raw_target)
            if url:
                return NavigateWebsiteAction(url=url, browser="default", site_name=raw_target.title())

            # Check registered apps (longer matches first)
            reg_apps = self.settings.get("applications", {})
            sorted_names = sorted(reg_apps.keys(), key=len, reverse=True)
            for name in sorted_names:
                if name == raw_target:
                    return LaunchAppAction(app_name=name)

            # Check well-known desktop apps
            if "microsoft edge" in raw_target or raw_target == "edge":
                return LaunchAppAction(app_name="microsoft edge" if "microsoft" in raw_target else "edge")
            if "google chrome" in raw_target or raw_target == "chrome":
                return LaunchAppAction(app_name="google chrome" if "google" in raw_target else "chrome")
            if raw_target in ("browser", "web browser"):
                return LaunchAppAction(app_name="chrome")
            if "notepad" in raw_target:
                return LaunchAppAction(app_name="notepad")
            if "calc" in raw_target:
                return LaunchAppAction(app_name="calculator")
            if "paint" in raw_target:
                return LaunchAppAction(app_name="paint")
            if "task manager" in raw_target or "taskmgr" in raw_target:
                return LaunchAppAction(app_name="task manager")
            if "setting" in raw_target:
                return LaunchAppAction(app_name="settings")
            if "file explorer" in raw_target or "explorer" in raw_target:
                return LaunchAppAction(app_name="file explorer")
            if "firefox" in raw_target:
                return LaunchAppAction(app_name="firefox")
            if "command prompt" in raw_target or raw_target == "cmd":
                return LaunchAppAction(app_name="cmd")
            if "powershell" in raw_target:
                return LaunchAppAction(app_name="powershell")

            # Substring match against registered apps
            for name in sorted_names:
                if name in raw_target or raw_target in name:
                    return LaunchAppAction(app_name=name)

            return LaunchAppAction(app_name=raw_target)

        # 10. Search web fallback
        web_match = re.search(r"(?:search(?: the web)? for|search google for|^google)\s+(.*)", cmd_lower)
        if web_match:
            query = web_match.group(1).strip().rstrip(".")
            return WebSearchAction(query=query, browser="chrome")

        # 11. Open specific URLs
        if re.search(r"(?:open|go to)\s+(https?://[^\s]+|[a-zA-Z0-9\-]+\.(?:com|org|io|net|edu))", cmd_lower):
            url_match = re.search(r"(https?://[^\s]+|[a-zA-Z0-9\-]+\.(?:com|org|io|net|edu))", cmd_lower)
            if url_match:
                raw_url = url_match.group(1)
                resolved = _resolve_site_url(raw_url)
                return NavigateWebsiteAction(url=resolved or (f"https://{raw_url}" if not raw_url.startswith("http") else raw_url))

        # 12. Time / Date queries
        if any(phrase in cmd_lower for phrase in ["what time is it", "current time", "what's the time", "tell me the time"]):
            now_time = datetime.datetime.now().strftime("%I:%M %p")
            return ConversationalResponseAction(response_text=f"The current time is {now_time}.")

        if any(phrase in cmd_lower for phrase in ["what day is it", "what is today's date", "today's date", "what is the date"]):
            now_date = datetime.datetime.now().strftime("%A, %B %d, %Y")
            return ConversationalResponseAction(response_text=f"Today is {now_date}.")

        # 13. System health
        if any(phrase in cmd_lower for phrase in ["system status", "computer status", "how is my computer", "system health"]):
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory().percent
            return ConversationalResponseAction(response_text=f"All systems operational. CPU load is at {cpu}%, and RAM usage is at {mem}%.")

        # 14. Conversational greetings
        if any(cmd_lower.startswith(g) for g in ["hello", "hi", "hey", "good morning", "good evening", "who are you"]):
            user_name = self.settings.get("user_name", "Sir")
            return ConversationalResponseAction(
                response_text=f"Greetings, {user_name}. FRIDAY systems are fully operational and standing by for your command."
            )

        # 15. Informational Queries & General Questions (Redirect to Google Chrome)
        # e.g. "what is the on road price of suzuki fronx", "who is ...", "how to ...", "price of ..."
        info_query_match = re.search(
            r"^(?:what(?:'s|\s+is|\s+are)?|who(?:'s|\s+is|\s+was|\s+are)?|how(?:\s+to|\s+does|\s+do|\s+can)?|"
            r"why(?:\s+is|\s+does|\s+do)?|where(?:\s+is|\s+can)?|when(?:\s+is|\s+was)?|"
            r"price\s+of|cost\s+of|rate\s+of|on\s+road\s+price|tell\s+me\s+about|info\s+on|information\s+about)\b"
            r"|\b(?:price|cost|mileage|review|specs|specifications|vs|versus)\b",
            cmd_lower
        )
        if info_query_match:
            clean_q = cmd.strip().rstrip("?.!")
            return WebSearchAction(query=clean_q, browser="chrome")

        # 16. Fallback: Automatically redirect any query or request to Google in Chrome
        if cmd and len(cmd) > 2:
            return WebSearchAction(query=cmd, browser="chrome")

        return ConversationalResponseAction(response_text="Hello Sir, what can I do for you?")
