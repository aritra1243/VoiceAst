import { useState, useRef, useCallback } from 'react';

export default function VisionCard() {
  const [streaming, setStreaming] = useState(false);
  const [faceData,  setFaceData]  = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const videoRef  = useRef(null);
  const streamRef = useRef(null);
  const timerRef  = useRef(null);

  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      setStreaming(true);

      // Simulate face analysis ping every 3s
      timerRef.current = setInterval(async () => {
        setAnalyzing(true);
        try {
          const res = await fetch('/api/analyze_face', { method: 'POST' });
          if (res.ok) {
            const d = await res.json();
            setFaceData(d);
          }
        } catch { /* backend may not have this endpoint yet */ }
        finally { setAnalyzing(false); }
      }, 3000);
    } catch (e) {
      console.warn('Camera error:', e);
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    if (timerRef.current) clearInterval(timerRef.current);
    setStreaming(false);
    setFaceData(null);
    setAnalyzing(false);
  }, []);

  return (
    <div className="glass-card rounded-lg p-5 flex flex-col gap-4 h-full">

      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-[rgba(0,247,255,0.12)]">
        <div className="flex items-center gap-2">
          <span className="text-lg">👁</span>
          <span className="font-orbitron text-xs tracking-[0.2em] text-glow-cyan">VISION MODULE</span>
        </div>
        <span className={`font-orbitron text-[9px] tracking-widest ${streaming ? 'text-glow-green animate-pulse' : 'text-[rgba(0,247,255,0.4)]'}`}>
          {streaming ? '● ACTIVE' : '○ OFFLINE'}
        </span>
      </div>

      {/* Video feed */}
      <div className="relative rounded bg-[rgba(0,0,0,0.6)] border border-[rgba(0,247,255,0.1)] overflow-hidden aspect-video">
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          id="vision-feed"
          className={`w-full h-full object-cover transition-opacity duration-300 ${streaming ? 'opacity-100' : 'opacity-0'}`}
        />
        {/* Overlay when no stream */}
        {!streaming && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
            <div className="text-4xl opacity-30">📷</div>
            <p className="font-orbitron text-[9px] tracking-widest text-[rgba(0,247,255,0.3)]">NO SIGNAL</p>
          </div>
        )}
        {/* HUD overlay */}
        {streaming && (
          <div className="absolute inset-0 pointer-events-none">
            {/* Corner brackets */}
            <div className="absolute top-2 left-2 w-6 h-6 border-t-2 border-l-2 border-[rgba(0,247,255,0.6)]"/>
            <div className="absolute top-2 right-2 w-6 h-6 border-t-2 border-r-2 border-[rgba(0,247,255,0.6)]"/>
            <div className="absolute bottom-2 left-2 w-6 h-6 border-b-2 border-l-2 border-[rgba(0,247,255,0.6)]"/>
            <div className="absolute bottom-2 right-2 w-6 h-6 border-b-2 border-r-2 border-[rgba(0,247,255,0.6)]"/>
            {/* Scanning line */}
            {analyzing && (
              <div className="absolute left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[rgba(0,247,255,0.8)] to-transparent"
                style={{ animation: 'scanLine 1.5s linear infinite', top: '30%' }}
              />
            )}
          </div>
        )}
      </div>

      {/* Face data */}
      {faceData && (
        <div className="rounded bg-[rgba(0,10,25,0.6)] border border-[rgba(0,247,255,0.1)] p-3 animate-fade-in-up">
          <div className="font-orbitron text-[8px] text-[rgba(0,247,255,0.4)] mb-1 tracking-widest">RECOGNITION</div>
          <p className="font-rajdhani text-xs text-[#c8f0ff]">{JSON.stringify(faceData)}</p>
        </div>
      )}

      {/* Controls */}
      <div className="flex gap-3">
        <button
          id="vision-start-btn"
          onClick={startCamera}
          disabled={streaming}
          className="hud-btn flex-1 disabled:opacity-40"
        >
          ▶ Enable
        </button>
        <button
          id="vision-stop-btn"
          onClick={stopCamera}
          disabled={!streaming}
          className="hud-btn danger flex-1 disabled:opacity-40"
        >
          ■ Disable
        </button>
      </div>

      {/* Capabilities */}
      <div className="grid grid-cols-2 gap-1.5 pt-1 border-t border-[rgba(0,247,255,0.08)]">
        {['Face Detection', 'Speaker ID', 'Emotion Analysis', 'Object Track'].map(cap => (
          <div key={cap} className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-[rgba(0,247,255,0.5)]" />
            <span className="font-rajdhani text-[10px] text-[rgba(0,247,255,0.5)]">{cap}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
