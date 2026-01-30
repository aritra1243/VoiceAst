"""
Voice recognition module using Vosk (offline speech recognition)
"""
import json
import queue
import config

# Optional imports - gracefully handle if not installed
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    print("sounddevice not installed - microphone input will be unavailable")

try:
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    print("vosk not installed - offline voice recognition will be unavailable")

class VoiceRecognition:
    """Offline voice recognition using Vosk"""
    
    def __init__(self):
        self.model = None
        self.recognizer = None
        self.sample_rate = 16000
        self.is_initialized = False
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize Vosk model"""
        if not VOSK_AVAILABLE:
            print("✗ Vosk not installed - voice recognition unavailable")
            print("  Install with: pip install vosk sounddevice numpy")
            print("  App will use browser's speech recognition as fallback")
            self.is_initialized = False
            return
        
        try:
            model_path = str(config.VOSK_MODEL_PATH)
            print(f"Loading Vosk model from: {model_path}")
            
            self.model = Model(model_path)
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
            self.is_initialized = True
            
            print("✓ Voice recognition initialized")
            
        except Exception as e:
            print(f"✗ Vosk initialization error: {e}")
            print(f"  Please ensure model is downloaded to: {config.VOSK_MODEL_PATH}")
            print(f"  Run: python setup.py")
            print(f"  App will use browser's speech recognition as fallback")
            self.is_initialized = False
    
    def create_recognizer(self):
        """Create a new KaldiRecognizer instance"""
        if not self.is_initialized:
            return None
        return KaldiRecognizer(self.model, self.sample_rate)

    def process_chunk(self, recognizer, audio_chunk: bytes) -> dict:
        """
        Process a single chunk of audio with an existing recognizer
        """
        if not recognizer:
            return {}
            
        if recognizer.AcceptWaveform(audio_chunk):
            result = json.loads(recognizer.Result())
            text = result.get("text", "")
            if text:
                return {"text": text, "is_final": True}
        else:
            # Partial result (optional to return)
            partial = json.loads(recognizer.PartialResult())
            if partial.get("partial"):
                return {"text": partial["partial"], "is_final": False}
                
        return {}

    def recognize_from_audio(self, audio_data: bytes) -> dict:
        """
        Recognize speech from audio data (One-shot)
        
        Args:
            audio_data: Raw audio bytes (16-bit PCM, 16kHz)
        
        Returns:
            dict with 'text' and 'confidence' keys
        """
        if not self.is_initialized:
            return {"text": "", "confidence": 0.0, "error": "Model not initialized"}
        
        try:
            # Reset recognizer for new recognition
            rec = self.create_recognizer()
            if not rec:
                 return {"text": "", "confidence": 0.0, "error": "Could not create recognizer"}

            # Process audio
            if rec.AcceptWaveform(audio_data):
                result = json.loads(rec.Result())
            else:
                result = json.loads(rec.PartialResult())
            
            text = result.get("text", "")
            
            return {
                "text": text,
                "confidence": 1.0 if text else 0.0,
                "partial": "partial" in result
            }
            
        except Exception as e:
            print(f"Recognition error: {e}")
            return {"text": "", "confidence": 0.0, "error": str(e)}
    
    def recognize_from_microphone(self, duration: int = 5) -> dict:
        """
        Record from microphone and recognize speech
        
        Args:
            duration: Recording duration in seconds
        
        Returns:
            dict with recognition results
        """
        if not self.is_initialized:
            return {"text": "", "confidence": 0.0, "error": "Model not initialized"}
        
        if not SOUNDDEVICE_AVAILABLE:
            return {"text": "", "confidence": 0.0, "error": "sounddevice not installed"}
        
        try:
            print(f"Recording for {duration} seconds...")
            
            # Record audio
            audio_queue = queue.Queue()
            
            def audio_callback(indata, frames, time, status):
                if status:
                    print(f"Audio status: {status}")
                audio_queue.put(bytes(indata))
            
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=8000,
                dtype='int16',
                channels=1,
                callback=audio_callback
            ):
                # Reset recognizer
                self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
                
                # Process audio chunks
                import time
                start_time = time.time()
                
                while time.time() - start_time < duration:
                    data = audio_queue.get()
                    if self.recognizer.AcceptWaveform(data):
                        pass
                
                # Get final result
                result = json.loads(self.recognizer.FinalResult())
                text = result.get("text", "")
                
                return {
                    "text": text,
                    "confidence": 1.0 if text else 0.0
                }
                
        except Exception as e:
            print(f"Microphone recognition error: {e}")
            return {"text": "", "confidence": 0.0, "error": str(e)}
    
    def process_stream(self, audio_stream):
        """
        Process continuous audio stream
        
        Args:
            audio_stream: Generator yielding audio chunks
        
        Yields:
            Recognition results as they become available
        """
        if not self.is_initialized:
            yield {"text": "", "confidence": 0.0, "error": "Model not initialized"}
            return
        
        try:
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
            
            for audio_chunk in audio_stream:
                if self.recognizer.AcceptWaveform(audio_chunk):
                    result = json.loads(self.recognizer.Result())
                    if result.get("text"):
                        yield {
                            "text": result["text"],
                            "confidence": 1.0,
                            "final": True
                        }
                else:
                    result = json.loads(self.recognizer.PartialResult())
                    if result.get("partial"):
                        yield {
                            "text": result["partial"],
                            "confidence": 0.5,
                            "final": False
                        }
                        
        except Exception as e:
            print(f"Stream processing error: {e}")
            yield {"text": "", "confidence": 0.0, "error": str(e)}

# Global voice recognition instance
voice_recognition = VoiceRecognition()
