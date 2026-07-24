"""
Train NLP Intent Classifier -- replaces Ollama qwen2
Architecture: TF-IDF + scikit-learn MLP classifier
Generates 5000+ synthetic training examples from existing patterns.
Saves best model (by validation accuracy) to saved_models/.
"""
import json
import random
import re
import sys
import os
from pathlib import Path
from datetime import datetime

# Allow importing from project root
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import LabelEncoder
    from sklearn.model_selection import cross_val_score, train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.metrics import classification_report, accuracy_score
    import joblib
    SKLEARN_OK = True
except ImportError:
    print("[ERR] scikit-learn not installed. Run: pip install scikit-learn")
    SKLEARN_OK = False

# --- Paths --------------------------------------------------------------------
SCRIPT_DIR   = Path(__file__).parent
DATASETS_DIR = SCRIPT_DIR / "datasets"
SAVED_DIR    = SCRIPT_DIR / "saved_models"
LOGS_DIR     = SCRIPT_DIR / "training_logs"

for d in (DATASETS_DIR, SAVED_DIR, LOGS_DIR):
    d.mkdir(parents=True, exist_ok=True)

INTENT_DATA_PATH      = DATASETS_DIR / "intent_data.json"
INTENT_MODEL_PATH     = SAVED_DIR / "intent_model.pkl"
INTENT_VECTORIZER_PATH = SAVED_DIR / "intent_vectorizer.pkl"
INTENT_ENCODER_PATH   = SAVED_DIR / "intent_label_encoder.pkl"
RESULTS_PATH          = LOGS_DIR / "training_results.json"


# --- Synthetic Data Generator -------------------------------------------------
APPS      = ["notepad", "chrome", "calculator", "explorer", "paint", "cmd",
             "powershell", "edge", "firefox", "wordpad", "vlc", "spotify",
             "discord", "steam", "word", "excel", "photoshop", "vscode"]
QUERIES   = ["weather today", "latest news", "python tutorial", "stock prices",
             "covid update", "recipe for pasta", "translate hello to french",
             "machine learning basics", "how to fix wifi", "math formula"]
FILES     = ["report.txt", "notes.md", "image.png", "data.csv", "script.py"]
DIRS      = ["documents", "desktop", "downloads", "pictures", "music"]
KEYS      = ["enter", "escape", "space", "tab", "backspace", "ctrl+c", "ctrl+v"]
TEXTS     = ["Hello world", "This is a test", "Meeting at 3pm", "To do list"]

