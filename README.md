# VoiceAst - Voice Assistant with Full Device Control

A comprehensive voice assistant application built entirely with Python, featuring offline speech recognition, text-to-speech, and full device control capabilities.

## Features

✨ **Instant Response"** - "Fast Path" technology for <100ms execution of common commands  
🤖 **Advanced AI Brain** - Powered by **Qwen2** (0.5B) for fast, intelligent conversation  
👁️ **Vision Capabilities** - Show it things via webcam and ask questions (powered by LLaVA)  
� **Offline Capability** - Core features (Voice, AI, Control) work without internet  
�️ **Smart Dashboard** - Sci-Fi HUD with robust weather (Offline support + Geolocation)  
� **Local TTS & STT** - Privacy-focused, disconnected operation  
💻 **Full Device Control** - App management, media control, system stats, and more  

## Prerequisites

- Python 3.8+
- [Ollama](https://ollama.com/) (Required for AI features)
- MongoDB (Optional, for history)
- Windows OS

## Installation

### 1. Clone Project
```bash
cd e:\VoiceAst
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup AI Models
1. **Install Ollama** from [ollama.com](https://ollama.com)
2. **Pull the Qwen2 Model** (Fast & Efficient):
   ```bash
   ollama pull qwen2:0.5b
   ```
   *(Note: Config is set to use `qwen2` base name)*
3. **(Optional) Pull Vision Model**:
   ```bash
   ollama pull llava
   ```

### 4. Setup Vosk (Offline Speech)
Run the setup script to download the offline voice model:
```bash
python setup.py
```
*Or manually extract `vosk-model-small-en-us-0.15` to `models/`*

### 5. Configure Environment
```bash
copy .env.example .env
```
Default `.env` is already optimized for **Qwen2**.

## Usage

### 1. Start Backend
```bash
cd backend
python main.py
```
Server runs at `http://localhost:8000`.

### 2. Open Frontend
Open your browser to **http://localhost:8000**
*Allow Microphone and Location permissions for best experience.*

## Supported Functions

### 🧠 Long-term Memory
- **Text**: "Remember that my meet is at 5 PM" / "When is my meet?"
- **Visual (Face Rec)**: 
    - Teach: "This is John" (Show face to camera)
    - Ask: "Who is this?" (Show face again)

### 🛡️ Proactive System Monitor
- **Voice Alerts**: Warnings for High CPU (>90%), RAM (>95%), or Low Battery (<20%).
- **Checks**: Runs silently every 60 seconds.

### 📨 Universal Messaging
- "Send message to **John** on **WhatsApp** saying **Hello**"
- "Send text to **Mom** on **Phone Link** saying **I'm late**"
*(Note: Requires the app to be installed and logged in)*

### ⚡ Instant Commands (Fast Path)
- "Volume up/down/mute"
- "Take screenshot"
- "Open [app name]" (e.g., notepad, calculator, chrome)
- "What time/date is it"

### 🛠 System Control
- File management (create, delete, list)
- Brightness control
- Web search
- **Weather**: Shows automatically on the dashboard (Offline/Online auto-switch)

## Troubleshooting

### 🌦️ Weather Issues?
- The backend now fetches weather automatically via IP.
- If you see "Offline Mode", check your internet connection. We use `ipapi.co` and `wttr.in`.

### 🐢 Slow AI?
- Ensure you have the `qwen2` model pulled.
- GPU acceleration in Ollama helps significantly.
- "Fast Path" commands should always be instant.

## License
MIT License
