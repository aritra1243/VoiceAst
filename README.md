# VoiceAst - Voice Assistant with Full Device Control

A comprehensive voice assistant application built entirely with Python, featuring offline speech recognition, text-to-speech, and full device control capabilities.

## Features

✨ **Offline Voice Recognition** - Uses Vosk for speech-to-text without API keys  
🔊 **Offline Text-to-Speech** - Uses pyttsx3 for voice responses  
🎯 **Custom Intent Recognition** - Pattern-based command understanding  
💻 **Full Device Control** - Control applications, files, and system  
🌐 **Modern Web Interface** - Real-time WebSocket communication  
📊 **Command History** - MongoDB-backed history tracking  

## Prerequisites

- Python 3.8 or higher
- MongoDB (optional, for command history)
- Windows OS (some features are Windows-specific)

## Installation

### 1. Clone or Navigate to Project Directory

```bash
cd e:\VoiceAst
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Download Vosk Model

Download the Vosk speech recognition model:

```bash
python setup.py
```

Or manually download from: https://alphacephei.com/vosk/models
- Download: `vosk-model-small-en-us-0.15.zip`
- Extract to: `e:\VoiceAst\models\vosk-model-small-en-us-0.15`

### 4. Setup Environment Variables

```bash
copy .env.example .env
```

Edit `.env` if needed for custom configuration.

### 5. Install MongoDB (Optional)

For command history tracking:
- Download MongoDB Community Edition
- Start MongoDB service
- Default connection: `mongodb://localhost:27017`

## Usage

### Start the Backend Server

```bash
cd backend
python main.py
```

Server will start at: `http://localhost:8000`

### Open the Frontend

Open `frontend/index.html` in a web browser (Chrome/Edge recommended)

Or visit: `http://localhost:8000` (backend serves frontend automatically)

### Using Voice Commands

1. Click the microphone button
2. Speak your command clearly
3. Wait for voice response
4. View command history in the panel

## Supported Commands

### Application Control
- "open notepad"
- "open calculator"
- "open chrome"
- "close notepad"

### File Operations
- "create file test.txt"
- "delete file test.txt"
- "list files in documents"
- "search for keyword in documents"

### System Control
- "increase volume"
- "decrease volume"
- "increase brightness"
- "decrease brightness"
- "take screenshot"

### Information
- "what time is it"
- "what's the date"
- "system information"

### Web
- "search for Python tutorials"

## Project Structure

```
VoiceAst/
├── backend/
│   ├── main.py                  # FastAPI server
│   ├── voice_recognition.py     # Speech-to-text
│   ├── text_to_speech.py        # Text-to-speech
│   ├── intent_recognizer.py     # Command understanding
│   ├── device_controller.py     # Device control
│   ├── database.py              # MongoDB integration
│   └── config.py                # Configuration
├── frontend/
│   ├── index.html               # UI
│   ├── style.css                # Styling
│   └── app.js                   # Frontend logic
├── models/                      # Vosk models
├── requirements.txt
├── setup.py
└── README.md
```

## Security Notes

⚠️ This application has extensive system access. Use only in trusted environments.

- Some commands require administrator privileges
- Dangerous commands (shutdown, delete) have confirmation prompts
- Configure `ENABLE_DANGEROUS_COMMANDS` in `.env`

## Troubleshooting

### Microphone Not Working
- Check browser permissions (Chrome: chrome://settings/content/microphone)
- Ensure microphone is connected and working

### Vosk Model Not Found
- Verify model path in `.env`
- Re-run `python setup.py`

### MongoDB Connection Error
- Ensure MongoDB is running
- Check connection string in `.env`
- App works without MongoDB (history won't be saved)

### Commands Not Executing
- Check if running with sufficient permissions
- Verify application paths for Windows

## Development

Built with:
- **Backend**: FastAPI, Vosk, pyttsx3, PyAutoGUI
- **Frontend**: HTML5, CSS3, JavaScript (WebSocket)
- **Database**: MongoDB (optional)

## License

MIT License - Feel free to modify and use for your projects!
