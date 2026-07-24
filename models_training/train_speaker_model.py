"""
Train Custom Speaker Embedding Model -- replaces Resemblyzer
Architecture: Small LSTM-based d-vector encoder (PyTorch)
  - Input : 40-dim MFCC frames (16kHz, mono)
  - Output: 256-dim L2-normalised speaker embedding
  - Loss  : Generalised end-to-end (GE2E) softmax loss / triplet loss
  - Saves best checkpoint (lowest EER) to saved_models/speaker_model.pth
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
import random

# --- Paths --------------------------------------------------------------------
SCRIPT_DIR  = Path(__file__).parent
SAMPLES_DIR = SCRIPT_DIR / "datasets" / "speaker_samples"
SAVED_DIR   = SCRIPT_DIR / "saved_models"
LOGS_DIR    = SCRIPT_DIR / "training_logs"
RESULTS_PATH = LOGS_DIR / "training_results.json"
MODEL_PATH  = SAVED_DIR / "speaker_model.pth"

for d in (SAMPLES_DIR, SAVED_DIR, LOGS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# --- PyTorch check ------------------------------------------------------------
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_OK = True
except ImportError:
    print("[ERR] PyTorch not installed. Run: pip install torch")
    TORCH_OK = False

try:
    import librosa
    LIBROSA_OK = True
except ImportError:
    print("[WRN] librosa not installed -- will use synthetic data only. Run: pip install librosa")
    LIBROSA_OK = False


# --- Model Architecture -------------------------------------------------------
MFCC_DIM   = 40
EMBED_DIM  = 128   # Small for CPU speed
HIDDEN_DIM = 128   # Small for CPU speed
N_LAYERS   = 2     # 2 layers for CPU speed
MAX_FRAMES = 30    # Short sequences -- enough for speaker ID


class SpeakerEncoder(nn.Module):
    """
    LSTM-based d-vector speaker encoder.
    Input : (batch, seq_len, MFCC_DIM)
    Output: (batch, EMBED_DIM)  -- L2 normalised
    """
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
        """
        x: (B, T, F)
        returns: (B, embed_dim) normalised
        """
        out, _ = self.lstm(x)
        # Use last time-step
        last = out[:, -1, :]
        emb  = self.fc(last)
        return nn.functional.normalize(emb, dim=-1)


# --- Synthetic data generator -------------------------------------------------
def _load_wav_mfcc(wav_path: Path, sr=16000, n_mfcc=MFCC_DIM, max_frames=200):
    """Load a WAV file and compute MFCC frames."""
    if not LIBROSA_OK:
        return None
    try:
        y, _ = librosa.load(wav_path, sr=sr, mono=True)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc).T  # (T, 40)
        mfcc = (mfcc - mfcc.mean(0)) / (mfcc.std(0) + 1e-9)
        if len(mfcc) > max_frames:
            mfcc = mfcc[:max_frames]
        return mfcc.astype(np.float32)
    except Exception as e:
        print(f"  [WRN] Could not load {wav_path.name}: {e}")
        return None


def _synthetic_mfcc(n_frames=30, n_mfcc=MFCC_DIM, speaker_mu=None):
    """Generate a synthetic MFCC sequence for one utterance of one speaker."""
    if speaker_mu is None:
        speaker_mu = np.random.randn(n_mfcc).astype(np.float32) * 2
    noise = np.random.randn(n_frames, n_mfcc).astype(np.float32) * 0.3
    return speaker_mu + noise


def build_dataset(n_speakers=10, utterances_per_speaker=15):
    """
    Build a (utterances, labels) dataset.
    Priority: real WAV files in datasets/speaker_samples/<speaker_id>/*.wav
    Fallback: synthetic Gaussian MFCC sequences.
    """
    utterances, labels = [], []

    # Discover real audio
    real_speakers = sorted([d for d in SAMPLES_DIR.iterdir() if d.is_dir()])
    if real_speakers and LIBROSA_OK:
        print(f"   Found {len(real_speakers)} real speaker directories.")
        for spk_id, spk_dir in enumerate(real_speakers):
            wavs = list(spk_dir.glob("*.wav"))
            for wav in wavs:
                mfcc = _load_wav_mfcc(wav)
                if mfcc is not None:
                    utterances.append(mfcc)
                    labels.append(spk_id)
        if utterances:
            print(f"   Loaded {len(utterances)} real utterances.")

    # Top-up or fully synthetic
    existing_spk = len(set(labels)) if labels else 0
    synthetic_spk = max(0, n_speakers - existing_spk)
    print(f"   Generating synthetic data: {synthetic_spk} virtual speakers x {utterances_per_speaker} utterances")
    mus = [np.random.randn(MFCC_DIM).astype(np.float32) * 2 for _ in range(synthetic_spk)]
    for offset, mu in enumerate(mus):
        for _ in range(utterances_per_speaker):
            frames = random.randint(20, MAX_FRAMES)
            utterances.append(_synthetic_mfcc(n_frames=frames, speaker_mu=mu))
            labels.append(existing_spk + offset)

    return utterances, labels


def _pad_batch(utterances, labels):
    """Pad variable-length MFCC sequences to max length and stack."""
    max_len = max(u.shape[0] for u in utterances)
    padded  = np.zeros((len(utterances), max_len, MFCC_DIM), dtype=np.float32)
    for i, u in enumerate(utterances):
        padded[i, :u.shape[0]] = u
    return padded, np.array(labels, dtype=np.int64)


# --- Triplet Loss -------------------------------------------------------------
class TripletLoss(nn.Module):
    def __init__(self, margin=0.2):
        super().__init__()
        self.margin = margin

    def forward(self, anchor, positive, negative):
        d_ap = 1 - (anchor * positive).sum(dim=-1)  # cosine distance
        d_an = 1 - (anchor * negative).sum(dim=-1)
        loss = torch.clamp(d_ap - d_an + self.margin, min=0.0)
        return loss.mean()


def _sample_triplets(embeddings, labels, n_triplets=512):
    """Sample random valid triplets (anchor, positive, negative)."""
    label_arr = np.array(labels)
    unique    = np.unique(label_arr)
    anchors, positives, negatives = [], [], []
    for _ in range(n_triplets):
        spk  = random.choice(unique)
        pos_idx = np.where(label_arr == spk)[0]
        neg_idx = np.where(label_arr != spk)[0]
        if len(pos_idx) < 2 or len(neg_idx) == 0:
            continue
        a, p = random.sample(list(pos_idx), 2)
        n    = random.choice(neg_idx)
        anchors.append(embeddings[a])
        positives.append(embeddings[p])
        negatives.append(embeddings[n])
    if not anchors:
        return None, None, None
    return (torch.stack(anchors),
            torch.stack(positives),
            torch.stack(negatives))


def compute_eer(embeddings, labels):
    """Approximate Equal Error Rate using cosine similarity."""
    label_arr = np.array(labels)
    sims, targets = [], []
    n = len(embeddings)
    idx = random.sample(range(n), min(n, 200))
    for i in idx:
        for j in idx:
            if i == j:
                continue
            sim = float((embeddings[i] * embeddings[j]).sum())
            sims.append(sim)
            targets.append(int(label_arr[i] == label_arr[j]))
    sims    = np.array(sims)
    targets = np.array(targets)
    thresholds = np.linspace(-1, 1, 200)
    best_eer = 1.0
    for thr in thresholds:
        preds = (sims >= thr).astype(int)
        fa  = ((preds == 1) & (targets == 0)).sum() / max((targets == 0).sum(), 1)
        fr  = ((preds == 0) & (targets == 1)).sum() / max((targets == 1).sum(), 1)
        eer = (fa + fr) / 2
        if eer < best_eer:
            best_eer = eer
    return best_eer


# --- Training loop ------------------------------------------------------------
def train(n_epochs=20, lr=1e-3, n_speakers=10, utterances_per_speaker=15):
    if not TORCH_OK:
        return {"error": "PyTorch not installed"}

    print("=" * 60)
    print("  SPEAKER EMBEDDING MODEL TRAINING")
    print("=" * 60)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n   Device: {device}")

    # Build dataset
    print("\n[PKG] Building dataset...")
    utterances, labels = build_dataset(n_speakers, utterances_per_speaker)
    print(f"   Total utterances: {len(utterances)}  |  Speakers: {len(set(labels))}")

    # Pad + tensorise
    X_np, y_np = _pad_batch(utterances, labels)
    X = torch.from_numpy(X_np).to(device)

    # Model + optimiser
    model     = SpeakerEncoder().to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)
    criterion = TripletLoss(margin=0.3)

    best_eer   = 1.0
    best_state = None

    print(f"\n[TRN]  Training for {n_epochs} epochs...\n")

    label_list = y_np.tolist()
    label_arr  = np.array(label_list)
    unique_spks = np.unique(label_arr)

    for epoch in range(1, n_epochs + 1):
        model.train()
        optimizer.zero_grad()

        # Sample a small triplet batch per epoch
        pos_anchors, pos_positives, neg_indices = [], [], []
        for _ in range(16):  # small batch for CPU speed
            spk = random.choice(unique_spks)
            pos_idx = np.where(label_arr == spk)[0]
            neg_idx = np.where(label_arr != spk)[0]
            if len(pos_idx) < 2 or len(neg_idx) == 0:
                continue
            a_i, p_i = random.sample(list(pos_idx), 2)
            n_i      = random.choice(neg_idx)
            pos_anchors.append(a_i)
            pos_positives.append(p_i)
            neg_indices.append(n_i)

        if not pos_anchors:
            continue

        a_idx = torch.tensor(pos_anchors,   dtype=torch.long)
        p_idx = torch.tensor(pos_positives, dtype=torch.long)
        n_idx = torch.tensor(neg_indices,   dtype=torch.long)

        # Forward through model WITH gradients
        emb_a = model(X[a_idx])
        emb_p = model(X[p_idx])
        emb_n = model(X[n_idx])

        loss = criterion(emb_a, emb_p, emb_n)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        optimizer.step()
        scheduler.step()

        # Evaluate EER every 10 epochs
        if epoch % 10 == 0 or epoch == n_epochs:
            model.eval()
            with torch.no_grad():
                # Evaluate on a small random subset for speed
                eval_idx = random.sample(range(len(X)), min(len(X), 60))
                eval_X   = X[torch.tensor(eval_idx)]
                embs_eval = model(eval_X).cpu().numpy()
            sub_labels = [label_list[i] for i in eval_idx]
            eer = compute_eer(embs_eval, sub_labels)
            marker = " <- best" if eer < best_eer else ""
            print(f"  Epoch {epoch:3d}/{n_epochs} | Loss: {loss.item():.4f} | EER: {eer:.4f}{marker}")
            if eer < best_eer:
                best_eer   = eer
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

    # Save best model
    if best_state is None:
        best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

    save_dict = {
        "model_state_dict": best_state,
        "config": {
            "input_dim":  MFCC_DIM,
            "hidden_dim": HIDDEN_DIM,
            "embed_dim":  EMBED_DIM,
            "n_layers":   N_LAYERS,
        },
    }
    torch.save(save_dict, MODEL_PATH)
    print(f"\n[SAV] Best model saved -> {MODEL_PATH}")
    print(f"   Best EER: {best_eer:.4f}  ({best_eer*100:.1f}%)")

    # Log results
    results = {}
    if RESULTS_PATH.exists():
        with open(RESULTS_PATH) as f:
            results = json.load(f)

    results["speaker_model"] = {
        "trained_at":  datetime.now().isoformat(),
        "n_speakers":  len(set(labels)),
        "n_utterances": len(utterances),
        "best_eer":    float(best_eer),
        "n_epochs":    n_epochs,
        "architecture": {"input_dim": MFCC_DIM, "hidden_dim": HIDDEN_DIM,
                         "embed_dim": EMBED_DIM, "n_layers": N_LAYERS},
    }
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n[LOG] Results logged to: {RESULTS_PATH}")
    print("=" * 60)
    print(f"  DONE -- Best EER: {best_eer*100:.1f}%")
    print("=" * 60)
    return results["speaker_model"]


if __name__ == "__main__":
    train()
