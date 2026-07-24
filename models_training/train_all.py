"""
Master Training Runner -- VoiceAst Custom Local Models
Trains all 3 custom models in order:
  1. NLP Intent Classifier  (TF-IDF + MLP)
  2. Speaker Embedding Model (LSTM d-vector)
  3. Vision Caption Model    (EfficientNet-B0 + LSTM)

Usage:
    python models_training/train_all.py

Results are saved to models_training/training_logs/training_results.json
"""
import json
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

LOGS_DIR  = Path(__file__).parent / "training_logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_PATH = LOGS_DIR / "training_results.json"

# --- Banner ------------------------------------------------------------------
BANNER = """
+==========================================================+
|        VoiceAst -- Custom Local Model Training            |
|  Replaces: Ollama qwen2 + Ollama llava + Resemblyzer     |
+==========================================================?
"""


def _section(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def _run_module(name: str, train_fn, **kwargs) -> dict:
    """Run a training function, catch errors, return result dict."""
    _section(f"Training: {name}")
    t0 = time.time()
    try:
        result = train_fn(**kwargs)
        elapsed = time.time() - t0
        if isinstance(result, dict) and "error" in result:
            print(f"\n[WRN] {name} finished with error: {result['error']}")
            result["elapsed_sec"] = round(elapsed, 1)
            return result
        print(f"\n?  Time: {elapsed:.1f}s")
        if isinstance(result, dict):
            result["elapsed_sec"] = round(elapsed, 1)
        return result or {}
    except Exception as e:
        elapsed = time.time() - t0
        print(f"\n[ERR] {name} FAILED: {e}")
        traceback.print_exc()
        return {"error": str(e), "elapsed_sec": round(elapsed, 1)}


def main():
    print(BANNER)
    print(f"  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    summary = {}

    # -- 1. NLP Intent Classifier ---------------------------------------------
    try:
        from models_training.train_intent_model import train as train_intent
    except ImportError:
        from train_intent_model import train as train_intent

    result_intent = _run_module("NLP Intent Classifier", train_intent)
    summary["intent_model"] = result_intent

    # -- 2. Speaker Embedding Model -------------------------------------------
    try:
        from models_training.train_speaker_model import train as train_speaker
    except ImportError:
        from train_speaker_model import train as train_speaker

    result_speaker = _run_module(
        "Speaker Embedding Model (LSTM d-vector)",
        train_speaker,
        n_epochs=30,
        n_speakers=20,
        utterances_per_speaker=30,
    )
    summary["speaker_model"] = result_speaker

    # -- 3. Vision Caption Model ----------------------------------------------
    print("\n" + "=" * 60)
    print("  Note: Vision training downloads COCO (~1.5 GB) on first run.")
    print("  This may take 20-60 min on CPU. Skip with Ctrl+C if desired.")
    print("=" * 60)
    try:
        response = input("\n  Start vision training? [Y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        response = "y"

    if response in ("", "y", "yes"):
        try:
            from models_training.train_vision_model import train as train_vision
        except ImportError:
            from train_vision_model import train as train_vision

        result_vision = _run_module(
            "Vision Caption Model (EfficientNet-B0 + LSTM)",
            train_vision,
            n_epochs=10,
            max_images=8000,
        )
        summary["vision_model"] = result_vision
    else:
        print("  [SKP]  Vision training skipped.")
        summary["vision_model"] = {"skipped": True}

    # -- Summary table ---------------------------------------------------------
    _section("TRAINING SUMMARY")

    intent_acc  = summary.get("intent_model",  {}).get("test_accuracy")
    speaker_eer = summary.get("speaker_model", {}).get("best_eer")
    vision_bleu = summary.get("vision_model",  {}).get("best_bleu4")

    rows = [
        ("NLP Intent Classifier",  "test_accuracy",
         f"{intent_acc*100:.1f}%"  if isinstance(intent_acc,  float) else "N/A"),
        ("Speaker Encoder (EER?)", "best_eer",
         f"{speaker_eer*100:.1f}%" if isinstance(speaker_eer, float) else "N/A"),
        ("Vision Caption (BLEU-4)","best_bleu4",
         f"{vision_bleu:.4f}"     if isinstance(vision_bleu, float) else
         ("skipped" if summary.get("vision_model", {}).get("skipped") else "N/A")),
    ]

    col_w = 32
    print(f"\n  {'Model':<{col_w}} {'Metric':<20}")
    print("  " + "-" * 52)
    for model_name, _, metric_val in rows:
        print(f"  {model_name:<{col_w}} {metric_val:<20}")

    # Check saved models
    saved_dir = Path(__file__).parent / "saved_models"
    print(f"\n  Saved models in {saved_dir}:")
    for p in sorted(saved_dir.glob("*")):
        size_kb = p.stat().st_size // 1024
        print(f"    ? {p.name:<35} ({size_kb:,} KB)")

    # Persist summary
    with open(RESULTS_PATH, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Full results -> {RESULTS_PATH}")

    print("\n" + "=" * 60)
    print("  ALL TRAINING COMPLETE")
    print("  VoiceAst now runs 100% locally -- no Ollama required.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