TEMPLATES = {
    "open_app": [
        "open {app}", "launch {app}", "start {app}", "open up {app}",
        "can you open {app}", "please open {app}", "i want to open {app}",
        "run {app}", "execute {app}", "bring up {app}", "load {app}",
        "open the {app} application", "start {app} for me", "fire up {app}",
        "open {app} please", "hey open {app}", "launch the {app} app",
    ],
    "close_app": [
        "close {app}", "quit {app}", "exit {app}", "terminate {app}",
        "shut down {app}", "close the {app} window", "kill {app}",
        "stop {app}", "end {app}", "close {app} please", "please close {app}",
    ],
    "volume_up": [
        "volume up", "increase volume", "turn up the volume", "raise the volume",
        "louder please", "make it louder", "turn volume up", "raise volume",
        "increase the volume", "can you turn it up", "louder",
        "volume higher", "more volume", "boost the volume",
    ],
    "volume_down": [
        "volume down", "decrease volume", "turn down the volume", "lower the volume",
        "quieter please", "make it quieter", "turn volume down", "lower volume",
        "decrease the volume", "can you turn it down", "quieter",
        "volume lower", "less volume", "reduce the volume",
    ],
    "mute": [
        "mute", "silence", "mute the volume", "mute audio", "shut up",
        "turn off sound", "no sound", "go silent", "mute please",
        "be quiet", "silence the audio", "toggle mute",
    ],
    "brightness_up": [
        "brightness up", "increase brightness", "raise brightness",
        "make it brighter", "brighter please", "more brightness",
        "turn up the brightness", "higher brightness", "brighten the screen",
    ],
    "brightness_down": [
        "brightness down", "decrease brightness", "lower brightness",
        "make it darker", "darker please", "less brightness",
        "turn down the brightness", "lower the brightness", "dim the screen",
    ],
    "switch_tab": [
        "switch tab", "next tab", "previous tab", "change tab",
        "go to next tab", "go to previous tab", "tab next", "tab back",
        "go back to last tab", "switch to next tab",
    ],
    "screenshot": [
        "take a screenshot", "screenshot", "capture the screen",
        "take screenshot", "print screen", "capture screen",
        "snap the screen", "take a snap", "screen capture",
    ],
    "shutdown": [
        "shutdown the computer", "power off", "shut down the system",
        "turn off the computer", "shutdown pc", "power off the system",
        "shutdown", "turn off pc",
    ],
    "restart": [
        "restart the computer", "reboot", "restart the system",
        "restart pc", "reboot the system", "restart", "reboot computer",
    ],
    "time": [
        "what time is it", "tell me the time", "current time",
        "what's the time", "what is the time", "time please",
        "show the time", "check time",
    ],
    "date": [
        "what's the date", "what is the date", "today's date",
        "tell me the date", "current date", "what day is it",
        "date today", "show me the date",
    ],
    "system_info": [
        "system information", "computer info", "show system info",
        "system stats", "what are my system specs", "check system info",
        "hardware info", "cpu info", "show specs",
    ],
    "web_search": [
        "search for {query}", "google {query}", "look up {query}",
        "search {query}", "find {query} online", "search the web for {query}",
        "search online for {query}", "look {query} up", "search web {query}",
    ],
    "create_file": [
        "create a file named {file}", "make a file {file}",
        "new file {file}", "create file {file}", "make file {file}",
        "create the file {file}", "new file named {file}",
    ],
    "delete_file": [
        "delete the file {file}", "remove the file {file}",
        "delete file {file}", "remove file {file}", "erase {file}",
    ],
    "list_files": [
        "list files in {dir}", "show files in {dir}",
        "what files are in {dir}", "list {dir} files",
        "show me files in {dir}", "list directory {dir}",
    ],
    "type_text": [
        "type {text}", "write {text}", "type out {text}",
        "can you type {text}", "enter {text}", "input {text}",
    ],
    "press_key": [
        "press {key}", "hit {key}", "press the {key} key",
        "push {key}", "tap {key}",
    ],
    "greeting": [
        "hello", "hi", "hey", "greetings", "hey prime",
        "hi there", "hello prime", "good morning", "good afternoon",
        "what's up", "yo prime", "hello assistant",
    ],
    "help": [
        "help", "what can you do", "commands", "show commands",
        "list commands", "i need help", "help me", "what are your commands",
        "what do you know", "how can you help",
    ],
    "enroll_voice": [
        "learn my voice", "enroll my voice", "remember my voice",
        "this is my voice", "set my voice", "train my voice",
        "save my voice", "register my voice",
    ],
}

def _fill(template: str) -> str:
    """Fill template placeholders with random values."""
    template = template.replace("{app}", random.choice(APPS))
    template = template.replace("{query}", random.choice(QUERIES))
    template = template.replace("{file}", random.choice(FILES))
    template = template.replace("{dir}", random.choice(DIRS))
    template = template.replace("{key}", random.choice(KEYS))
    template = template.replace("{text}", random.choice(TEXTS))
    return template


def generate_dataset(n_per_intent: int = 220) -> list:
    """
    Generate synthetic (text, intent) pairs.
    Target: ~5000+ total examples across 23 intent classes.
    """
    samples = []
    for intent, templates in TEMPLATES.items():
        for _ in range(n_per_intent):
            tmpl = random.choice(templates)
            text = _fill(tmpl)
            # Light augmentation: random capitalisation, punctuation
            if random.random() < 0.3:
                text = text.capitalize()
            if random.random() < 0.2:
                text = text + random.choice([".", "!", "?"])
            samples.append({"text": text, "intent": intent})
    random.shuffle(samples)
    return samples


