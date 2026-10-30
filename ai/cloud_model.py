"""
Cloud AI Integration for FRIDAY AI.
Supports Google Gemini and OpenAI models using structured JSON tool calling.
Enforces security: AI responses are strictly validated against tool schemas and never executed as raw scripts.
"""

import json
import os
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image

from ai.tool_schemas import FridayAction
from config.settings import SettingsManager


SYSTEM_PROMPT = """You are FRIDAY (Female Replacement Intelligent Digital Assistant Youth), an advanced AI assistant inspired by Tony Stark's MCU assistant.
You control a Windows 11 desktop computer on behalf of the user.

Your goal is to parse the user's natural language request and respond ONLY with a valid JSON object matching one of the permitted action schemas:

Permitted action JSON structures:
1. Launch application:
   {"action_type": "launch_app", "app_name": "chrome", "arguments": []}
2. Search web:
   {"action_type": "web_search", "query": "latest AI developments", "engine": "google"}
3. Search YouTube:
   {"action_type": "youtube_search", "query": "Python tutorials"}
4. Open URL:
   {"action_type": "open_url", "url": "https://github.com"}
5. Safe calculation:
   {"action_type": "calculate", "expression": "250 * 48"}
6. Open user folder:
   {"action_type": "open_folder", "folder_name": "downloads"}
7. Find file on computer:
   {"action_type": "find_file", "query": "resume"}
8. Write note / document in Notepad:
   {"action_type": "write_note", "app_target": "notepad", "content": "..."}
9. Organize folder:
   {"action_type": "organize_folder", "folder_name": "downloads"}
10. Screen analysis:
   {"action_type": "screen_analysis", "prompt": "..."}
11. Stop listening:
   {"action_type": "stop_listening"}
12. Conversational answer / explanation:
   {"action_type": "chat_response", "response_text": "..."}
13. Clarification question (if request is ambiguous):
   {"action_type": "clarification", "question": "..."}

SECURITY CONSTRAINTS:
- NEVER output raw shell commands, powershell, or Python code.
- NEVER request file deletion or destructive actions.
- Output ONLY the JSON object, with no markdown code blocks or additional conversational filler outside the JSON.
"""


class CloudAIClient:
    def __init__(self):
        self.settings = SettingsManager()

    def is_configured(self) -> bool:
        provider = self.settings.get("ai.provider", "gemini")
        if provider == "gemini":
            key = self.settings.get("ai.gemini_api_key") or os.getenv("GEMINI_API_KEY")
            return bool(key and key.strip())
        elif provider == "openai":
            key = self.settings.get("ai.openai_api_key") or os.getenv("OPENAI_API_KEY")
            return bool(key and key.strip())
        return False

    def understand_command(self, user_prompt: str) -> Optional[dict]:
        """Queries Cloud AI to map an ambiguous prompt to a structured action."""
        if not self.is_configured():
            return None

        provider = self.settings.get("ai.provider", "gemini")
        if provider == "gemini":
            return self._call_gemini(user_prompt)
        elif provider == "openai":
            return self._call_openai(user_prompt)
        return None

    def _call_gemini(self, prompt: str) -> Optional[dict]:
        try:
            from google import genai
            from google.genai import types

            api_key = self.settings.get("ai.gemini_api_key") or os.getenv("GEMINI_API_KEY")
            client = genai.Client(api_key=api_key)
            model_name = self.settings.get("ai.gemini_model", "gemini-2.5-flash")

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.2,
                    response_mime_type="application/json",
                ),
            )

            if response and response.text:
                return json.loads(response.text.strip())
        except Exception as e:
            print(f"[CloudAIClient] Gemini error: {e}")
        return None

    def _call_openai(self, prompt: str) -> Optional[dict]:
        try:
            import requests

            api_key = self.settings.get("ai.openai_api_key") or os.getenv("OPENAI_API_KEY")
            base_url = self.settings.get("ai.openai_base_url", "https://api.openai.com/v1").rstrip("/")
            model_name = self.settings.get("ai.openai_model", "gpt-4o")

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            }

            resp = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return json.loads(content.strip())
        except Exception as e:
            print(f"[CloudAIClient] OpenAI error: {e}")
        return None

    def analyze_screen(self, image_path: Path, prompt: str) -> Tuple[bool, str]:
        """Performs multimodal screen understanding on a screenshot."""
        if not self.is_configured():
            return False, "Cloud AI is not configured. Add your GEMINI_API_KEY in Settings to enable visual screen analysis."

        try:
            from google import genai
            from google.genai import types

            api_key = self.settings.get("ai.gemini_api_key") or os.getenv("GEMINI_API_KEY")
            client = genai.Client(api_key=api_key)
            model_name = self.settings.get("ai.gemini_model", "gemini-2.5-flash")

            with open(image_path, "rb") as f:
                image_bytes = f.read()

            response = client.models.generate_content(
                model=model_name,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                    f"You are FRIDAY. The user asks: '{prompt}'. Provide a clear, natural summary of what is visible on this desktop screen.",
                ],
            )
            if response and response.text:
                return True, response.text.strip()
            return False, "Failed to analyze screen image."
        except Exception as e:
            return False, f"Vision analysis error: {str(e)}"
