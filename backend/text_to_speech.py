"""
Text-to-Speech module using pyttsx3 (offline)
"""
import pyttsx3
import threading
from queue import Queue
import config
import base64
import os
import uuid
import tempfile
import multiprocessing

def _generate_audio_file_process(text, filename, rate, volume):
    """
    Standalone function to run in a separate process.
    This ensures pyttsx3/COM loop is completely isolated and cleaned up.
    """
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except:
        pass # pythoncom might not be needed if comtypes is used, but good for safety
        
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', rate)
        engine.setProperty('volume', volume)
        
        # Simple voice selection (default/first)
        voices = engine.getProperty('voices')
        if voices:
            # Use first voice (typically male on Windows)
            engine.setProperty('voice', voices[0].id)
            
        engine.save_to_file(text, filename)
        engine.runAndWait()
    except Exception as e:
        print(f"Process TTS Error: {e}")

class TextToSpeech:
    """Text-to-speech handler using pyttsx3"""
    
    def __init__(self):
        self.engine = None
        # self.engine = pyttsx3.init() # Avoid init in main process if not needed exclusively
        self._initialize_engine()

    def _initialize_engine(self):
        """Initialize pyttsx3 engine for sync usage"""
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', config.TTS_RATE)
            self.engine.setProperty('volume', config.TTS_VOLUME)
            
            voices = self.engine.getProperty('voices')
            if voices:
                self.engine.setProperty('voice', voices[0].id)
            
            print("✓ Text-to-Speech initialized")
        except Exception as e:
            print(f"✗ TTS initialization error: {e}")
            self.engine = None
    
    def speak(self, text: str, voice_type: str = "male", return_audio: bool = True) -> str:
        """
        Convert text to speech and return as base64 audio
        """
        if not self.engine:
            print(f"TTS not available. Would say: {text}")
            return ""
        
        # Note: Changing properties here might conflict if using _speak_sync
        # but for text_to_audio_base64 we use the process which uses its own engine.
        
        if return_audio:
            return self.text_to_audio_base64(text)
        else:
            self._speak_sync(text)
            return ""
    
    def _speak_sync(self, text: str):
        """Speak synchronously (blocking) - fallback"""
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"TTS error: {e}")

    def text_to_audio_base64(self, text: str, language='en') -> str:
        """
        Convert text to speech using a separate process for stability.
        Returns base64 encoded WAV.
        """
        # Use a timeout for the process
        PROCESS_TIMEOUT = 5.0
        
        try:
            temp_dir = tempfile.gettempdir()
            filename = os.path.join(temp_dir, f"prime_tts_{uuid.uuid4()}.wav")
            
            # Create a separate process for TTS generation
            p = multiprocessing.Process(
                target=_generate_audio_file_process, 
                args=(text, filename, config.TTS_RATE, config.TTS_VOLUME)
            )
            p.start()
            p.join(PROCESS_TIMEOUT)
            
            if p.is_alive():
                print("⚠ TTS Process hung - killing")
                p.terminate()
                p.join()
                return ""
            
            # Read and encode if file exists
            if os.path.exists(filename):
                with open(filename, 'rb') as f:
                    audio_data = base64.b64encode(f.read()).decode('utf-8')
                
                try:
                    os.remove(filename)
                except:
                    pass
                return audio_data
            else:
                return ""
                
        except Exception as e:
            print(f"Error generating audio base64: {e}")
            return ""

    def stop(self):
        if self.engine:
            try:
                self.engine.stop()
            except:
                pass

    def set_rate(self, rate: int):
        if self.engine:
            self.engine.setProperty('rate', rate)

    def set_volume(self, volume: float):
        if self.engine:
            volume = max(0.0, min(1.0, volume))
            self.engine.setProperty('volume', volume)

    def get_voices(self):
        if self.engine:
            voices = self.engine.getProperty('voices')
            return [{"id": v.id, "name": v.name} for v in voices]
        return []

    def set_voice(self, voice_id: str):
        if self.engine:
            self.engine.setProperty('voice', voice_id)

    def save_to_file(self, text: str, filename: str):
        # Use the process method for safer file saving too?
        # For now, keep as is for legacy/sync usage, or use process
        pass

# Global TTS instance
tts = TextToSpeech()
