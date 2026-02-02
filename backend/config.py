"""
Configuration management for VoiceAst
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent.parent

# MongoDB Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "voice_assistant")

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

# Vosk Model Path
VOSK_MODEL_PATH = BASE_DIR / os.getenv(
    "VOSK_MODEL_PATH", 
    "models/vosk-model-small-en-us-0.15"
)

# TTS Settings
TTS_RATE = int(os.getenv("TTS_RATE", 150))
TTS_VOLUME = float(os.getenv("TTS_VOLUME", 0.9))

# AI Settings (Ollama)
AI_ENABLED = os.getenv("AI_ENABLED", "true").lower() == "true"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Security Settings
ENABLE_DANGEROUS_COMMANDS = os.getenv("ENABLE_DANGEROUS_COMMANDS", "false").lower() == "true"

# Command Aliases
COMMAND_ALIASES = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "paint": "mspaint.exe",
    "wordpad": "wordpad.exe",
}

# Dangerous commands that require confirmation
DANGEROUS_COMMANDS = [
    "shutdown",
    "restart",
    "delete",
    "format",
    "remove",
]

# System paths
DOCUMENTS_PATH = Path.home() / "Documents"
DESKTOP_PATH = Path.home() / "Desktop"
DOWNLOADS_PATH = Path.home() / "Downloads"

PATH_ALIASES = {
    "documents": DOCUMENTS_PATH,
    "desktop": DESKTOP_PATH,
    "downloads": DOWNLOADS_PATH,
    "home": Path.home(),
}
