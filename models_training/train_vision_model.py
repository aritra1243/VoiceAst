"""
Train Custom Vision Caption Model -- replaces Ollama LLaVA
Architecture: EfficientNet-B0 (frozen ImageNet backbone) + LSTM caption decoder
  - Feature extractor : EfficientNet-B0 -> 1280-dim image embedding
  - Caption decoder   : Embedding -> LSTM -> word probabilities
  - Training data     : COCO Captions 2017 (auto-downloaded, ~1.5GB)
  - Metric            : BLEU-4 score; best epoch saved to saved_models/

NOTE: Requires internet for first run (COCO download). After that, fully offline.
"""
import json
import sys
import os
import re
import time
import math
import random
import zipfile
import urllib.request
from pathlib import Path
from datetime import datetime
from collections import Counter

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# --- Paths --------------------------------------------------------------------
SCRIPT_DIR   = Path(__file__).parent
DATASETS_DIR = SCRIPT_DIR / "datasets"
SAVED_DIR    = SCRIPT_DIR / "saved_models"
LOGS_DIR     = SCRIPT_DIR / "training_logs"
COCO_DIR     = DATASETS_DIR / "coco"
RESULTS_PATH = LOGS_DIR / "training_results.json"
MODEL_PATH   = SAVED_DIR / "vision_model.pth"
VOCAB_PATH   = SAVED_DIR / "vision_vocab.json"

for d in (DATASETS_DIR, SAVED_DIR, LOGS_DIR, COCO_DIR):
    d.mkdir(parents=True, exist_ok=True)

# --- Dependency checks --------------------------------------------------------
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    TORCH_OK = True
except ImportError:
    print("[ERR] PyTorch not installed. Run: pip install torch torchvision")
    TORCH_OK = False

try:
    import torchvision
    import torchvision.transforms as T
    from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights
    TORCHVISION_OK = True
except ImportError:
    print("[ERR] torchvision not installed. Run: pip install torchvision")
    TORCHVISION_OK = False

try:
    from PIL import Image
    PIL_OK = True
except ImportError:
    print("[ERR] Pillow not installed. Run: pip install Pillow")
    PIL_OK = False


# --- COCO downloader ---------------------------------------------------------
COCO_URLS = {
    "annotations": "http://images.cocodataset.org/annotations/annotations_trainval2017.zip",
    "images_train": "http://images.cocodataset.org/zips/train2017.zip",
}


