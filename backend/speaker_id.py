"""
Speaker Identification Module
Uses a custom-trained LSTM d-vector encoder (replaces Resemblyzer).
No external dependencies -- fully local inference.
"""
import os
import sys
import numpy as np
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import config

# --- PyTorch + librosa --------------------------------------------------------
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("[WRN] PyTorch not installed. Speaker ID will be disabled.")

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    print("[WRN] librosa not installed. MFCC extraction unavailable.")


# --- Model definition (must match train_speaker_model.py) ---------------------
MFCC_DIM   = 40
HIDDEN_DIM = 128   # must match train_speaker_model.py defaults
EMBED_DIM  = 128
N_LAYERS   = 2


class SpeakerEncoder(nn.Module):
    """LSTM-based d-vector encoder (mirrors training architecture)."""
    def __init__(self, input_dim=MFCC_DIM, hidden_dim=HIDDEN_DIM,
                 embed_dim=EMBED_DIM, n_layers=N_LAYERS):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=n_layers,
            batch_first=True,
            dropout=0.2 if n_layers > 1 else 0.0,
        )
        self.fc = nn.Linear(hidden_dim, embed_dim)

    def forward(self, x):
        out, _ = self.lstm(x)
        last   = out[:, -1, :]
        emb    = self.fc(last)
        return nn.functional.normalize(emb, dim=-1)


# --- MFCC extraction ----------------------------------------------------------
def _bytes_to_mfcc(audio_data: bytes, sr=16000, n_mfcc=MFCC_DIM, max_frames=200):
    """
    Convert raw 16-bit PCM bytes -> MFCC tensor (1, T, 40).
    Falls back to simple numpy approach if librosa unavailable.
    """
    audio_float = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

    if LIBROSA_AVAILABLE:
        mfcc = librosa.feature.mfcc(y=audio_float, sr=sr, n_mfcc=n_mfcc).T
        mfcc = (mfcc - mfcc.mean(0)) / (mfcc.std(0) + 1e-9)
    else:
        # Rough approximation: split into frames of 512 and compute log-energy
        frame_size = 512
        n_frames   = len(audio_float) // frame_size
        if n_frames == 0:
            n_frames = 1
        frames = np.array_split(audio_float[:n_frames * frame_size], n_frames)
        mfcc   = np.array([
            np.log(np.maximum(np.var(f), 1e-9)) *
            np.ones(n_mfcc, dtype=np.float32)
            for f in frames
        ])

    if len(mfcc) > max_frames:
        mfcc = mfcc[:max_frames]

    return torch.tensor(mfcc[np.newaxis], dtype=torch.float32)  # (1, T, 40)


# --- SpeakerRecognizer class --------------------------------------------------
class SpeakerRecognizer:
    """
    Speaker verification using a custom-trained LSTM d-vector encoder.
    Public API identical to the old Resemblyzer-based version:
        enroll_voice(audio_data: bytes) -> dict
        verify_voice(audio_data: bytes, threshold: float) -> dict
    """

    def __init__(self):
        self.encoder        = None
        self.owner_embedding = None
        self.is_available   = False
        self.embeddings_path = config.BASE_DIR / "models" / "owner_voice.npy"

        if not TORCH_AVAILABLE:
            print("[X] Speaker ID disabled -- PyTorch not installed.")
            return

        try:
            print("[...] Loading Speaker Encoder model...")
            self._load_encoder()
            self._load_embedding()
        except Exception as e:
            print(f"[ERR] Failed to load Speaker Encoder: {e}")
            print("   Run: python models_training/train_speaker_model.py")

    def _load_encoder(self):
        """Load trained LSTM encoder weights."""
        model_path = config.SPEAKER_MODEL_PATH

        if not model_path.exists():
            print(f"[WRN] Speaker model not found at {model_path}")
            print("  Run: python models_training/train_speaker_model.py")
            return

        checkpoint = torch.load(model_path, map_location="cpu", weights_only=True)

        # Support both raw state_dict and wrapped checkpoint formats
        if "model_state_dict" in checkpoint:
            cfg   = checkpoint.get("config", {})
            model = SpeakerEncoder(
                input_dim  = cfg.get("input_dim",  MFCC_DIM),
                hidden_dim = cfg.get("hidden_dim", HIDDEN_DIM),
                embed_dim  = cfg.get("embed_dim",  EMBED_DIM),
                n_layers   = cfg.get("n_layers",   N_LAYERS),
            )
            model.load_state_dict(checkpoint["model_state_dict"])
        else:
            model = SpeakerEncoder()
            model.load_state_dict(checkpoint)

        model.eval()
        self.encoder      = model
        self.is_available = True
        print("? Speaker Encoder loaded (custom LSTM d-vector)")

    def _load_embedding(self):
        """Load saved owner voice embedding."""
        if self.embeddings_path.exists():
            try:
                self.owner_embedding = np.load(self.embeddings_path)
                print("? Owner voice profile loaded")
            except Exception as e:
                print(f"[WRN] Could not load voice profile: {e}")

    def _embed(self, audio_data: bytes) -> np.ndarray:
        """Convert raw PCM bytes -> numpy embedding vector."""
        mfcc_tensor = _bytes_to_mfcc(audio_data)
        with torch.no_grad():
            emb = self.encoder(mfcc_tensor)  # (1, 256)
        return emb.squeeze(0).numpy()

    # -- Public API -------------------------------------------------------------

    def enroll_voice(self, audio_data: bytes) -> dict:
        """
        Create a voice profile from audio data.
        Args:
            audio_data: Raw 16-bit PCM bytes @ 16kHz mono
        """
        if not self.is_available:
            return {"success": False, "error": "Module not available"}
        try:
            embedding = self._embed(audio_data)
            self.embeddings_path.parent.mkdir(parents=True, exist_ok=True)
            np.save(self.embeddings_path, embedding)
            self.owner_embedding = embedding
            return {"success": True, "message": "Voice profile created successfully."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def verify_voice(self, audio_data: bytes, threshold: float = 0.75) -> dict:
        """
        Verify if the audio matches the enrolled owner voice.
        Returns similarity score (cosine) and match boolean.
        """
        if not self.is_available:
            return {"match": False, "similarity": 0.0, "error": "Module not available"}
        if self.owner_embedding is None:
            return {"match": False, "similarity": 0.0, "error": "No voice profile enrolled"}
        try:
            input_emb = self._embed(audio_data)
            similarity = float(np.dot(self.owner_embedding, input_emb) / (
                np.linalg.norm(self.owner_embedding) * np.linalg.norm(input_emb) + 1e-9
            ))
            return {
                "match":      bool(similarity > threshold),
                "similarity": similarity,
                "threshold":  threshold,
            }
        except Exception as e:
            print(f"Verification error: {e}")
            return {"match": False, "similarity": 0.0, "error": str(e)}


# Global instance
speaker_recognizer = SpeakerRecognizer()
