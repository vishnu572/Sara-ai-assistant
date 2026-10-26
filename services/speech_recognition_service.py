import os
import io
import wave
import logging
from typing import Dict, Any, Optional
import config

logger = logging.getLogger(__name__)

# Try importing speech_recognition safely
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    sr = None
    SR_AVAILABLE = False

class SpeechRecognitionService:
    def __init__(self):
        self.language = config.SPEECH_LANGUAGE
        if SR_AVAILABLE:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
        else:
            self.recognizer = None

    def is_available(self) -> bool:
        """Check if SpeechRecognition library is installed."""
        return SR_AVAILABLE

    def transcribe_file(self, filepath: str) -> Dict[str, Any]:
        """
        Transcribe an audio file from disk (WAV format preferred).
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "SpeechRecognition library is not installed.",
                "text": ""
            }

        if not os.path.exists(filepath):
            return {
                "success": False,
                "error": f"Audio file not found: {filepath}",
                "text": ""
            }

        try:
            with sr.AudioFile(filepath) as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
                audio_data = self.recognizer.record(source)
                
            text = self.recognizer.recognize_google(audio_data, language=self.language)
            return {
                "success": True,
                "text": text.strip(),
                "error": None
            }
        except sr.UnknownValueError:
            return {
                "success": False,
                "error": "Sara could not understand the speech. Please speak clearly and try again.",
                "text": ""
            }
        except sr.RequestError as e:
            return {
                "success": False,
                "error": f"Speech recognition service unavailable: {str(e)}",
                "text": ""
            }
        except Exception as e:
            logger.error(f"Audio transcription error: {e}")
            return {
                "success": False,
                "error": f"Audio processing error: {str(e)}",
                "text": ""
            }

    def transcribe_bytes(self, audio_bytes: bytes, filename: str = "audio.wav") -> Dict[str, Any]:
        """
        Transcribe audio bytes by saving temporarily and reading with AudioFile.
        """
        temp_path = os.path.join(config.UPLOAD_FOLDER, f"temp_{os.path.basename(filename)}")
        try:
            with open(temp_path, "wb") as f:
                f.write(audio_bytes)
            return self.transcribe_file(temp_path)
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

speech_recognition_service = SpeechRecognitionService()
