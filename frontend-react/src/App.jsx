import { useState, useCallback, useRef } from 'react';
import Header      from './components/Header';
import ScannerCore from './components/ScannerCore';
import VoiceCard   from './components/VoiceCard';
import SystemCard  from './components/SystemCard';
import HistoryCard from './components/HistoryCard';
import VisionCard  from './components/VisionCard';
import { useWebSocket } from './hooks/useWebSocket';

export default function App() {
  const [isListening,    setIsListening]    = useState(false);
  const [isTalking,      setIsTalking]      = useState(false);   // AI is speaking
  const [history,        setHistory]        = useState([]);
  const [totalCommands,  setTotalCommands]  = useState(0);
  const [successCount,   setSuccessCount]   = useState(0);

  // Audio player ref to detect when TTS audio finishes
  const audioRef = useRef(null);

  /* Play base64 audio and toggle isTalking while it plays */
  const playAudio = useCallback((audioBase64) => {
    if (!audioBase64) return;
    try {
      // Stop any currently playing audio
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      const audio = new Audio(`data:audio/wav;base64,${audioBase64}`);
      audioRef.current = audio;
      setIsTalking(true);
      audio.play().catch(() => {});
      audio.onended = () => setIsTalking(false);
      audio.onerror = () => setIsTalking(false);
    } catch {
      setIsTalking(false);
    }
  }, []);

  // Handle messages from WebSocket
  const handleMessage = useCallback((data) => {
    // Play TTS audio from any result/greeting that contains one
    if (data.audio) {
      playAudio(data.audio);
    }

    if (data.type === 'result') {
      const now = new Date();
      const timeStr = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
      setHistory(h => [
        ...h,
        { text: data.message, success: data.success, time: timeStr }
      ].slice(-50)); // keep last 50
      setTotalCommands(c => c + 1);
      if (data.success) setSuccessCount(c => c + 1);
    }
  }, [playAudio]);

  const { status: wsStatus, send } = useWebSocket(handleMessage);

  return (
    <div className="relative z-[1] min-h-screen flex flex-col px-4 py-4 max-w-[1600px] mx-auto">

      {/* ── Header ── */}
      <Header wsStatus={wsStatus} />

      {/* ── Main layout: 3-column grid ── */}
      <main className="flex-1 grid grid-cols-[1fr_340px_1fr] gap-4 items-start">

        {/* Left column — 2 stacked cards */}
        <div className="flex flex-col gap-4">
          <VoiceCard
            send={send}
            wsStatus={wsStatus}
            onListenChange={setIsListening}
          />
          <HistoryCard history={history} />
        </div>

        {/* Center column — 3D Robotic Head */}
        <div className="flex items-center justify-center sticky top-4">
          <ScannerCore
            isListening={isListening}
            isTalking={isTalking}
            wsStatus={wsStatus}
          />
        </div>

        {/* Right column — 2 stacked cards */}
        <div className="flex flex-col gap-4">
          <SystemCard
            totalCommands={totalCommands}
            successCount={successCount}
          />
          <VisionCard />
        </div>
      </main>

      {/* ── Footer ── */}
      <footer className="mt-6 text-center">
        <p className="font-orbitron text-[8px] tracking-[0.3em] text-[rgba(0,247,255,0.2)] uppercase">
          PRIME Autonomous Intelligence System · Ver 3.0.0 · © 2026 Stark Systems
        </p>
      </footer>
    </div>
  );
}