# --- Train --------------------------------------------------------------------
def train():
    if not SKLEARN_OK:
        return {"error": "scikit-learn not installed"}

    print("=" * 60)
    print("  NLP INTENT CLASSIFIER TRAINING")
    print("=" * 60)

    # 1. Generate data
    print("\n[PKG] Generating synthetic training data...")
    samples = generate_dataset(n_per_intent=220)
    print(f"   Total samples: {len(samples)}")

    # Save dataset
    with open(INTENT_DATA_PATH, "w") as f:
        json.dump(samples, f, indent=2)
    print(f"   Saved to: {INTENT_DATA_PATH}")

    texts   = [s["text"]   for s in samples]
    intents = [s["intent"] for s in samples]

    # 2. Encode labels
    le = LabelEncoder()
    y  = le.fit_transform(intents)
    print(f"\n[LBL]  Intent classes ({len(le.classes_)}): {list(le.classes_)}")

    # 3. Build pipeline
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 3),
            max_features=20000,
            sublinear_tf=True,
            analyzer="word",
            token_pattern=r"(?u)\b\w+\b",
        )),
        ("clf", MLPClassifier(
            hidden_layer_sizes=(256, 128),
            activation="relu",
            solver="adam",
            alpha=1e-4,
            batch_size=64,
            learning_rate="adaptive",
            max_iter=200,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=15,
            random_state=42,
            verbose=False,
        )),
    ])

    # 4. Cross-validate
    print("\n[CHK] Cross-validating (5-fold)...")
    cv_scores = cross_val_score(pipeline, texts, y, cv=5, scoring="accuracy", n_jobs=-1)
    print(f"   CV accuracy: {cv_scores.mean():.4f} ? {cv_scores.std():.4f}")

    # 5. Train on full data (keep 10% for final eval)
    print("\n[TRN]  Training final model...")
    X_train, X_test, y_train, y_test = train_test_split(
        texts, y, test_size=0.1, random_state=42, stratify=y
    )
    pipeline.fit(X_train, y_train)

    # 6. Evaluate
    y_pred = pipeline.predict(X_test)
    acc    = accuracy_score(y_test, y_pred)
    print(f"\n[OK] Final test accuracy: {acc:.4f}  ({acc*100:.1f}%)")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    # 7. Save
    print("\n[SAV] Saving models...")
    # Extract components separately so ai_brain.py can use them independently
    vectorizer = pipeline.named_steps["tfidf"]
    classifier = pipeline.named_steps["clf"]

    joblib.dump(vectorizer,  INTENT_VECTORIZER_PATH)
    joblib.dump(classifier,  INTENT_MODEL_PATH)
    joblib.dump(le,           INTENT_ENCODER_PATH)
    print(f"   ? Vectorizer -> {INTENT_VECTORIZER_PATH}")
    print(f"   ? Classifier -> {INTENT_MODEL_PATH}")
    print(f"   ? Label encoder -> {INTENT_ENCODER_PATH}")

    # 8. Update training results log
    results = {}
    if RESULTS_PATH.exists():
        with open(RESULTS_PATH) as f:
            results = json.load(f)

    results["intent_model"] = {
        "trained_at": datetime.now().isoformat(),
        "n_samples": len(samples),
        "n_classes": int(len(le.classes_)),
        "cv_accuracy_mean": float(cv_scores.mean()),
        "cv_accuracy_std": float(cv_scores.std()),
        "test_accuracy": float(acc),
        "classes": list(le.classes_),
    }
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n[LOG] Results logged to: {RESULTS_PATH}")
    print("=" * 60)
    print(f"  DONE -- Best accuracy: {acc*100:.1f}%")
    print("=" * 60)

    return results["intent_model"]


if __name__ == "__main__":
    train()
