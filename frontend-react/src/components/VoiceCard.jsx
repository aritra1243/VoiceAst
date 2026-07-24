import { useState, useCallback } from 'react';
import { useSpeech } from '../hooks/useSpeech';

export default function VoiceCard({ send, wsStatus, onListenChange }) {
  const [transcript, setTranscript] = useState('');
  const [response, setResponse]     = useState('');
  const [isSuccess, setIsSuccess]   = useState(true);
  const [active, setActive]         = useState(false);

  const handleFinal = useCallback((text) => {
    setTranscript(text);
    send({ type: 'voice_command', text });
  }, [send]);

  const { isListening, startListening, stopListening } = useSpeech({
    onTranscript: setTranscript,
    onFinal: handleFinal,
  });

  const activate = () => {
    setActive(true);
    startListening();
    if (onListenChange) onListenChange(true);
  };

  const deactivate = () => {
    setActive(false);
    stopListening();
    if (onListenChange) onListenChange(false);
  };

  return (
    <div className="glass-card rounded-lg p-5 flex flex-col gap-4 h-full">

      {/* Card header */}
      <div className="flex items-center justify-between pb-2 border-b border-[rgba(0,247,255,0.12)]">
        <div className="flex items-center gap-2">
          <span className="text-lg">🎤</span>
          <span className="font-orbitron text-xs tracking-[0.2em] text-glow-cyan">VOICE CONTROL</span>
        </div>
        <span className={`font-orbitron text-[9px] tracking-widest ${isListening ? 'text-glow-amber animate-pulse' : 'text-[rgba(0,247,255,0.4)]'}`}>
          {isListening ? '● REC' : '○ IDLE'}
        </span>
      </div>

      {/* Transcription box */}
      <div className="flex-1 min-h-[60px] rounded bg-[rgba(0,10,25,0.6)] border border-[rgba(0,247,255,0.1)] p-3">
        <div className="font-orbitron text-[8px] text-[rgba(0,247,255,0.4)] mb-1 tracking-widest">INPUT</div>
        <p className="font-rajdhani text-sm text-[#c8f0ff] leading-relaxed min-h-[28px]">
          {transcript || <span className="text-[rgba(0,247,255,0.25)]">Awaiting voice input…</span>}
        </p>
      </div>

      {/* Response box */}
      <div className={`rounded border p-3 transition-all duration-300 ${
        isSuccess
          ? 'bg-[rgba(0,255,136,0.05)] border-[rgba(0,255,136,0.15)]'
          : 'bg-[rgba(255,51,102,0.05)] border-[rgba(255,51,102,0.15)]'
      }`}>
        <div className="font-orbitron text-[8px] mb-1 tracking-widest text-[rgba(0,247,255,0.4)]">RESPONSE</div>
        <p className={`font-rajdhani text-sm leading-relaxed min-h-[28px] ${isSuccess ? 'text-glow-green' : 'text-glow-red'}`}>
          {response || <span className="text-[rgba(0,247,255,0.25)]">System ready…</span>}
        </p>
      </div>

      {/* Controls */}
      <div className="flex gap-3">
        <button
          id="voice-start-btn"
          onClick={activate}
          disabled={isListening}
          className="hud-btn flex-1 disabled:opacity-40"
        >
          ▶ Start
        </button>
        <button
          id="voice-stop-btn"
          onClick={deactivate}
          disabled={!isListening}
          className="hud-btn danger flex-1 disabled:opacity-40"
        >
          ■ Stop
        </button>
      </div>

      {/* Hint */}
      <p className="font-rajdhani text-[10px] text-[rgba(0,247,255,0.3)] tracking-wider text-center">
        {wsStatus === 'online' ? 'WebSocket connected — click Start to speak' : 'Backend offline — check server'}
      </p>
    </div>
  );
}
