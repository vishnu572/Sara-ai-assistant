import os
import uuid
import logging
from typing import Dict, Any, Optional
import config
from services.speech_recognition_service import speech_recognition_service
from services.text_to_speech_service import text_to_speech_service
from services.assistant import assistant_service
from services.commands import is_command, execute_command
from database.history import add_message, get_conversation

logger = logging.getLogger(__name__)

class VoiceService:
    def __init__(self):
        self.sr_service = speech_recognition_service
        self.tts_service = text_to_speech_service

    def process_voice_interaction(
        self,
        audio_filepath: Optional[str] = None,
        text_prompt: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Full voice cycle:
        1. Transcribe audio if provided
        2. Generate response via AI assistant or commands
        3. Synthesize response to audio (pyttsx3) or flag for browser speech synthesis
        4. Record to conversation history if conversation_id provided
        """
        recognized_text = ""
        
        # Step 1: Transcribe audio if provided
        if audio_filepath:
            transcription = self.sr_service.transcribe_file(audio_filepath)
            if not transcription.get("success"):
                return {
                    "success": False,
                    "error": transcription.get("error", "Could not transcribe audio"),
                    "recognized_text": "",
                    "response_text": "",
                    "audio_url": None,
                    "use_browser_tts": False
                }
            recognized_text = transcription.get("text", "").strip()
        elif text_prompt:
            recognized_text = text_prompt.strip()
        else:
            return {
                "success": False,
                "error": "No audio or text provided for voice interaction.",
                "recognized_text": "",
                "response_text": "",
                "audio_url": None,
                "use_browser_tts": False
            }

        if not recognized_text:
            return {
                "success": False,
                "error": "No audible speech recognized. Please try again.",
                "recognized_text": "",
                "response_text": "",
                "audio_url": None,
                "use_browser_tts": False
            }

        # Step 2: Fetch history for context if conversation_id provided
        history_messages = []
        if conversation_id:
            conv = get_conversation(conversation_id)
            if conv and "messages" in conv:
                history_messages = conv["messages"]

        # Step 3: Handle commands or AI generation
        provider_name = "Sara AI Voice"
        if is_command(recognized_text):
            cmd_result = execute_command(recognized_text)
            response_text = cmd_result.get("text", "")
            provider_name = "Sara Command System"
        else:
            ai_result = assistant_service.generate_response(recognized_text, history=history_messages)
            response_text = ai_result.get("text", "")
            provider_name = ai_result.get("provider", "Sara AI")

        # Step 4: Save to database if conversation_id provided
        if conversation_id:
            try:
                add_message(conversation_id, "user", recognized_text, {"type": "voice_input"})
                add_message(conversation_id, "assistant", response_text, {"type": "voice_output", "provider": provider_name})
            except Exception as e:
                logger.error(f"Error persisting voice interaction in history: {e}")

        # Step 5: Synthesize voice
        audio_url = None
        use_browser_tts = False
        
        tts_res = self.tts_service.synthesize_to_file(response_text)
        if tts_res.get("success") and tts_res.get("url"):
            audio_url = tts_res["url"]
        else:
            # pyttsx3 not available or failed on host, instruct browser to speak natively
            use_browser_tts = True

        return {
            "success": True,
            "recognized_text": recognized_text,
            "response_text": response_text,
            "audio_url": audio_url,
            "use_browser_tts": use_browser_tts,
            "provider": provider_name,
            "error": None
        }

    def run_desktop_voice_mode(self) -> None:
        """
        Standalone desktop loop using local PyAudio and SpeechRecognition directly.
        Can be invoked from terminal: `python -m services.voice_service`
        """
        try:
            import speech_recognition as sr
        except ImportError:
            print("[ERROR] SpeechRecognition not installed.")
            return

        recognizer = sr.Recognizer()
        print("\n" + "="*50)
        print("  Sara AI — Desktop Voice Assistant Mode")
        print("  (Press Ctrl+C to exit)")
        print("="*50 + "\n")
        
        try:
            mic = sr.Microphone()
        except Exception as e:
            print(f"[ERROR] Could not access local microphone via PyAudio: {e}")
            print("Please ensure PyAudio is installed and a working microphone is connected.")
            return

        with mic as source:
            print("Calibrating microphone for ambient noise... Please wait 1 second.")
            recognizer.adjust_for_ambient_noise(source, duration=1.0)
            print("Sara AI is ready and listening! Speak into your microphone...")

            while True:
                try:
                    print("\nListening...")
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    print("Processing speech...")
                    try:
                        text = recognizer.recognize_google(audio, language=config.SPEECH_LANGUAGE)
                        print(f"You said: {text}")
                    except sr.UnknownValueError:
                        print("Sara could not understand audio.")
                        continue
                    except sr.RequestError as e:
                        print(f"Speech recognition service error: {e}")
                        continue

                    # Generate AI response
                    ai_resp = assistant_service.generate_response(text)
                    reply = ai_resp.get("text", "")
                    print(f"\nSara AI: {reply}\n")

                    # Speak response locally
                    self.tts_service.speak_locally(reply)

                except KeyboardInterrupt:
                    print("\nExiting Sara AI Desktop Voice Mode. Goodbye!")
                    break
                except Exception as e:
                    print(f"Error in voice loop: {e}")

voice_service = VoiceService()

if __name__ == "__main__":
    voice_service.run_desktop_voice_mode()
