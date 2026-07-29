<div align="center">

# ⚡ VoiceAst (PRIME AI) ⚡

### Autonomous Dual-Database Voice Assistant & Device Controller with 3D WebGL Interface

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.140-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.0-61DAFB.svg)](https://react.dev/)
[![Three.js](https://img.shields.io/badge/Three.js-WebGL-black.svg)](https://threejs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Media_Store-336791.svg)](https://www.postgresql.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Memory_Store-47A248.svg)](https://www.mongodb.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-Custom_ML-EE4C2C.svg)](https://pytorch.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

*VoiceAst (PRIME)* is a state-of-the-art, fully autonomous voice assistant and device control platform. Built entirely with custom local AI models (no external API dependencies), a hybrid dual-database architecture, and a 3D WebGL holographic interface inspired by the Iron Man JARVIS blueprint.

</div>

---

## 🌟 Key Features

### 🤖 100% In-House Custom ML Pipeline (Zero External APIs / No Ollama)
- **Custom Intent Recognizer**: Multi-class Scikit-Learn TF-IDF classifier supporting 23+ intent actions.
- **Custom Speaker Verification**: PyTorch LSTM d-vector encoder (`speaker_id.py`) for voice profile matching.
- **Custom Vision Engine**: PyTorch EfficientNet-B0 scene captioner for visual Q&A and image understanding.
- **Offline Vosk Speech Recognition**: High-accuracy local speech-to-text with zero internet latency.

### 🗄️ Hybrid Dual-Database Strategy
- **PostgreSQL (`image_store.py`)**: Asynchronous `asyncpg` binary (`BYTEA`) store for webcam photos, screenshots, and visual memories with indexed label search.
- **MongoDB (`database.py`)**: Asynchronous `motor` document store for command history, text memories (RAG-lite), and user preferences.

### 👑 Owner Verification & Identity Recognition
- **Voice Profile Matching**: Recognizes the registered owner's voice embedding and addresses them as **"Sir"**.
- **Face Memory**: OpenCV LBPH face recognizer trains on user faces via camera ("*This is Aritra*") to grant personalized responses.
- **Guest Protection**: Non-owners receive standard polite responses without administrative privileges.

### 🤖 3D WebGL Iron Man JARVIS HUD
- **Real-Time Lip-Sync Animation**: Dynamic lower faceplate jaw rotation oscillating synchronously with active TTS audio speech.
- **Blueprint Line-Art Geometry**: Built using Three.js with glowing cyan eyes, collar wireframes, animated Arc Reactor chest core, and floating particles.
- **3D Cursor Tracking**: Holographic head smoothly tilts and rotates to follow mouse movement across the dashboard.
- **Adaptive Color States**: Seamlessly shifts from **Cyan** (`#00f7ff`) on standby/speaking to **Amber** (`#ffaa00`) while processing input.

### ⚡ Instant Command Execution ("Fast Path")
- Sub-100ms instant execution bypasses AI processing for volume, mute, brightness, screenshots, app launching, time/date, and photo memory commands.

### 💻 Full Device Control & Automation
- **Application Control**: Open/close desktop applications (Notepad, Chrome, VS Code, Calculator, Spotify, etc.).
- **System Automation**: Screen brightness, master volume, tab switching, file creation/deletion/search, and screenshots.
- **Universal Robotic Messaging**: Automated desktop messaging on WhatsApp and Phone Link.
- **Proactive System Monitor**: Background monitor issuing voice alerts for CPU (>90%), RAM (>95%), or Low Battery (<20%).

---

## 📐 System Architecture

```mermaid
flowchart TD
    subgraph Frontend ["React 19 Frontend (Port 5173)"]
        UI[HUD Dashboard]
        WebGL[3D Iron Man Head]
        STT[Browser STT / Vosk]
        Audio[Audio Player & Lip-Sync]
    end

    subgraph Backend ["FastAPI Backend (Port 8000)"]
        WS[WebSocket Endpoint /ws]
        FastPath[Fast-Path Engine]
        AIBrain[AI Brain Orchestrator]
        
        subgraph ML ["Custom ML Pipeline (PyTorch & Scikit-Learn)"]
            Intent[TF-IDF Intent Classifier]
            SpeakerID[LSTM Speaker Encoder]
            Vision[EfficientNet-B0 Captioner]
            FaceRec[OpenCV LBPH Face Recognizer]
        end
        
        DevCtrl[Device Controller / PyAutoGUI]
    end

    subgraph Storage ["Dual-Database Layer"]
        PG[(PostgreSQL - Media BYTEA)]
        Mongo[(MongoDB - Text & History)]
    end

    UI -->|WebSocket JSON| WS
    WS --> FastPath
    FastPath -->|Match| DevCtrl
    FastPath -->|No Match| AIBrain
    
    AIBrain --> ML
    SpeakerID -->|Voice Match?| AIBrain
    FaceRec -->|Face Match?| AIBrain
    
    AIBrain --> DevCtrl
    AIBrain -->|Save Photo/Screenshot| PG
    AIBrain -->|Save Command/Memory| Mongo
    
    WS -->|Audio Base64 & Intent| Audio
    Audio -->|isTalking Trigger| WebGL
```

---

## 🛠️ Installation & Setup Guide

### 1. Prerequisites
Ensure you have the following installed on your system:
- **Python**: `3.10` or higher
- **Node.js**: `18.0` or higher
- **PostgreSQL**: Running locally on port `5432`
- **MongoDB**: Running locally on port `27017`

---

### 2. Repository Setup

```bash
git clone https://github.com/aritra1243/VoiceAst.git
cd VoiceAst
```

---

### 3. Backend Environment Setup

#### Install Python Dependencies
```bash
pip install -r requirements.txt
```

#### Download Vosk Offline Speech Model
```bash
python setup.py
```
*(Extracts `vosk-model-small-en-us-0.15` into the `models/` directory)*

#### Configure Environment Variables
Copy `.env.example` to `.env` and set your credentials:
```bash
copy .env.example .env
```

Edit `.env`:
```ini
# PostgreSQL (Media Store)
POSTGRES_URL=postgresql://postgres:aritra@localhost:5432/voiceast_media

# MongoDB (Text Store)
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=voice_assistant

# Owner Identity Name
OWNER_FACE_NAME=Aritra
```

---

### 4. Frontend Setup

```bash
cd frontend-react
npm install
```

---

## 🚀 Running the Application

### Step 1: Start Backend Server (Terminal 1)
```bash
cd VoiceAst
python backend/main.py
```
*Backend runs at: `http://localhost:8000`*

### Step 2: Start React Frontend (Terminal 2)
```bash
cd VoiceAst/frontend-react
cmd /c npm run dev
```
*Frontend runs at: `http://localhost:5173`*

Open your browser to **`http://localhost:5173`** and allow Microphone & Camera permissions.

---

## 🗣️ Supported Voice Commands

| Category | Voice Command Example | Action Executed |
|---|---|---|
| **Identity & Enrollment** | *"Enroll my voice"* | Learns & saves speaker voice embedding to `owner_voice.npy` |
| | *"This is Aritra"* | Trains face recognizer model on current webcam frame |
| | *"Who is this?"* | Runs face recognition and identifies the person on camera |
| **Media Memory (PostgreSQL)** | *"Take a photo and remember this as my desk"* | Captures webcam frame, generates description, saves to PostgreSQL |
| | *"Save this screenshot as error screen"* | Captures screen PNG and stores in PostgreSQL database |
| | *"Show me the photo of my desk"* | Queries PostgreSQL by label and describes the saved image |
| **System Control** | *"Open Notepad"* / *"Close Chrome"* | Launches or terminates application |
| | *"Volume up"* / *"Volume down"* / *"Mute"* | Adjusts master system audio levels |
| | *"Brightness up"* / *"Brightness down"* | Controls display brightness |
| | *"Take screenshot"* | Saves screenshot image file to Desktop |
| | *"What time is it"* / *"What is the date"* | Spoken & visual time/date report |
| **Messaging** | *"Send message to John on WhatsApp saying Hello"* | Executes UI automation to send message |
| **Information** | *"What is the weather?"* | Server-side IP weather lookup with dashboard widget |

---

## 🔧 Troubleshooting

### 1. `ModuleNotFoundError: No module named 'fastapi'` or `pyautogui`
Run pip install directly:
```bash
python -m pip install -r requirements.txt
```

### 2. `ECONNREFUSED` in Vite Terminal
This means the React frontend is trying to proxy WebSockets to port 8000, but the Python backend is not running yet. Start the backend in Terminal 1 via `python backend/main.py`.

### 3. PowerShell Script Execution Policy (`npm.ps1 cannot be loaded`)
Bypass policy by running `cmd /c npm run dev` or run once in PowerShell:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).

---

<div align="center">
Built with ❤️ by <b>Aritra</b> · Powered by <b>Stark Industries Autonomous AI Engine</b>
</div>
