"""
AI Brain - Custom NLP Intent Classifier
Replaces Ollama qwen2 with a locally-trained TF-IDF + MLP classifier.
No external services required -- fully offline inference.
"""
import json
import re
import sys
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path

# Allow running standalone
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import asyncio
import config

# --- Model loading ------------------------------------------------------------
try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False
    print("[WRN] joblib not installed. Run: pip install scikit-learn")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


def _load_models():
    """Load trained intent classifier, vectorizer, and label encoder."""
    if not JOBLIB_AVAILABLE:
        return None, None, None
    try:
        vectorizer = joblib.load(config.INTENT_VECTORIZER_PATH)
        classifier = joblib.load(config.INTENT_MODEL_PATH)
        label_enc  = joblib.load(config.INTENT_ENCODER_PATH)
        return vectorizer, classifier, label_enc
    except FileNotFoundError:
        return None, None, None
    except Exception as e:
        print(f"[WRN] Could not load intent models: {e}")
        return None, None, None


# --- Response templates -------------------------------------------------------
RESPONSE_TEMPLATES = {
    "open_app":        ("Opening {app_name}!", "open_app"),
    "close_app":       ("Closing {app_name}!", "close_app"),
    "volume_up":       ("Turning up the volume!", "volume_up"),
    "volume_down":     ("Lowering the volume!", "volume_down"),
    "mute":            ("Toggling mute!", "mute"),
    "brightness_up":   ("Increasing brightness!", "brightness_up"),
    "brightness_down": ("Decreasing brightness!", "brightness_down"),
    "switch_tab":      ("Switching tab!", "switch_tab"),
    "screenshot":      ("Taking a screenshot!", "take_screenshot"),
    "shutdown":        ("Shutting down the system!", "shutdown"),
    "restart":         ("Restarting the system!", "restart"),
    "time":            ("Checking the time!", "time"),
    "date":            ("Checking the date!", "date"),
    "system_info":     ("Fetching system info!", "system_info"),
    "web_search":      ("Searching for that!", "web_search"),
    "create_file":     ("Creating the file!", "create_file"),
    "delete_file":     ("Deleting the file!", "delete_file"),
    "list_files":      ("Listing files!", "list_files"),
    "type_text":       ("Typing that for you!", "type_text"),
    "press_key":       ("Pressing the key!", "press_key"),
    "greeting":        ("Hi there! How can I help?", None),
    "help":            ("Here's what I can do: open apps, control volume, search the web, and more!", None),
    "enroll_voice":    ("Starting voice enrollment. Please speak clearly.", "enroll_voice"),
    "search_files":    ("Searching for files!", "search_files"),
    "unknown":         ("I'm here to help! Try saying 'open notepad' or 'what time is it'.", None),
}

# Intent -> action name mapping (classifier intent -> backend action key)
INTENT_TO_ACTION = {t[0]: (t[1][1], t[1][0]) for t in RESPONSE_TEMPLATES.items()}


# --- Entity extractor --------------------------------------------------------
APPS_LIST = [
    "notepad", "chrome", "calculator", "explorer", "paint", "cmd",
    "powershell", "edge", "firefox", "wordpad", "vlc", "spotify",
    "discord", "steam", "word", "excel", "photoshop", "vscode",
]

def _extract_params(intent: str, text: str) -> Dict:
    """Extract entities from text based on predicted intent."""
    text_lower = text.lower()
    params = {}

    if intent in ("open_app", "close_app"):
        # Check known apps first
        for app in APPS_LIST:
            if app in text_lower:
                params["app_name"] = app
                break
        if "app_name" not in params:
            # Extract word after trigger verb
            m = re.search(r"(?:open|launch|start|close|quit|exit|kill|stop|run)\s+(?:the\s+|up\s+)?(\w+)", text_lower)
            if m:
                params["app_name"] = m.group(1)

    elif intent == "web_search":
        for kw in ("search for", "search", "google", "look up", "find"):
            if kw in text_lower:
                q = text_lower.split(kw, 1)[-1].strip()
                if q:
                    params["query"] = q
                    break

    elif intent == "switch_tab":
        if any(w in text_lower for w in ("previous", "back", "last")):
            params["direction"] = "previous"
        else:
            params["direction"] = "next"

    elif intent in ("create_file", "delete_file"):
        m = re.search(r"(?:file|named?)\s+(\S+)", text_lower)
        if m:
            params["filename"] = m.group(1)

    elif intent == "list_files":
        m = re.search(r"(?:in|inside|under)\s+(.+)$", text_lower)
        if m:
            params["directory"] = m.group(1).strip()

    elif intent == "type_text":
        m = re.search(r"(?:type|write|enter|input)\s+(.+)$", text, re.I)
        if m:
            params["text"] = m.group(1).strip()

    elif intent == "press_key":
        m = re.search(r"(?:press|hit|push|tap)\s+(?:the\s+)?(.+?)(?:\s+key)?$", text_lower)
        if m:
            params["key"] = m.group(1).strip()

    return params


