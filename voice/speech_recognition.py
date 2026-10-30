"""
Speech Recognition Engine for FRIDAY AI.
Captures user voice through the microphone and converts speech to text.
Supports offline recognition via Vosk when a model is present,
with automatic fallback to local audio recognition.
"""

from pathlib import Path
from typing import List, Optional, Tuple
import speech_recognition as sr

from config.constants import BASE_DIR
from config.settings import SettingsManager


class SpeechRecognizer:
    def __init__(self):
        self.settings = SettingsManager()
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8

        self.vosk_model_dir = BASE_DIR / "vosk-model"

    def list_microphones(self) -> List[str]:
        """Returns the list of available audio input devices."""
        try:
            return sr.Microphone.list_microphone_names()
        except Exception as e:
            print(f"[SpeechRecognizer] Could not list microphones: {e}")
            return ["Default Microphone"]

    def listen_and_recognize(self, timeout: float = 5.0, phrase_time_limit: float = 8.0) -> Tuple[bool, str]:
        """
        Records audio from the selected microphone and converts it to text.
        Returns (success: bool, text_or_error: str).
        """
        device_index = self.settings.get("wake_word.input_device_index", -1)
        mic_args = {}
        if device_index >= 0:
            mic_args["device_index"] = device_index

        try:
            with sr.Microphone(**mic_args) as source:
                # Adjust for ambient noise briefly
                self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)

            # Try offline Vosk first if local model is installed
            if self.vosk_model_dir.exists() and (self.vosk_model_dir / "am").exists():
                try:
                    import json
                    vosk_res = self.recognizer.recognize_vosk(audio)
                    data = json.loads(vosk_res)
                    text = data.get("text", "").strip()
                    if text:
                        return True, text
                except Exception as e:
                    print(f"[SpeechRecognizer] Vosk recognition error: {e}")

            # Fallback to standard recognizer
            try:
                text = self.recognizer.recognize_google(audio)
                return True, text.strip()
            except sr.UnknownValueError:
                return False, "Could not understand audio"
            except sr.RequestError as e:
                return False, f"Speech recognition service error: {e}"

        except sr.WaitTimeoutError:
            return False, "Listening timed out with no speech detected"
        except Exception as e:
            return False, f"Microphone error: {str(e)}"
