"""
Vision Recognition Module
Uses a locally-trained EfficientNet-B0 + LSTM caption model.
Replaces Ollama LLaVA -- no external services required.
"""
import base64
import json
import sys
import io
from pathlib import Path
from typing import Optional, Dict

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import config

# --- Dependency checks --------------------------------------------------------
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("[WRN] PyTorch not installed. Vision features disabled.")

try:
    import torchvision.transforms as T
    from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights
    TORCHVISION_AVAILABLE = True
except ImportError:
    TORCHVISION_AVAILABLE = False
    print("[WRN] torchvision not installed. Vision features disabled.")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("[WRN] Pillow not installed. Vision features disabled.")

import asyncio


# --- Model definition (mirrors train_vision_model.py) ------------------------
PAD, SOS, EOS, UNK = "<PAD>", "<SOS>", "<EOS>", "<UNK>"
EMBED_DIM  = 256
HIDDEN_DIM = 512
FEAT_DIM   = 1280   # EfficientNet-B0 output
MAX_LEN    = 25


class CaptionModel(nn.Module):
    """EfficientNet-B0 feature extractor + LSTM caption decoder."""
    def __init__(self, vocab_size: int, embed_dim=EMBED_DIM,
                 hidden_dim=HIDDEN_DIM, feat_dim=FEAT_DIM):
        super().__init__()
        self.feat_proj = nn.Linear(feat_dim, hidden_dim)
        self.embed     = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.lstm      = nn.LSTM(embed_dim, hidden_dim, batch_first=True)
        self.fc        = nn.Linear(hidden_dim, vocab_size)

    def forward(self, features, captions):
        h0  = self.feat_proj(features).unsqueeze(0)
        c0  = torch.zeros_like(h0)
        emb = self.embed(captions[:, :-1])
        out, _ = self.lstm(emb, (h0, c0))
        return self.fc(out)

    @torch.no_grad()
    def generate(self, feature, vocab_inv: dict,
                 max_len: int = MAX_LEN, device: str = "cpu") -> str:
        """Greedy-decode a caption from a single image feature vector."""
        sos_id = {v: k for k, v in vocab_inv.items()}.get(SOS, 1)
        eos_id = {v: k for k, v in vocab_inv.items()}.get(EOS, 2)
        h = self.feat_proj(feature.unsqueeze(0)).unsqueeze(0)
        c = torch.zeros_like(h)
        inp = torch.tensor([[sos_id]], device=device)
        words = []
        for _ in range(max_len):
            emb = self.embed(inp)
            out, (h, c) = self.lstm(emb, (h, c))
            tok = self.fc(out.squeeze(1)).argmax(-1).item()
            if tok == eos_id:
                break
            word = vocab_inv.get(tok, UNK)
            if word not in (PAD, SOS, EOS, UNK):
                words.append(word)
            inp = torch.tensor([[tok]], device=device)
        return " ".join(words) if words else "A scene is visible."


# --- Image transform ----------------------------------------------------------
_TRANSFORM = None