# --- Main class ---------------------------------------------------------------
class AIBrain:
    """
    AI-powered brain for Prime voice assistant.
    Uses a locally-trained TF-IDF + MLP classifier (no Ollama required).
    """

    def __init__(self):
        self.vectorizer, self.classifier, self.label_enc = _load_models()

        if self.vectorizer is not None:
            print(f"? AI Brain loaded -- custom intent classifier active "
                  f"({len(self.label_enc.classes_)} intents)")
            self.is_available = True
        else:
            print("[WRN] AI Brain: no trained model found. Using pattern-match fallback.")
            print("  Run: python models_training/train_intent_model.py")
            self.is_available = False

    def _detect_language(self, text: str) -> str:
        """Detect if text is Hindi or English."""
        if re.search(r'[\u0900-\u097F]', text):
            return 'hi'
        return 'en'

    def _classify(self, text: str) -> tuple[str, float]:
        """Run the classifier and return (intent, confidence)."""
        X = self.vectorizer.transform([text])
        proba = self.classifier.predict_proba(X)[0]
        idx = int(proba.argmax())
        intent = self.label_enc.inverse_transform([idx])[0]
        confidence = float(proba[idx])
        return intent, confidence

    async def think(self, user_input: str, context_memories: list = None) -> Dict:
        """
        Process user input and generate response with optional action.

        Args:
            user_input: The user's voice command or question
            context_memories: Unused (kept for API compatibility)

        Returns:
            Dict with 'response', 'action', 'params', and 'language'
        """
        language = self._detect_language(user_input)

        if not self.is_available:
            return self._fallback_response(user_input)

        try:
            # Run CPU-bound classification off the event loop
            intent, confidence = await asyncio.to_thread(self._classify, user_input)

            if confidence < 0.35:
                intent = "unknown"

            print(f"[AI] Intent: {intent}  (conf={confidence:.2f})")

            # Look up response template and action
            action_name, response_text = INTENT_TO_ACTION.get(
                intent, (None, "I'm not sure how to help with that.")
            )

            # Extract entities
            params = _extract_params(intent, user_input)

            # Personalise response with entity values
            try:
                response_text = response_text.format(**params)
            except (KeyError, AttributeError):
                pass

            # Remap internal action names to backend keys expected by main.py
            ACTION_REMAP = {
                "take_screenshot": "take_screenshot",
                "open_app":  "open_app",
                "close_app": "close_app",
            }
            final_action = ACTION_REMAP.get(action_name, action_name)

            return {
                "response": response_text,
                "action":   final_action,
                "params":   params,
                "language": language,
            }

        except Exception as e:
            print(f"[ERR] AI Error: {e}")
            return self._fallback_response(user_input)

    def _fallback_response(self, user_input: str) -> Dict:
        """Fallback when classifier is not available -- use pattern matching."""
        text = user_input.lower().strip()
        language = self._detect_language(user_input)

        patterns = {
            ('open', 'launch', 'start'):                ('open_app',       "Opening that for you!"),
            ('close', 'quit', 'exit'):                  ('close_app',      "Closing that!"),
            ('screenshot', 'screen shot'):              ('take_screenshot', "Taking a screenshot!"),
            ('volume up', 'louder'):                    ('volume_up',      "Turning up the volume!"),
            ('volume down', 'quieter'):                 ('volume_down',    "Lowering the volume!"),
            ('mute', 'silence'):                        ('mute',           "Muting!"),
            ('switch tab', 'next tab', 'previous tab'): ('switch_tab',     "Switching tab!"),
            ('time', 'what time'):                      ('time',           "Checking the time."),
            ('date', "what's the date"):                ('date',           "Checking the date."),
            ('search', 'google'):                       ('web_search',     "Searching for that!"),
        }

        for keywords, (action, response) in patterns.items():
            if any(kw in text for kw in keywords):
                params = {}
                if action in ('open_app', 'close_app'):
                    for app in APPS_LIST:
                        if app in text:
                            params['app_name'] = app
                            break
                    else:
                        words = text.split()
                        for i, w in enumerate(words):
                            if w in ('open', 'launch', 'start', 'close'):
                                if i + 1 < len(words):
                                    params['app_name'] = words[i + 1]
                                break
                if action == 'switch_tab':
                    params['direction'] = 'previous' if any(
                        w in text for w in ['previous', 'back', 'last']
                    ) else 'next'
                if action == 'web_search':
                    for kw in ('search for', 'search', 'google'):
                        if kw in text:
                            q = text.split(kw, 1)[-1].strip()
                            if q:
                                params['query'] = q
                            break

                return {'response': response, 'action': action,
                        'params': params, 'language': language}

        return {
            'response': "I'm here to help! Try saying 'open notepad' or 'what time is it'.",
            'action':   None,
            'params':   {},
            'language': language,
        }


# Global AI brain instance
ai_brain = AIBrain()
