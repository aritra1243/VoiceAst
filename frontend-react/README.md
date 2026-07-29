# VoiceAst Frontend (React + Three.js + Tailwind CSS)

The frontend for **VoiceAst (PRIME AI)** — a sci-fi sci-fi dashboard featuring a 3D WebGL Iron Man JARVIS interface, real-time audio lip-syncing, live system metrics, and camera vision feed.

## 🚀 Features

- 🤖 **3D WebGL Iron Man Helmet (Three.js)**: Interactive 3D blueprint wireframe with real-time lip-sync jaw rotation when the AI speaks (`isTalking` state).
- 🎤 **Voice Control Panel**: Real-time speech input transcription, response playback, and listening state indicator.
- 👁️ **Vision Feed Module**: Live webcam preview with HUD scanner overlays for face recognition and image memory capture.
- 📊 **System Monitor Widget**: Live stats displaying CPU usage, RAM usage, command count, success rate, and uptime.
- 📜 **Command History Log**: History stack of recent voice commands and execution responses.

## 🛠️ Development Setup

### Install Dependencies
```bash
npm install
```

### Run Dev Server
```bash
cmd /c npm run dev
```

The dev server will run on `http://localhost:5173`.

### Production Build
```bash
cmd /c npm run build
```

The compiled output will be generated in `dist/`.
