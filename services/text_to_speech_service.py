import os
import uuid
import logging
from typing import Dict, Any, Optional
import config

logger = logging.getLogger(__name__)

# Try importing pyttsx3
try:
    import pyttsx3
    PYTTSX3_INSTALLED = True
except ImportError:
    pyttsx3 = None
    PYTTSX3_INSTALLED = False

class TextToSpeechService:
    def __init__(self):
        self.rate = config.TTS_RATE
        self.volume = config.TTS_VOLUME
        self._engine_available = None

    def is_available(self) -> bool:
        """Check if pyttsx3 can be initialized on this host system."""
        if not PYTTSX3_INSTALLED:
            return False
        if self._engine_available is not None:
            return self._engine_available

        try:
            # Attempt a quick driver initialization check
            engine = pyttsx3.init()
            engine.stop()
            self._engine_available = True
        except Exception as e:
            logger.warning(f"pyttsx3 is installed but SAPI/audio device is unavailable on this host: {e}")
            self._engine_available = False
        return self._engine_available

    def _get_engine(self):
        """Create and configure a fresh pyttsx3 engine instance."""
        if not self.is_available():
            return None
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", self.rate)
            engine.setProperty("volume", self.volume)
            return engine
        except Exception as e:
            logger.error(f"Failed to create pyttsx3 engine: {e}")
            return None

    def speak_locally(self, text: str) -> Dict[str, Any]:
        """
        Speak text directly through the host computer's speakers.
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "pyttsx3 audio output device is not available on this host. Use browser speech playback."
            }

        try:
            engine = self._get_engine()
            if not engine:
                return {"success": False, "error": "TTS engine could not be initialized."}
            engine.say(text)
            engine.runAndWait()
            return {"success": True, "error": None}
        except Exception as e:
            logger.error(f"pyttsx3 speak_locally error: {e}")
            return {"success": False, "error": str(e)}

    def synthesize_to_file(self, text: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Synthesize text to a WAV file in the outputs directory for web browser playback.
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "pyttsx3 is not available on this system. Web Speech API playback will be used.",
                "filename": None,
                "url": None
            }

        if not filename:
            filename = f"sara_speech_{uuid.uuid4().hex[:8]}.wav"

        filepath = os.path.join(config.OUTPUT_FOLDER, filename)
        try:
            engine = self._get_engine()
            if not engine:
                return {
                    "success": False,
                    "error": "TTS engine not available",
                    "filename": None,
                    "url": None
                }
            engine.save_to_file(text, filepath)
            engine.runAndWait()

            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                return {
                    "success": True,
                    "filename": filename,
                    "url": f"/download/{filename}",
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "error": "Audio file was not generated.",
                    "filename": None,
                    "url": None
                }
        except Exception as e:
            logger.error(f"pyttsx3 synthesize error: {e}")
            return {
                "success": False,
                "error": str(e),
                "filename": None,
                "url": None
            }

text_to_speech_service = TextToSpeechService()
