"""
Text-to-Speech (TTS) Engine for FRIDAY AI.
Delivers a bold, mature, deep-throat masculine voice persona using Windows SAPI5 (Microsoft David)
tuned with deep acoustic resonance, steady cadence, and markdown pre-filtering.
"""

import queue
import re
import threading
import time
from typing import Callable, List, Optional
import pyttsx3

from config.settings import SettingsManager


def clean_speech_text(text: str) -> str:
    """
    Cleans markdown formatting, symbols, bullets, and URLs so speech sounds
    natural, mature, and authoritative without reading technical characters.
    """
    if not text:
        return ""
    # Remove code blocks
    t = re.sub(r"```[\s\S]*?```", "", text)
    # Remove markdown formatting symbols
    t = re.sub(r"[=\*#_\~`]", " ", t)
    # Replace bullets and long dashes with natural pauses
    t = re.sub(r"[•\-\–\—]", ", ", t)
    # Remove URLs completely
    t = re.sub(r"https?://\S+", "", t)
    # Clean raw paths if any
    t = re.sub(r"[A-Z]:\\[^\s]+", "", t)
    # Normalize whitespace
    t = re.sub(r"\s+", " ", t).strip()
    return t


class TextToSpeechEngine:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TextToSpeechEngine, cls).__new__(cls)
                cls._instance._init_engine()
            return cls._instance

    def _init_engine(self):
        self.settings = SettingsManager()
        self.speech_queue = queue.Queue()
        self._is_speaking = False
        self._stop_event = threading.Event()
        self._state_callback: Optional[Callable[[bool], None]] = None
        self._current_engine = None

        # Start TTS background worker
        self._worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self._worker_thread.start()

    def set_state_callback(self, callback: Callable[[bool], None]):
        """Notifies UI when speaking starts/stops."""
        self._state_callback = callback

    def _speech_worker(self):
        """Worker loop that initializes pyttsx3 per speech item to maintain COM stability."""
        while True:
            try:
                raw_text = self.speech_queue.get()
                if raw_text is None:
                    break

                if self._stop_event.is_set():
                    self.speech_queue.task_done()
                    continue

                clean_text = clean_speech_text(raw_text)
                if not clean_text:
                    self.speech_queue.task_done()
                    continue

                self._is_speaking = True
                if self._state_callback:
                    self._state_callback(True)

                engine = pyttsx3.init()
                self._current_engine = engine

                # Bold, mature masculine cadence (146-152 WPM delivers deep chest/throat resonance)
                rate = int(self.settings.get("voice.rate", 148))
                volume = float(self.settings.get("voice.volume", 1.0))
                engine.setProperty("rate", rate)
                engine.setProperty("volume", volume)

                # Prioritize deep male voices (David or Mark)
                voices = engine.getProperty("voices")
                selected_voice_id = self.settings.get("voice.voice_id")
                chosen_voice = None

                if selected_voice_id:
                    for v in voices:
                        if selected_voice_id.lower() in v.id.lower() or selected_voice_id.lower() in v.name.lower():
                            chosen_voice = v.id
                            break

                if not chosen_voice:
                    for v in voices:
                        if "david" in v.name.lower() or "mark" in v.name.lower() or "male" in v.name.lower():
                            chosen_voice = v.id
                            break

                if chosen_voice:
                    engine.setProperty("voice", chosen_voice)

                # Direct SAPI Rate fine-tuning for deep masculine timbre
                try:
                    engine.proxy._driver._tts.Rate = -2
                except Exception:
                    pass

                engine.say(clean_text)
                engine.runAndWait()
                del engine
                self._current_engine = None

            except Exception as e:
                print(f"[TextToSpeechEngine] Speech error: {e}")
            finally:
                self._is_speaking = False
                if self._state_callback:
                    self._state_callback(False)
                self.speech_queue.task_done()

    def speak(self, text: str):
        """Queues text to be spoken."""
        if not self.settings.get("voice.enabled", True):
            return
        if not text or not text.strip():
            return
        self._stop_event.clear()
        self.speech_queue.put(text.strip())

    def stop(self):
        """Interrupts current speech immediately."""
        self._stop_event.set()
        if self._current_engine:
            try:
                self._current_engine.stop()
            except Exception:
                pass
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
                self.speech_queue.task_done()
            except queue.Empty:
                break
        self._is_speaking = False
        if self._state_callback:
            self._state_callback(False)

    def is_speaking(self) -> bool:
        return self._is_speaking or not self.speech_queue.empty()

    def wait_until_done(self, timeout: float = 8.0):
        """Blocks until pending speech has finished playing or timeout is reached."""
        t0 = time.time()
        time.sleep(0.04)
        while (self._is_speaking or not self.speech_queue.empty()) and (time.time() - t0) < timeout:
            if self._stop_event.is_set():
                break
            time.sleep(0.04)

    def list_available_voices(self) -> List[dict]:
        """Returns list of installed Windows voices."""
        try:
            temp_engine = pyttsx3.init()
            voices = temp_engine.getProperty("voices")
            res = [{"id": v.id, "name": v.name, "languages": getattr(v, "languages", [])} for v in voices]
            del temp_engine
            return res
        except Exception:
            return []
