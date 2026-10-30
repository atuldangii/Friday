"""
Wake-Word Detection Engine for FRIDAY AI.
Supports hands-free background activation with configurable wake phrases ("Hey FRIDAY").
Runs in a background thread and triggers speech recognition upon activation.
Supports both direct single-utterance commands ("Hey FRIDAY open YouTube")
and two-step conversational wake ("Hey FRIDAY" -> "Yes, I am listening...").
"""

import re
import threading
import time
from typing import Callable, Optional, Tuple
import speech_recognition as sr

from config.constants import BASE_DIR
from config.settings import SettingsManager
from voice.speech_recognition import SpeechRecognizer


class WakeWordDetector:
    def __init__(self, on_wake_detected: Callable[..., None]):
        self.settings = SettingsManager()
        self.on_wake_detected = on_wake_detected
        self.speech_recognizer = SpeechRecognizer()
        self.vosk_model_dir = BASE_DIR / "vosk-model"

        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self):
        """Starts background hands-free listening."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._paused = False
            self._thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._thread.start()

    def pause(self):
        """Pauses wake-word detection (e.g. while FRIDAY is speaking or processing)."""
        self._paused = True

    def resume(self):
        """Resumes wake-word detection."""
        self._paused = False

    def stop(self):
        """Stops the background detector."""
        with self._lock:
            self._running = False
            self._paused = False

    def is_running(self) -> bool:
        return self._running and not self._paused

    @staticmethod
    def extract_command(text: str, configured_phrase: str = "hey friday") -> Tuple[bool, Optional[str]]:
        """
        Extracts trailing command from text if wake phrase or 'friday' is present.
        Supports: 'hey friday', 'ok friday', 'okay friday', 'hi friday', 'hello friday', 'friday'.
        Returns (is_wake: bool, command: Optional[str]).
        """
        text_clean = text.lower().strip()
        configured = configured_phrase.lower().strip()

        # Build list of recognized wake phrases
        phrases = [
            configured,
            "hey friday",
            "ok friday",
            "okay friday",
            "hi friday",
            "hello friday",
        ]
        # Remove duplicates while prioritizing longer phrases
        unique_phrases = sorted(list(set(p for p in phrases if p)), key=len, reverse=True)

        for phrase in unique_phrases:
            if phrase in text_clean:
                idx = text_clean.find(phrase)
                after = text_clean[idx + len(phrase):].strip(" ,.:;!?")
                return True, after if after else None

        # Check standalone "friday" with word boundaries
        match = re.search(r"\bfriday\b", text_clean)
        if match:
            after = text_clean[match.end():].strip(" ,.:;!?")
            return True, after if after else None

        return False, None

    def _safe_dispatch_wake(self, callback: Callable, extracted_cmd: Optional[str]):
        """Dispatches wake callback in dedicated thread and guarantees detector resumes."""
        try:
            callback(extracted_cmd)
        except TypeError:
            callback()
        except Exception as e:
            print(f"[WakeWordDetector] Error in wake callback: {e}")
            self.resume()

    def _listen_loop(self):
        """Background continuous audio monitor with persistent mic stream."""
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 220
        recognizer.dynamic_energy_threshold = True
        recognizer.dynamic_energy_adjustment_damping = 0.15
        recognizer.pause_threshold = 0.5

        while self._running:
            if self._paused or not self.settings.get("wake_word.enabled", True):
                time.sleep(0.2)
                continue

            wake_phrase = self.settings.get("wake_word.phrase", "hey friday").lower()
            device_index = self.settings.get("wake_word.input_device_index", -1)
            mic_args = {}
            if device_index >= 0:
                mic_args["device_index"] = device_index

            try:
                with sr.Microphone(**mic_args) as source:
                    # Initial ambient noise calibration
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)

                    # Persistent listening loop on the open mic stream
                    while self._running and not self._paused:
                        try:
                            audio = recognizer.listen(source, timeout=2.5, phrase_time_limit=5.0)
                        except sr.WaitTimeoutError:
                            continue

                        if self._paused or not self._running:
                            break

                        # Recognize audio
                        text = ""
                        # Try offline Vosk first if available
                        if self.vosk_model_dir.exists() and (self.vosk_model_dir / "am").exists():
                            try:
                                import json
                                vosk_res = recognizer.recognize_vosk(audio)
                                text = json.loads(vosk_res).get("text", "").lower().strip()
                            except Exception:
                                pass

                        # Fallback to Google recognizer
                        if not text:
                            try:
                                text = recognizer.recognize_google(audio).lower().strip()
                            except (sr.UnknownValueError, sr.RequestError):
                                continue

                        if not text:
                            continue

                        # Check if wake phrase or command is present
                        is_wake, extracted_cmd = self.extract_command(text, wake_phrase)
                        if is_wake:
                            self.pause()
                            # Asynchronously dispatch callback so with sr.Microphone() exits immediately
                            # and frees the audio capture device for the active recognition step
                            if self.on_wake_detected:
                                threading.Thread(
                                    target=self._safe_dispatch_wake,
                                    args=(self.on_wake_detected, extracted_cmd),
                                    daemon=True,
                                ).start()
                            break

            except Exception:
                # Device contention or temporary driver error
                time.sleep(1.0)
