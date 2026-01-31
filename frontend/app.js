/**
 * PRIME Voice Assistant - Frontend Application
 * Using Web Speech API for fast, instant speech recognition
 */

class PrimeAssistant {
    constructor() {
        this.ws = null;
        this.isListening = false;
        this.isConnected = false;
        this.recognition = null;
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
        this.setupSpeechRecognition();
        this.connectWebSocket();
        this.setupEventListeners();
        this.loadHistory();
        this.loadStatistics();
        this.startClock();
        this.fetchWeather();
    }

    // Realtime Clock
    startClock() {
        const updateClock = () => {
            const now = new Date();

            // Time
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            const timeEl = document.getElementById('timeDisplay');
            if (timeEl) timeEl.textContent = `${hours}:${minutes}:${seconds}`;

            // Date
            const options = { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' };
            const dateStr = now.toLocaleDateString('en-US', options);
            const dateEl = document.getElementById('dateDisplay');
            if (dateEl) dateEl.textContent = dateStr;
        };

        updateClock();
        setInterval(updateClock, 1000);
    }

    // Weather (using wttr.in free API)
    async fetchWeather() {
        try {
            // Get user's location via IP
            const geoRes = await fetch('https://ipapi.co/json/');
            const geoData = await geoRes.json();
            const city = geoData.city || 'Delhi';

            // Fetch weather
            const weatherRes = await fetch(`https://wttr.in/${city}?format=j1`);
            const weatherData = await weatherRes.json();

            const current = weatherData.current_condition[0];
            const temp = current.temp_C;
            const desc = current.weatherDesc[0].value;

            // Weather icon based on condition
            const icon = this.getWeatherIcon(desc);

            const iconEl = document.querySelector('.weather-icon');
            const tempEl = document.getElementById('weatherTemp');
            const cityEl = document.getElementById('weatherCity');

            if (iconEl) iconEl.textContent = icon;
            if (tempEl) tempEl.textContent = `${temp}°C`;
            if (cityEl) cityEl.textContent = city;

            // Update every 10 minutes
            setTimeout(() => this.fetchWeather(), 10 * 60 * 1000);

        } catch (error) {
            console.error('Weather fetch error:', error);
            const cityEl = document.getElementById('weatherCity');
            if (cityEl) cityEl.textContent = 'Unavailable';
        }
    }

    getWeatherIcon(desc) {
        desc = desc.toLowerCase();
        if (desc.includes('sunny') || desc.includes('clear')) return '☀️';
        if (desc.includes('cloud')) return '☁️';
        if (desc.includes('rain')) return '🌧️';
        if (desc.includes('thunder') || desc.includes('storm')) return '⛈️';
        if (desc.includes('snow')) return '❄️';
        if (desc.includes('fog') || desc.includes('mist')) return '🌫️';
        if (desc.includes('overcast')) return '🌥️';
        return '🌡️';
    }

    setupSpeechRecognition() {
        // Use browser's Web Speech API for FAST recognition
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.error('Speech Recognition not supported');
            this.showResponse('Speech Recognition not supported in this browser', false);
            return;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.recognition.onstart = () => {
            console.log('🎤 Listening...');
            this.isListening = true;
            if (this.ui.voiceOrb) this.ui.voiceOrb.classList.add('listening');
            if (this.ui.visualizer) this.ui.visualizer.classList.add('active');
            if (this.ui.statusDot) this.ui.statusDot.classList.add('listening');
            this.updateStatus('listening', 'Listening...');
        };

        this.recognition.onresult = (event) => {
            let finalTranscript = '';
            let interimTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }

            // Show live transcription
            this.showTranscription(finalTranscript || interimTranscript);

            // Send final result to backend
            if (finalTranscript) {
                console.log('📝 Recognized:', finalTranscript);
                this.sendCommand(finalTranscript.trim());
            }
        };

        this.recognition.onend = () => {
            console.log('🔇 Stopped listening');
            this.isListening = false;
            if (this.ui.voiceOrb) this.ui.voiceOrb.classList.remove('listening');
            if (this.ui.visualizer) this.ui.visualizer.classList.remove('active');
            if (this.ui.statusDot) this.ui.statusDot.classList.remove('listening');

            if (this.conversationActive) {
                this.updateStatus('online', 'Processing...');
            } else {
                this.updateStatus('online', 'System Online');
            }
        };

        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.isListening = false;

            if (event.error === 'no-speech') {
                this.showResponse('No speech detected. Click Start to try again.', false);
                this.conversationActive = false;
            } else if (event.error === 'not-allowed') {
                this.showResponse('Microphone access denied. Please allow microphone.', false);
            }

            this.updateStatus('online', 'Click Start to try again');
        };
    }

    setupEventListeners() {
        // Voice Orb click
        if (this.ui.voiceOrb) {
            this.ui.voiceOrb.addEventListener('click', () => this.activateConversation());
        }

        // Start button
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
            this.conversationActive = false;
            this.updateStatus('offline', 'Reconnecting...');
            setTimeout(() => this.connectWebSocket(), 2000);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.isConnected = false;
        };
    }

    handleMessage(data) {
        console.log('📩 Message:', data.type);

        switch (data.type) {
            case 'connected':
                console.log('Connected to Prime backend');
                break;

            case 'processing':
                this.updateStatus('online', 'Processing...');
                break;

            case 'intent':
                console.log(`Intent: ${data.intent}`);
                break;

            case 'result':
                this.showResponse(data.message, data.success);
                this.addToHistory(data.message, data.success);

                // Play audio response
                if (data.audio) {
                    this.playAudio(data.audio, () => {
                        // After audio, start listening again if successful
                        if (data.success && this.conversationActive) {
                            setTimeout(() => this.startListening(), 300);
                        }
                    });
                } else if (data.success && this.conversationActive) {
                    setTimeout(() => this.startListening(), 500);
                }

                if (!data.success) {
                    this.conversationActive = false;
                    this.updateStatus('online', 'Click Start to try again');
                }

                this.loadStatistics();
                break;

            case 'error':
                this.showResponse(data.message, false);
                this.conversationActive = false;
                break;
        }
    }

    activateConversation() {
        if (!this.isConnected) {
            this.showResponse('Not connected to server', false);
            return;
        }

        console.log('🎯 Activating Prime...');
        this.conversationActive = true;

        // Request greeting from server
        this.sendToServer({ type: 'greeting' });
        this.showResponse('Activating Prime...', true);
        this.updateStatus('online', 'Prime Active');
    }

    startListening() {
        if (this.isListening || !this.recognition) return;

        try {
            this.recognition.start();
        } catch (e) {
            console.error('Failed to start recognition:', e);
        }
    }

    stopListening() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
        }
        this.isListening = false;
    }

    stopConversation() {
        console.log('🛑 Stopping conversation');
        this.conversationActive = false;
        this.stopListening();

        // Stop any playing audio
        document.querySelectorAll('audio').forEach(audio => {
            audio.pause();
            audio.remove();
        });

        this.updateStatus('online', 'System Online');
        this.showResponse('Say "Hey Prime" or click Start', true);
    }

    sendCommand(text) {
        if (!text.trim()) return;

        // Detect language (Hindi or English)
        const isHindi = /[\u0900-\u097F]/.test(text);

        this.sendToServer({
            type: 'voice_command',
            text: text,
            language: isHindi ? 'hi' : 'en'
        });

        this.updateStatus('online', 'Processing...');
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
    }

    addToHistory(text, success) {
        if (!this.ui.historyList) return;

        const item = document.createElement('div');
        item.className = 'history-item';
        item.style.borderLeftColor = success ? '#00ff88' : '#ff3366';
        item.innerHTML = `<span>${text.substring(0, 40)}${text.length > 40 ? '...' : ''}</span>`;

        this.ui.historyList.insertBefore(item, this.ui.historyList.firstChild);

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
        assistant.sendCommand(cmd);
        assistant.showTranscription(cmd);
    } else {
        alert('System not connected');
    }
}
