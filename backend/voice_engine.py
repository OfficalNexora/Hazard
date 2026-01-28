try:
    import pyttsx3
    PYTHON_TTS_AVAILABLE = True
except ImportError:
    PYTHON_TTS_AVAILABLE = False
import threading
import time
import os

class VoiceEngine:
    """
    Local AI Voice Talker using pyttsx3 (SAPI5/nsss/espeak).
    Works offline and provides various voices.
    """
    def __init__(self):
        self.engine = None
        self.lock = threading.Lock()
        if PYTHON_TTS_AVAILABLE:
            self._init_engine()

    def _init_engine(self):
        if not PYTHON_TTS_AVAILABLE: return
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)    # Speed of speech
            self.engine.setProperty('volume', 1.0)  # Volume 0-1
            
            # Use the first available voice
            voices = self.engine.getProperty('voices')
            if voices:
                self.engine.setProperty('voice', voices[0].id)
        except Exception as e:
            print(f"[VoiceEngine] Initialization error: {e}")

    def say(self, text: str):
        """Speak text in a separate thread to avoid blocking"""
        def _speak():
            with self.lock:
                try:
                    print(f"[VoiceEngine] Speaking: {text}")
                    self.engine.say(text)
                    self.engine.runAndWait()
                except Exception as e:
                    print(f"[VoiceEngine] Error: {e}")
                    # Re-init if engine gets stuck
                    self._init_engine()

        threading.Thread(target=_speak, daemon=True).start()

    def save_to_file(self, text: str, filename: str):
        """Generate a .wav or .mp3 file of the speech"""
        with self.lock:
            try:
                self.engine.save_to_file(text, filename)
                self.engine.runAndWait()
                return True
            except Exception as e:
                print(f"[VoiceEngine] Save error: {e}")
                return False

# Global instance
voice_engine = VoiceEngine()