def _download_with_progress(url: str, dest: Path):
    """Download a file showing progress."""
    if dest.exists():
        print(f"   Already downloaded: {dest.name}")
        return
    print(f"   Downloading {dest.name} ...")

    def _progress(count, block_size, total_size):
        pct = min(int(count * block_size * 100 / max(total_size, 1)), 100)
        bar = "#" * (pct // 5)
        print(f"\r   [{bar:<20}] {pct}%", end="", flush=True)

    urllib.request.urlretrieve(url, dest, reporthook=_progress)
    print()


def download_coco(max_images=10000):
    """
    Download COCO annotations + a subset of training images.
    max_images: cap on how many images to download (full set = ~118k).
    """
    ann_zip  = COCO_DIR / "annotations.zip"
    ann_dir  = COCO_DIR / "annotations"
    img_dir  = COCO_DIR / "train2017"

    # Download annotations
    _download_with_progress(COCO_URLS["annotations"], ann_zip)
    if not ann_dir.exists():
        print("   Extracting annotations ...")
        with zipfile.ZipFile(ann_zip) as z:
            z.extractall(COCO_DIR)

    captions_file = ann_dir / "captions_train2017.json"
    if not captions_file.exists():
        raise FileNotFoundError(f"Captions file not found: {captions_file}")

    with open(captions_file) as f:
        coco = json.load(f)

    # Build image_id -> file_name map
    id2file = {img["id"]: img["file_name"] for img in coco["images"]}

    # Build list of (filename, caption) up to max_images
    pairs = []
    seen_ids = set()
    for ann in coco["annotations"]:
        img_id   = ann["image_id"]
        filename = id2file.get(img_id)
        if filename and img_id not in seen_ids:
            pairs.append((filename, ann["caption"]))
            seen_ids.add(img_id)
        if len(pairs) >= max_images:
            break

    # Download images (only those in pairs, partial download)
    img_dir.mkdir(exist_ok=True)
    needed = {fname for fname, _ in pairs}
    existing = {p.name for p in img_dir.glob("*.jpg")}
    to_download = needed - existing
    print(f"   Images needed: {len(needed)}, already downloaded: {len(existing)}, "
          f"downloading: {len(to_download)}")

    base_url = "http://images.cocodataset.org/train2017/"
    for i, fname in enumerate(sorted(to_download)):
        dest = img_dir / fname
        try:
            urllib.request.urlretrieve(base_url + fname, dest)
        except Exception as e:
            pass  # Skip failed downloads
        if (i + 1) % 500 == 0:
            print(f"   ... {i+1}/{len(to_download)} images downloaded")

    # Filter pairs to only images we have
    existing_now = {p.name for p in img_dir.glob("*.jpg")}
    pairs = [(f, c) for f, c in pairs if f in existing_now]
    print(f"   Final usable pairs: {len(pairs)}")
    return pairs, img_dir


# --- Vocabulary ---------------------------------------------------------------
PAD, SOS, EOS, UNK = "<PAD>", "<SOS>", "<EOS>", "<UNK>"

def build_vocab(captions: list, min_freq=3) -> dict:
    counter = Counter()
    for cap in captions:
        counter.update(cap.lower().split())
    vocab = {PAD: 0, SOS: 1, EOS: 2, UNK: 3}
    for word, freq in counter.most_common():
        if freq >= min_freq:
            vocab[word] = len(vocab)
    return vocab

def tokenise(caption: str, vocab: dict, max_len=25) -> list:
    tokens = [vocab.get(SOS)]
    for w in caption.lower().split()[:max_len - 2]:
        tokens.append(vocab.get(w, vocab[UNK]))
    tokens.append(vocab.get(EOS))
    # Pad
    tokens += [vocab[PAD]] * (max_len - len(tokens))
    return tokens[:max_len]


# --- Dataset -----------------------------------------------------------------
class COCOCaptionDataset(Dataset):
    def __init__(self, pairs: list, img_dir: Path, vocab: dict, transform=None, max_len=25):
        self.pairs    = pairs
        self.img_dir  = img_dir
        self.vocab    = vocab
        self.max_len  = max_len
        self.transform = transform or T.Compose([
            T.Resize((224, 224)),
            T.ToTensor(),
            T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, idx):
        fname, caption = self.pairs[idx]
        img_path = self.img_dir / fname
        try:
            img = Image.open(img_path).convert("RGB")
        except Exception:
            img = Image.new("RGB", (224, 224))
        img    = self.transform(img)
        tokens = torch.tensor(tokenise(caption, self.vocab, self.max_len), dtype=torch.long)
        return img, tokens


# --- Model --------------------------------------------------------------------
EMBED_DIM  = 256
HIDDEN_DIM = 512
MAX_LEN    = 25
FEAT_DIM   = 1280  # EfficientNet-B0 output


class CaptionModel(nn.Module):
    """
    EfficientNet-B0 feature extractor + LSTM caption decoder.
    """
    def __init__(self, vocab_size: int, embed_dim=EMBED_DIM,
                 hidden_dim=HIDDEN_DIM, feat_dim=FEAT_DIM):
        super().__init__()
        self.feat_proj  = nn.Linear(feat_dim, hidden_dim)
        self.embed      = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.lstm       = nn.LSTM(embed_dim, hidden_dim, batch_first=True)
        self.fc         = nn.Linear(hidden_dim, vocab_size)

    def forward(self, features, captions):
        """
        features: (B, feat_dim)
        captions: (B, max_len)  -- teacher-forced
        """
        h0 = self.feat_proj(features).unsqueeze(0)  # (1, B, H)
        c0 = torch.zeros_like(h0)
        emb = self.embed(captions[:, :-1])           # (B, T-1, E)
        out, _ = self.lstm(emb, (h0, c0))            # (B, T-1, H)
        logits = self.fc(out)                         # (B, T-1, V)
        return logits

    def generate(self, feature, vocab_inv: dict, max_len=MAX_LEN, device="cpu"):
        """Greedy decode a caption from an image feature vector."""
        self.eval()
        sos_id = {v: k for k, v in vocab_inv.items()}.get(SOS, 1)
        eos_id = {v: k for k, v in vocab_inv.items()}.get(EOS, 2)
        h = self.feat_proj(feature.unsqueeze(0)).unsqueeze(0)
        c = torch.zeros_like(h)
        inp = torch.tensor([[sos_id]], device=device)
        words = []
        with torch.no_grad():
            for _ in range(max_len):
                emb = self.embed(inp)
                out, (h, c) = self.lstm(emb, (h, c))
                logit = self.fc(out.squeeze(1))
                tok   = logit.argmax(-1).item()
                if tok == eos_id:
                    break
                word = vocab_inv.get(tok, UNK)
                if word not in (PAD, SOS, EOS, UNK):
                    words.append(word)
                inp = torch.tensor([[tok]], device=device)
        return " ".join(words)


# --- BLEU-4 -------------------------------------------------------------------
def bleu4(hypothesis: list, reference: list) -> float:
    """Corpus-level BLEU-4 (simplified)."""
    score = 0.0
    for hyp, ref in zip(hypothesis, reference):
        h_tokens = hyp.lower().split()
        r_tokens = ref.lower().split()
        if not h_tokens:
            continue
        bp = min(1.0, math.exp(1 - len(r_tokens) / max(len(h_tokens), 1)))
        ngram_score = 1.0
        for n in range(1, 5):
            h_ngrams = Counter(tuple(h_tokens[i:i+n]) for i in range(len(h_tokens)-n+1))
            r_ngrams = Counter(tuple(r_tokens[i:i+n]) for i in range(len(r_tokens)-n+1))
            match  = sum((h_ngrams & r_ngrams).values())
            total  = max(sum(h_ngrams.values()), 1)
            ngram_score *= (match / total) ** (1/4)
        score += bp * ngram_score
    return score / max(len(hypothesis), 1)


# --- Training loop ------------------------------------------------------------
def train(n_epochs=10, batch_size=32, lr=1e-3, max_images=8000, max_len=MAX_LEN):
    if not (TORCH_OK and TORCHVISION_OK and PIL_OK):
        return {"error": "Missing dependencies"}

    print("=" * 60)
    print("  VISION CAPTION MODEL TRAINING")
    print("=" * 60)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n   Device: {device}")

    # 1. Download COCO data
    print("\n[DL] Downloading COCO Captions (first run only) ...")
    try:
        pairs, img_dir = download_coco(max_images=max_images)
    except Exception as e:
        print(f"[ERR] COCO download failed: {e}")
        return {"error": str(e)}

    if not pairs:
        return {"error": "No COCO pairs available"}

    # 2. Build vocabulary
    print("\n[VOC] Building vocabulary ...")
    all_captions = [c for _, c in pairs]
    vocab = build_vocab(all_captions)
    vocab_inv = {v: k for k, v in vocab.items()}
    print(f"   Vocabulary size: {len(vocab)}")

    # Save vocab
    with open(VOCAB_PATH, "w") as f:
        json.dump(vocab, f)

    # 3. Dataset + DataLoader
    random.shuffle(pairs)
    split = int(0.9 * len(pairs))
    train_pairs = pairs[:split]
    val_pairs   = pairs[split:]

    train_ds = COCOCaptionDataset(train_pairs, img_dir, vocab, max_len=max_len)
    val_ds   = COCOCaptionDataset(val_pairs,   img_dir, vocab, max_len=max_len)
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True,
                          num_workers=0, pin_memory=False)
    val_dl   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False,
                          num_workers=0, pin_memory=False)

    # 4. Feature extractor (frozen EfficientNet-B0)
    print("\n[BLD]  Loading EfficientNet-B0 feature extractor ...")
    backbone = efficientnet_b0(weights=EfficientNet_B0_Weights.DEFAULT)
    backbone.classifier = nn.Identity()   # remove classification head -> 1280-dim
    backbone = backbone.to(device)
    backbone.eval()
    for p in backbone.parameters():
        p.requires_grad = False

    # 5. Caption model
    caption_model = CaptionModel(vocab_size=len(vocab)).to(device)
    optimizer = optim.Adam(caption_model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss(ignore_index=0)

    best_bleu  = 0.0
    best_state = None

    print(f"\n[TRN]  Training caption decoder for {n_epochs} epochs ...\n")
    for epoch in range(1, n_epochs + 1):
        caption_model.train()
        total_loss = 0.0
        n_batches  = 0
        for imgs, tokens in train_dl:
            imgs   = imgs.to(device)
            tokens = tokens.to(device)
            with torch.no_grad():
                feats = backbone(imgs)         # (B, 1280)
            logits = caption_model(feats, tokens)   # (B, T-1, V)
            targets = tokens[:, 1:].reshape(-1)
            loss = criterion(logits.reshape(-1, len(vocab)), targets)
            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(caption_model.parameters(), 5.0)
            optimizer.step()
            total_loss += loss.item()
            n_batches  += 1

        avg_loss = total_loss / max(n_batches, 1)

        # Validation BLEU
        caption_model.eval()
        hyps, refs = [], []
        for imgs, tokens in val_dl:
            imgs = imgs.to(device)
            with torch.no_grad():
                feats = backbone(imgs)
            for i in range(len(imgs)):
                hyp = caption_model.generate(feats[i], vocab_inv, device=str(device))
                ref_ids = tokens[i].tolist()
                ref = " ".join(vocab_inv.get(t, "") for t in ref_ids
                               if t not in (0, 1, 2))
                hyps.append(hyp)
                refs.append(ref)
            if len(hyps) >= 200:
                break

        bleu = bleu4(hyps, refs)
        marker = " <- best" if bleu > best_bleu else ""
        print(f"  Epoch {epoch:2d}/{n_epochs} | Loss: {avg_loss:.4f} | BLEU-4: {bleu:.4f}{marker}")

        if bleu > best_bleu:
            best_bleu  = bleu
            best_state = {k: v.cpu().clone() for k, v in caption_model.state_dict().items()}

    # 6. Save best model
    if best_state is None:
        best_state = {k: v.cpu().clone() for k, v in caption_model.state_dict().items()}

    save_dict = {
        "model_state_dict": best_state,
        "config": {
            "vocab_size": len(vocab),
            "embed_dim":  EMBED_DIM,
            "hidden_dim": HIDDEN_DIM,
            "feat_dim":   FEAT_DIM,
            "max_len":    max_len,
        },
    }
    torch.save(save_dict, MODEL_PATH)
    print(f"\n[SAV] Best model saved -> {MODEL_PATH}")
    print(f"   Vocabulary  saved -> {VOCAB_PATH}")
    print(f"   Best BLEU-4: {best_bleu:.4f}")

    # 7. Log results
    results = {}
    if RESULTS_PATH.exists():
        with open(RESULTS_PATH) as f:
            results = json.load(f)

    results["vision_model"] = {
        "trained_at":  datetime.now().isoformat(),
        "n_pairs":     len(pairs),
        "vocab_size":  len(vocab),
        "best_bleu4":  float(best_bleu),
        "n_epochs":    n_epochs,
        "architecture": {"backbone": "EfficientNet-B0", "decoder": "LSTM",
                         "embed_dim": EMBED_DIM, "hidden_dim": HIDDEN_DIM},
    }
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n[LOG] Results logged to: {RESULTS_PATH}")
    print("=" * 60)
    print(f"  DONE -- Best BLEU-4: {best_bleu:.4f}")
    print("=" * 60)
    return results["vision_model"]


if __name__ == "__main__":
    train()
