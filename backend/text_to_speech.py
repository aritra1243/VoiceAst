"""
Text-to-Speech module using pyttsx3 (offline)
"""
import pyttsx3
import threading
from queue import Queue
import config

class TextToSpeech:
    """Text-to-speech handler using pyttsx3"""
    
    def __init__(self):
        self.engine = None
        self.speech_queue = Queue()
        self.is_running = False
        self.thread = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize pyttsx3 engine"""
        try:
            self.engine = pyttsx3.init()
            
            # Configure voice settings
            self.engine.setProperty('rate', config.TTS_RATE)
            self.engine.setProperty('volume', config.TTS_VOLUME)
            
            # Set male voice (usually index 0 is male on Windows)
            voices = self.engine.getProperty('voices')
            if voices:
                # Use first voice (typically male on Windows)
                self.engine.setProperty('voice', voices[0].id)
                print(f"✓ Using voice: {voices[0].name}")
            
            print("✓ Text-to-Speech initialized")
            
        except Exception as e:
            print(f"✗ TTS initialization error: {e}")
            self.engine = None
    
    def speak(self, text: str, voice_type: str = "male", return_audio: bool = True) -> str:
        """
        Convert text to speech and return as base64 audio
        
        Args:
            text: Text to speak
            voice_type: 'male' or 'female' voice
            return_audio: If True, return base64 audio string
        
        Returns:
            Base64 encoded audio data (or empty string if return_audio is False)
        """
        if not self.engine:
            print(f"TTS not available. Would say: {text}")
            return ""
        
        # Set voice based on type
        voices = self.engine.getProperty('voices')
        if voices:
            if voice_type == "female" and len(voices) > 1:
                self.engine.setProperty('voice', voices[1].id)
            else:
                self.engine.setProperty('voice', voices[0].id)
        
        # Use faster rate for responsiveness
        self.engine.setProperty('rate', 180)
        
        if return_audio:
            return self.text_to_audio_base64(text)
        else:
            self._speak_sync(text)
            return ""
    
    def _speak_sync(self, text: str):
        """Speak synchronously (blocking)"""
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"TTS error: {e}")
    
    def _start_worker(self):
        """Start background worker for async speech"""
        if self.thread and self.thread.is_alive():
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()
    
    def _worker(self):
        """Background worker to process speech queue"""
        while self.is_running:
            try:
                if not self.speech_queue.empty():
                    text = self.speech_queue.get(timeout=1)
                    self._speak_sync(text)
                    self.speech_queue.task_done()
                else:
                    # No items in queue, stop worker
                    self.is_running = False
            except Exception as e:
                print(f"TTS worker error: {e}")
    
    def stop(self):
        """Stop current speech"""
        if self.engine:
            try:
                self.engine.stop()
            except:
                pass
    
    def set_rate(self, rate: int):
        """Set speech rate (words per minute)"""
        if self.engine:
            self.engine.setProperty('rate', rate)
    
    def set_volume(self, volume: float):
        """Set volume (0.0 to 1.0)"""
        if self.engine:
            volume = max(0.0, min(1.0, volume))
            self.engine.setProperty('volume', volume)
    
    def get_voices(self):
        """Get available voices"""
        if self.engine:
            voices = self.engine.getProperty('voices')
            return [{"id": v.id, "name": v.name} for v in voices]
        return []
    
    def set_voice(self, voice_id: str):
        """Set voice by ID"""
        if self.engine:
            self.engine.setProperty('voice', voice_id)
    
    def save_to_file(self, text: str, filename: str):
        """Save speech to audio file"""
        if not self.engine:
            return False
        
        try:
            self.engine.save_to_file(text, filename)
            self.engine.runAndWait()
            return True
        except Exception as e:
            print(f"Error saving audio file: {e}")
            return False
    
    def text_to_audio_base64(self, text: str, language='en') -> str:
        """
        Convert text to speech and return as base64 encoded WAV
        
        Args:
            text: Text to convert
            language: Language code ('en' or 'hi')
        
        Returns:
            Base64 encoded audio data
        """
        import base64
        import os
        import uuid
        import tempfile
        
        if not self.engine:
            return ""
        
        try:
            # Create temp file
            temp_dir = tempfile.gettempdir()
            filename = os.path.join(temp_dir, f"prime_tts_{uuid.uuid4()}.wav")
            
            # Generate audio file
            self.save_to_file(text, filename)
            
            # Read and encode
            with open(filename, 'rb') as f:
                audio_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Clean up
            try:
                os.remove(filename)
            except:
                pass
            
            return audio_data
            
        except Exception as e:
            print(f"Error generating audio base64: {e}")
            return ""

# Global TTS instance
tts = TextToSpeech()
