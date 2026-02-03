"""
Speaker Identification Module
Uses Resemblyzer (Deep Learning) to identify the speaker.
"""
import os
import numpy as np
import json
from pathlib import Path
import config

try:
    from resemblyzer import VoiceEncoder, preprocess_wav
    RESEMB_AVAILABLE = True
except ImportError:
    RESEMB_AVAILABLE = False
    print("⚠ Resemblyzer/Torch not installed. Speaker ID will be disabled.")

class SpeakerRecognizer:
    def __init__(self):
        self.encoder = None
        self.owner_embedding = None
        self.is_available = RESEMB_AVAILABLE
        self.embeddings_path = config.BASE_DIR / "models" / "owner_voice.npy"
        
        if self.is_available:
            try:
                print("⏳ Loading Voice Encoder Model (this may take a moment)...")
                self.encoder = VoiceEncoder()
                print("✓ Voice Encoder loaded")
                self._load_embedding()
            except Exception as e:
                print(f"❌ Failed to load Voice Encoder: {e}")
                self.is_available = False

    def _load_embedding(self):
        """Load saved owner embedding"""
        if self.embeddings_path.exists():
            try:
                self.owner_embedding = np.load(self.embeddings_path)
                print("✓ Owner voice profile loaded")
            except Exception as e:
                print(f"⚠ Could not load voice profile: {e}")

    def enroll_voice(self, audio_data: bytes) -> dict:
        """
        Create a voice profile from audio data
        Args:
            audio_data: Raw PCM audio bytes
        """
        if not self.is_available:
            return {"success": False, "error": "Module not available"}

        try:
            # Preprocess is usually for file paths or librosa loaded audio
            # We need to convert bytes to float32 numpy array
            # Assuming 16kHz mono 16-bit PCM (standard for Vosk/Microphone)
            audio_float = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Generate embedding
            embedding = self.encoder.embed_utterance(audio_float)
            
            # Save
            self.embeddings_path.parent.mkdir(parents=True, exist_ok=True)
            np.save(self.embeddings_path, embedding)
            self.owner_embedding = embedding
            
            return {
                "success": True, 
                "message": "Voice profile created successfully."
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def verify_voice(self, audio_data: bytes, threshold: float = 0.75) -> dict:
        """
        Verify if the audio matches the owner
        """
        if not self.is_available:
            # If not available, we can't verify, so we default to True (Owner) or False
            # For now, let's strictly fail if feature is requested but broken
            return {"match": False, "similarity": 0.0, "error": "Module not available"}
        
        if self.owner_embedding is None:
            return {"match": False, "similarity": 0.0, "error": "No voice profile enrolled"}

        try:
            # Convert bytes to float array
            audio_float = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Create embedding for input
            input_embedding = self.encoder.embed_utterance(audio_float)
            
            # Compute cosine similarity
            similarity = np.dot(self.owner_embedding, input_embedding) / (
                np.linalg.norm(self.owner_embedding) * np.linalg.norm(input_embedding)
            )
            
            is_match = similarity > threshold
            
            return {
                "match": bool(is_match),
                "similarity": float(similarity),
                "threshold": threshold
            }
            
        except Exception as e:
            print(f"Verification error: {e}")
            return {"match": False, "similarity": 0.0, "error": str(e)}

# Global instance
speaker_recognizer = SpeakerRecognizer()
