/**
 * PRIME Voice Assistant - Frontend Application
 * Features: Wake word "Hey Prime", Start/Stop buttons, AI-powered responses
 */

class PrimeAssistant {
    constructor() {
        this.ws = null;
        this.isListening = false;
        this.isConnected = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.audioContext = null;
        this.analyser = null;
        this.silenceTimer = null;
        this.conversationActive = false;

        // DOM Elements
        this.ui = {
            voiceOrb: document.getElementById('voiceOrb'),
            startBtn: document.getElementById('startBtn'),
            stopBtn: document.getElementById('stopBtn'),
            visualizer: document.getElementById('visualizer'),
            statusDot: document.getElementById('statusDot'),
            statusText: document.getElementById('statusText'),
            transcription: document.getElementById('transcription'),
            responseText: document.getElementById('responseText'),
            historyList: document.getElementById('historyList'),
            statTotal: document.getElementById('statTotal'),
            statSuccess: document.getElementById('statSuccess')
        };

        this.init();
    }

    init() {
        this.connectWebSocket();
        this.setupEventListeners();
        this.loadHistory();
        this.loadStatistics();
    }

    setupEventListeners() {
        // Voice Orb click - activates conversation with greeting
        if (this.ui.voiceOrb) {
            this.ui.voiceOrb.addEventListener('click', () => this.activateConversation());
        }

        // Start button - activates conversation with greeting
        if (this.ui.startBtn) {
            this.ui.startBtn.addEventListener('click', () => this.activateConversation());
        }

        // Stop button
        if (this.ui.stopBtn) {
            this.ui.stopBtn.addEventListener('click', () => this.stopConversation());
        }
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('✓ Connected to Prime');
            this.isConnected = true;
            this.updateStatus('online', 'System Online');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.ws.onclose = () => {
            console.log('Disconnected from server');
            this.isConnected = false;
            this.updateStatus('offline', 'Disconnected');
            setTimeout(() => this.connectWebSocket(), 3000);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    handleMessage(data) {
        console.log('📩 Message:', data.type, data);

        switch (data.type) {
            case 'transcription':
                if (data.text) {
                    this.showTranscription(data.text);
                    // Check for wake word
                    if (this.checkWakeWord(data.text)) {
                        this.activateConversation();
                    }
                }
                break;

            case 'intent':
                console.log(`Intent: ${data.intent}`);
                break;

            case 'result':
                this.showResponse(data.message, data.success);
                this.addToHistory(data.message, data.success);

                // Play audio response, then continue conversation
                if (data.audio) {
                    this.playAudio(data.audio, () => {
                        // After audio finishes, start listening if conversation is active
                        if (this.conversationActive) {
                            setTimeout(() => this.startListening(), 500);
                        }
                    });
                } else if (this.conversationActive) {
                    // No audio, start listening after delay
                    setTimeout(() => this.startListening(), 1000);
                }

                this.loadStatistics();
                break;

            case 'error':
                this.showResponse(data.message, false);
                break;
        }
    }

    checkWakeWord(text) {
        const wakeWords = ['hey prime', 'hi prime', 'hello prime', 'hey pryme', 'हे प्राइम'];
        const lowerText = text.toLowerCase().trim();
        return wakeWords.some(word => lowerText.includes(word));
    }

    activateConversation() {
        console.log('🎯 Activating Prime with greeting...');
        this.conversationActive = true;

        // Send greeting request to backend (male voice greeting)
        this.sendToServer({
            type: 'greeting'
        });

        // Update UI
        this.showResponse('Activating Prime...', true);
        this.updateStatus('online', 'Prime Active');
    }

    async startListening() {
        if (this.isListening) return;

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });

            this.isListening = true;
            this.conversationActive = true;
            this.audioChunks = [];

            // Update UI
            if (this.ui.voiceOrb) this.ui.voiceOrb.classList.add('listening');
            if (this.ui.visualizer) this.ui.visualizer.classList.add('active');
            if (this.ui.statusDot) this.ui.statusDot.classList.add('listening');
            this.updateStatus('listening', 'Listening...');

            // Setup MediaRecorder
            this.mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = () => {
                this.processAudio();
            };

            this.mediaRecorder.start(100);

            // Setup audio analysis for VAD
            this.setupAudioAnalysis(stream);

            // Auto-stop after silence
            this.startSilenceDetection();

        } catch (error) {
            console.error('Microphone error:', error);
            this.showResponse('Microphone access denied', false);
        }
    }

    setupAudioAnalysis(stream) {
        this.audioContext = new AudioContext();
        this.analyser = this.audioContext.createAnalyser();
        const source = this.audioContext.createMediaStreamSource(stream);
        source.connect(this.analyser);
        this.analyser.fftSize = 256;
    }

    startSilenceDetection() {
        let silenceStart = null;
        const silenceThreshold = 0.01;
        const silenceDuration = 2000; // 2 seconds of silence

        const checkSilence = () => {
            if (!this.isListening || !this.analyser) return;

            const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
            this.analyser.getByteFrequencyData(dataArray);
            const average = dataArray.reduce((a, b) => a + b) / dataArray.length / 255;

            if (average < silenceThreshold) {
                if (!silenceStart) silenceStart = Date.now();
                else if (Date.now() - silenceStart > silenceDuration) {
                    this.stopListening();
                    return;
                }
            } else {
                silenceStart = null;
            }

            if (this.isListening) {
                requestAnimationFrame(checkSilence);
            }
        };

        checkSilence();
    }

    stopListening() {
        if (!this.isListening) return;

        this.isListening = false;

        // Stop MediaRecorder
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
            this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
        }

        // Close audio context
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }

        // Update UI
        if (this.ui.voiceOrb) this.ui.voiceOrb.classList.remove('listening');
        if (this.ui.visualizer) this.ui.visualizer.classList.remove('active');
        if (this.ui.statusDot) this.ui.statusDot.classList.remove('listening');
        this.updateStatus('online', 'Processing...');
    }

    stopConversation() {
        console.log('🛑 Stopping conversation');
        this.conversationActive = false;
        this.stopListening();

        // Stop any playing audio
        const audioElements = document.querySelectorAll('audio');
        audioElements.forEach(audio => {
            audio.pause();
            audio.remove();
        });

        this.updateStatus('online', 'System Online');
        this.showResponse('Conversation stopped. Say "Hey Prime" to start again.', true);
    }

    toggleListening() {
        if (this.isListening) {
            this.stopListening();
        } else {
            this.startListening();
        }
    }

    async processAudio() {
        if (this.audioChunks.length === 0) return;

        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });

        // Convert to WAV
        const arrayBuffer = await audioBlob.arrayBuffer();
        const audioContext = new AudioContext({ sampleRate: 16000 });
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        const wavBlob = this.audioBufferToWav(audioBuffer);

        // Convert to base64
        const reader = new FileReader();
        reader.onloadend = () => {
            const base64Audio = reader.result.split(',')[1];

            // Send to server
            this.sendToServer({
                type: 'voice_audio_file',
                audio: base64Audio
            });
        };
        reader.readAsDataURL(wavBlob);

        audioContext.close();
    }

    audioBufferToWav(buffer) {
        const numChannels = 1;
        const sampleRate = buffer.sampleRate;
        const format = 1; // PCM
        const bitDepth = 16;

        const bytesPerSample = bitDepth / 8;
        const blockAlign = numChannels * bytesPerSample;

        const data = buffer.getChannelData(0);
        const samples = new Int16Array(data.length);

        for (let i = 0; i < data.length; i++) {
            const s = Math.max(-1, Math.min(1, data[i]));
            samples[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }

        const wavBuffer = new ArrayBuffer(44 + samples.length * 2);
        const view = new DataView(wavBuffer);

        // WAV header
        const writeString = (offset, string) => {
            for (let i = 0; i < string.length; i++) {
                view.setUint8(offset + i, string.charCodeAt(i));
            }
        };

        writeString(0, 'RIFF');
        view.setUint32(4, 36 + samples.length * 2, true);
        writeString(8, 'WAVE');
        writeString(12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, format, true);
        view.setUint16(22, numChannels, true);
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * blockAlign, true);
        view.setUint16(32, blockAlign, true);
        view.setUint16(34, bitDepth, true);
        writeString(36, 'data');
        view.setUint32(40, samples.length * 2, true);

        const offset = 44;
        for (let i = 0; i < samples.length; i++) {
            view.setInt16(offset + i * 2, samples[i], true);
        }

        return new Blob([wavBuffer], { type: 'audio/wav' });
    }

    sendToServer(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        }
    }

    playAudio(base64Audio, onEnded) {
        if (!base64Audio) {
            if (onEnded) onEnded();
            return;
        }

        const audio = new Audio(`data:audio/wav;base64,${base64Audio}`);
        audio.onended = () => {
            audio.remove();
            if (onEnded) onEnded();
        };
        audio.onerror = () => {
            if (onEnded) onEnded();
        };
        audio.play().catch((err) => {
            console.error('Audio play error:', err);
            if (onEnded) onEnded();
        });
    }

    updateStatus(state, text) {
        if (this.ui.statusText) this.ui.statusText.textContent = text;
        if (this.ui.statusDot) {
            this.ui.statusDot.className = 'status-dot';
            if (state === 'offline') this.ui.statusDot.classList.add('offline');
            else if (state === 'listening') this.ui.statusDot.classList.add('listening');
        }
    }

    showTranscription(text) {
        if (this.ui.transcription) {
            this.ui.transcription.textContent = `"${text}"`;
        }
    }

    showResponse(text, success) {
        if (this.ui.responseText) {
            this.ui.responseText.textContent = text;
            this.ui.responseText.style.color = success ? '#00f7ff' : '#ff3366';
        }
        if (!this.isListening) {
            this.updateStatus('online', 'System Online');
        }
    }

    addToHistory(text, success) {
        if (!this.ui.historyList) return;

        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const item = document.createElement('div');
        item.className = 'history-item';
        item.style.borderLeftColor = success ? '#00ff88' : '#ff3366';
        item.innerHTML = `<span>${text.substring(0, 40)}${text.length > 40 ? '...' : ''}</span>`;

        this.ui.historyList.insertBefore(item, this.ui.historyList.firstChild);

        // Keep only last 10 items
        while (this.ui.historyList.children.length > 10) {
            this.ui.historyList.removeChild(this.ui.historyList.lastChild);
        }
    }

    loadHistory() {
        fetch('/api/history')
            .then(r => r.json())
            .then(data => {
                if (data.history && this.ui.historyList) {
                    this.ui.historyList.innerHTML = '';
                    data.history.slice(0, 10).forEach(item => {
                        this.addToHistory(item.response || item.command, item.success);
                    });
                }
            })
            .catch(() => { });
    }

    loadStatistics() {
        fetch('/api/statistics')
            .then(r => r.json())
            .then(data => {
                if (this.ui.statTotal) this.ui.statTotal.textContent = data.total_commands || '0';
                if (this.ui.statSuccess) {
                    const rate = data.success_rate ? `${Math.round(data.success_rate * 100)}%` : '0%';
                    this.ui.statSuccess.textContent = rate;
                }
            })
            .catch(() => { });
    }
}

// Initialize
let assistant;
document.addEventListener('DOMContentLoaded', () => {
    assistant = new PrimeAssistant();
});

// Quick action helper
function sendCommand(cmd) {
    if (assistant && assistant.ws && assistant.ws.readyState === WebSocket.OPEN) {
        assistant.sendToServer({
            type: 'voice_command',
            text: cmd,
            language: 'en'
        });
        assistant.showTranscription(cmd);
    } else {
        alert('System not connected');
    }
}