def _get_transform():
    global _TRANSFORM
    if _TRANSFORM is None and TORCHVISION_AVAILABLE:
        _TRANSFORM = T.Compose([
            T.Resize((224, 224)),
            T.ToTensor(),
            T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
    return _TRANSFORM


# --- VisionRecognition class -------------------------------------------------
class VisionRecognition:
    """
    Vision recognition using a locally-trained EfficientNet-B0 + LSTM model.
    Public API identical to the old Ollama-based version:
        analyze_image(image_base64, prompt) -> dict
        identify_objects(image_base64)      -> dict
        describe_scene(image_base64)        -> dict
        read_text(image_base64)             -> dict
    """

    def __init__(self):
        self.backbone      = None
        self.caption_model = None
        self.vocab_inv     = {}
        self.device        = "cpu"
        self.is_available  = False
        self._load_models()

    def _load_models(self):
        """Load EfficientNet-B0 backbone and trained caption decoder."""
        if not all([TORCH_AVAILABLE, TORCHVISION_AVAILABLE, PIL_AVAILABLE]):
            print("[X] Vision model disabled -- missing PyTorch/torchvision/Pillow")
            return

        model_path = config.VISION_MODEL_PATH
        vocab_path = config.VISION_VOCAB_PATH

        if not model_path.exists() or not vocab_path.exists():
            print(f"[WRN] Vision model not found. Run: python models_training/train_vision_model.py")
            print(f"  Expected: {model_path}")
            return

        try:
            # Load vocabulary
            with open(vocab_path) as f:
                vocab = json.load(f)
            self.vocab_inv = {v: k for k, v in vocab.items()}

            # Load EfficientNet-B0 backbone (frozen)
            backbone = efficientnet_b0(weights=EfficientNet_B0_Weights.DEFAULT)
            backbone.classifier = nn.Identity()
            backbone.eval()
            for p in backbone.parameters():
                p.requires_grad = False
            self.backbone = backbone

            # Load caption decoder
            checkpoint = torch.load(model_path, map_location="cpu", weights_only=True)
            cfg = checkpoint.get("config", {})
            cap_model = CaptionModel(
                vocab_size  = cfg.get("vocab_size", len(vocab)),
                embed_dim   = cfg.get("embed_dim",  EMBED_DIM),
                hidden_dim  = cfg.get("hidden_dim", HIDDEN_DIM),
                feat_dim    = cfg.get("feat_dim",   FEAT_DIM),
            )
            cap_model.load_state_dict(checkpoint["model_state_dict"])
            cap_model.eval()
            self.caption_model = cap_model

            self.device       = "cuda" if torch.cuda.is_available() else "cpu"
            self.is_available = True
            print(f"? Vision model loaded (EfficientNet-B0 + LSTM, vocab={len(vocab)})")

        except Exception as e:
            print(f"[X] Error loading vision model: {e}")

    def _base64_to_tensor(self, image_base64: str):
        """Decode a base64 image string -> normalised tensor (1, 3, 224, 224)."""
        img_bytes = base64.b64decode(image_base64)
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        transform = _get_transform()
        if transform is None:
            raise RuntimeError("torchvision transform unavailable")
        tensor = transform(img).unsqueeze(0)  # (1, C, H, W)
        return tensor

    def _generate_caption(self, image_base64: str) -> str:
        """Run the full pipeline: base64 -> feature -> caption."""
        tensor = self._base64_to_tensor(image_base64)
        with torch.no_grad():
            feature = self.backbone(tensor.to(self.device)).squeeze(0)  # (1280,)
        caption = self.caption_model.generate(
            feature, self.vocab_inv, device=self.device
        )
        return caption

    # -- Public API (identical signatures to old Ollama version) ---------------

    async def analyze_image(self, image_base64: str, prompt: str = None) -> Dict:
        """
        Analyze an image and describe its contents.
        The `prompt` parameter is accepted for API compatibility but not used
        (caption model generates fixed-style descriptions).
        """
        if not self.is_available:
            return {
                "success": False,
                "description": "",
                "error": "Vision model not available. Run: python models_training/train_vision_model.py",
            }
        try:
            # Run CPU-bound inference off the event loop
            description = await asyncio.to_thread(self._generate_caption, image_base64)
            # Capitalise first letter
            if description:
                description = description[0].upper() + description[1:]
            return {"success": True, "description": description, "error": None}
        except Exception as e:
            print(f"Vision analysis error: {e}")
            return {"success": False, "description": "", "error": str(e)}

    async def identify_objects(self, image_base64: str) -> Dict:
        """Identify objects -- returns same description (model is caption-based)."""
        return await self.analyze_image(image_base64)

    async def describe_scene(self, image_base64: str) -> Dict:
        """Describe the scene in the image."""
        return await self.analyze_image(image_base64)

    async def read_text(self, image_base64: str) -> Dict:
        """
        Attempt to read text in the image.
        Note: the current model is a scene captioner, not an OCR system.
        For OCR, integrate pytesseract separately.
        """
        result = await self.analyze_image(image_base64)
        if result["success"] and not result["description"]:
            result["description"] = "No text detected."
        return result


# Global instance
vision = VisionRecognition()
