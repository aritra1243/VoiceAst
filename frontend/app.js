// VoiceAst Frontend - Final Robust Implementation
// Features: VAD (Auto-Stop), Quick Actions, Visualizer Safety, Continuous Mode

class VoiceAssistant {
    constructor() {
        this.ws = null;
        this.isListening = false;

        // Audio Logic
        this.audioContext = null;
        this.processor = null;
        this.input = null;
        this.audioChunks = [];
        this.sampleRate = 16000;

        // State
        this.silenceStart = null;
        this.isSpeaking = false;
        this.commandHistory = [];

        // UI Cache
        this.ui = {
            statusDot: document.getElementById('statusDot'),
            statusText: document.getElementById('statusText'),
            micButton: document.getElementById('micButton'),
            micIcon: document.getElementById('micIcon'),
            speakerIcon: document.getElementById('speakerIcon'),
            voiceVisualizer: document.getElementById('voiceVisualizer'),
            voiceStatusText: document.getElementById('voiceStatusText'),
            voiceSubtitle: document.getElementById('voiceSubtitle'),
            transcriptionBox: document.getElementById('transcriptionBox'),
            transcriptionText: document.getElementById('transcriptionText'),
            responseBox: document.getElementById('responseBox'),
            responseText: document.getElementById('responseText'),
            responseStatus: document.getElementById('responseStatus'),
            historyList: document.getElementById('historyList'),
            statTotal: document.getElementById('statTotal'),
            statSuccess: document.getElementById('statSuccess')
        };

        this.init();
    }

    init() {
        // Event Listeners
        if (this.ui.micButton) {
            this.ui.micButton.addEventListener('click', () => this.toggleListening());
        }

        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && !this.isListening && e.target === document.body) {
                e.preventDefault();
                this.startListening();
            }
        });

        document.addEventListener('keyup', (e) => {
            if (e.code === 'Space' && this.isListening) {
                e.preventDefault();
                this.stopListening();
            }
        });

        this.connectWebSocket();
        this.loadHistory();
        this.loadStatistics();
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname || 'localhost';
        const port = window.location.port || '8000';
        const url = `${protocol}//${host}:${port}/ws`;

        console.log('Connecting to:', url);
        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
            console.log('✓ Connected');
            this.updateStatus('connected', 'System Online');
        };

        this.ws.onmessage = (e) => this.handleMessage(JSON.parse(e.data));

        this.ws.onclose = () => {
            console.log('Disconnected');
            this.updateStatus('disconnected', 'Offline');
            setTimeout(() => this.connectWebSocket(), 3000);
        };

        this.ws.onerror = (e) => console.error('WS Error:', e);
    }

    updateStatus(className, text) {
        if (this.ui.statusDot) this.ui.statusDot.className = `status-dot ${className}`;
        if (this.ui.statusText) this.ui.statusText.textContent = text;
    }

    handleMessage(data) {
        console.log('RX:', data.type);

        switch (data.type) {
            case 'intent':
                if (this.ui.voiceStatusText) this.ui.voiceStatusText.textContent = `Intent: ${data.intent}`;
                if (this.ui.voiceSubtitle) this.ui.voiceSubtitle.textContent = `Confidence: ${(data.confidence * 100).toFixed(0)}%`;
                break;

            case 'result':
                this.showResponse(data.message, data.success);
                this.addToHistory(data.data?.command || "Voice Command", data.message, data.success);

                if (data.data?.command && this.ui.transcriptionText) {
                    this.ui.transcriptionBox.classList.add('show');
                    this.ui.transcriptionText.textContent = data.data.command;
                }

                // Audio Playback & Auto Restart
                if (data.audio) {
                    this.playAudio(data.audio, true);
                } else {
                    // No audio, restart immediately
                    setTimeout(() => this.startListening(), 1000);
                }
                this.loadStatistics();
                break;
        }
    }

    // --- Audio Capture ---

    async startListening() {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            alert('Not connected to server');
            return;
        }
        if (this.isListening) return;

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            // Re-create context if closed
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            this.audioContext = new AudioContext({ sampleRate: this.sampleRate });

            this.input = this.audioContext.createMediaStreamSource(stream);
            this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);

            this.audioChunks = [];
            this.silenceStart = null;

            // --- VAD & Capture Loop ---
            this.processor.onaudioprocess = (e) => {
                if (!this.isListening) return;

                const inputData = e.inputBuffer.getChannelData(0);
                this.audioChunks.push(new Float32Array(inputData));

                // RMS Calculation
                let sum = 0;
                for (let i = 0; i < inputData.length; i++) {
                    sum += inputData[i] * inputData[i];
                }
                const rms = Math.sqrt(sum / inputData.length);
                const THRESHOLD = 0.02;

                // Visuals & VAD (SAFE ACCESS)
                if (rms > THRESHOLD) {
                    this.silenceStart = null;
                    if (this.ui.voiceVisualizer) this.ui.voiceVisualizer.style.opacity = '1';

                    const scale = 1 + (rms * 5);
                    if (this.ui.micButton) this.ui.micButton.style.transform = `scale(${Math.min(scale, 1.2)})`;
                } else {
                    if (!this.silenceStart) this.silenceStart = Date.now();

                    // Auto-stop after 1.5s silence
                    if (Date.now() - this.silenceStart > 1500) {
                        if (this.audioChunks.length > 5) {
                            console.log('🛑 Auto-stop: Silence');
                            this.stopListening();
                        }
                    }

                    if (this.ui.voiceVisualizer) this.ui.voiceVisualizer.style.opacity = '0.5';
                    if (this.ui.micButton) this.ui.micButton.style.transform = 'scale(1)';
                }
            };

            this.input.connect(this.processor);
            this.processor.connect(this.audioContext.destination);

            this.isListening = true;
            this.updateUIState('listening');

        } catch (e) {
            console.error('Mic Error:', e);
            alert('Microphone access needed');
        }
    }

    stopListening() {
        if (!this.isListening) return;
        this.isListening = false;

        // Cleanup Audio
        if (this.processor) {
            this.processor.disconnect();
            this.input.disconnect();
            this.audioContext.close();
            // Stop tracks
            if (this.input && this.input.mediaStream) {
                this.input.mediaStream.getTracks().forEach(t => t.stop());
            }
        }

        this.updateUIState('processing');

        // Send
        if (this.audioChunks.length > 0) {
            console.log(`Sending ${this.audioChunks.length} chunks`);
            const wav = this.exportWAV(this.audioChunks);
            this.sendAudio(wav);
        }
    }

    updateUIState(state) {
        // Safe UI updates
        if (!this.ui.micButton) return;

        if (state === 'listening') {
            this.ui.micButton.classList.add('listening');
            if (this.ui.voiceStatusText) this.ui.voiceStatusText.textContent = '🎤 Listening...';
            if (this.ui.voiceSubtitle) this.ui.voiceSubtitle.textContent = 'Speak now...';
            if (this.ui.micIcon) this.ui.micIcon.style.display = 'block';
            if (this.ui.speakerIcon) this.ui.speakerIcon.style.display = 'none';
        } else if (state === 'processing') {
            this.ui.micButton.classList.remove('listening');
            if (this.ui.voiceStatusText) this.ui.voiceStatusText.textContent = 'Processing...';
        } else if (state === 'speaking') {
            this.ui.micButton.classList.add('speaking');
            if (this.ui.voiceStatusText) this.ui.voiceStatusText.textContent = 'Speaking...';
            if (this.ui.micIcon) this.ui.micIcon.style.display = 'none';
            if (this.ui.speakerIcon) this.ui.speakerIcon.style.display = 'block';
        } else if (state === 'ready') {
            this.ui.micButton.classList.remove('listening', 'speaking');
            if (this.ui.voiceStatusText) this.ui.voiceStatusText.textContent = 'Ready';
            if (this.ui.micIcon) this.ui.micIcon.style.display = 'block';
            if (this.ui.speakerIcon) this.ui.speakerIcon.style.display = 'none';
        }
    }

    toggleListening() {
        this.isListening ? this.stopListening() : this.startListening();
    }

    // --- Helpers ---

    exportWAV(chunks) {
        let len = 0;
        chunks.forEach(c => len += c.length);
        const buffer = new Float32Array(len);
        let offset = 0;
        chunks.forEach(c => { buffer.set(c, offset); offset += c.length; });

        const pcm = new Int16Array(len);
        for (let i = 0; i < len; i++) {
            let s = Math.max(-1, Math.min(1, buffer[i]));
            pcm[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }

        const header = new ArrayBuffer(44);
        const v = new DataView(header);
        const writeString = (v, o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };

        writeString(v, 0, 'RIFF');
        v.setUint32(4, 36 + len * 2, true);
        writeString(v, 8, 'WAVE');
        writeString(v, 12, 'fmt ');
        v.setUint32(16, 16, true);
        v.setUint16(20, 1, true);
        v.setUint16(22, 1, true);
        v.setUint32(24, this.sampleRate, true);
        v.setUint32(28, this.sampleRate * 2, true);
        v.setUint16(32, 2, true);
        v.setUint16(34, 16, true);
        writeString(v, 36, 'data');
        v.setUint32(40, len * 2, true);

        return new Blob([header, pcm], { type: 'audio/wav' });
    }

    sendAudio(blob) {
        const r = new FileReader();
        r.onloadend = () => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({
                    type: 'voice_audio_file',
                    audio: r.result.split(',')[1]
                }));
            }
        };
        r.readAsDataURL(blob);
    }

    playAudio(b64, autoRestart) {
        const audio = new Audio(`data:audio/wav;base64,${b64}`);
        audio.onplay = () => this.updateUIState('speaking');
        audio.onended = () => {
            this.updateUIState('ready');
            if (autoRestart) setTimeout(() => this.startListening(), 500);
        };
        audio.play().catch(e => console.error('Play error:', e));
    }

    showResponse(msg, success) {
        if (!this.ui.responseBox) return;
        this.ui.responseBox.classList.add('show');
        if (this.ui.responseStatus) {
            this.ui.responseStatus.textContent = success ? '✓ Success' : '✗ Failed';
            this.ui.responseStatus.className = `response-status ${success ? 'success' : 'error'}`;
        }
        if (this.ui.responseText) this.ui.responseText.textContent = msg;
    }

    addToHistory(cmd, res, success) {
        this.commandHistory.unshift({ cmd, res, success, time: new Date() });
        if (this.commandHistory.length > 50) this.commandHistory.pop();
        this.renderHistory();
    }

    renderHistory() {
        if (!this.ui.historyList) return;
        this.ui.historyList.innerHTML = this.commandHistory.map(i => `
            <div class="history-item ${i.success ? '' : 'error'}">
                <div class="history-command">${i.cmd}</div>
                <div class="history-response">${i.res}</div>
            </div>`).join('');
    }

    loadHistory() {
        fetch('/api/history')
            .then(r => r.json())
            .then(d => {
                if (d.history) this.commandHistory = d.history;
                this.renderHistory();
            })
            .catch(e => console.log('History load skipped:', e));
    }

    loadStatistics() {
        fetch('/api/statistics')
            .then(r => r.json())
            .then(d => {
                if (this.ui.statTotal) this.ui.statTotal.textContent = d.total_commands || '0';
                if (this.ui.statSuccess) this.ui.statSuccess.textContent = d.success_rate ? `${(d.success_rate * 100).toFixed(0)}%` : '0%';
            })
            .catch(e => console.log('Statistics load skipped:', e));
    }
}

let assistant;
document.addEventListener('DOMContentLoaded', () => assistant = new VoiceAssistant());

// Quick Action Helper
function sendCommand(cmd) {
    if (assistant && assistant.ws && assistant.ws.readyState === WebSocket.OPEN) {
        console.log('Sending command:', cmd);
        assistant.ws.send(JSON.stringify({
            type: 'voice_command',
            text: cmd,
            language: 'en'
        }));
    } else {
        alert('System not ready');
    }
}

// Clear History
function clearHistory() {
    if (assistant) {
        assistant.commandHistory = [];
        assistant.renderHistory();
    }
    fetch('/api/history', { method: 'DELETE' }).catch(() => { });
}

// Close Settings Modal
function closeSettings() {
    const modal = document.getElementById('settingsModal');
    if (modal) modal.style.display = 'none';
}

// Open Settings Modal
function openSettings() {
    const modal = document.getElementById('settingsModal');
    if (modal) modal.style.display = 'flex';
}
