import { useEffect, useRef, useState } from 'react';

/* =========================================================================
   IRON MAN JARVIS HOLOGRAPHIC BLUEPRINT 3D HEAD & ARC REACTOR
   Renders a pixel-perfect holographic wireframe vector matching the Iron Man
   blueprint schematic with glowing cyan helmet contour, glowing eye slits,
   red collar accent lines, glowing Arc Reactor, and animated talking jaw.
   ========================================================================= */

export default function ScannerCore({ isListening, isTalking = false, wsStatus }) {
  const containerRef = useRef(null);

  // Mouse tracking for subtle 3D perspective tilt
  const [tilt, setTilt] = useState({ rx: 0, ry: 0 });

  useEffect(() => {
    const handleMouseMove = (e) => {
      const cx = window.innerWidth / 2;
      const cy = window.innerHeight / 2;
      const rx = ((e.clientY - cy) / cy) * -10; // max -10 to +10 deg
      const ry = ((e.clientX - cx) / cx) * 12;  // max -12 to +12 deg
      setTilt({ rx, ry });
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  // Jaw animation when talking
  const [jawOffset, setJawOffset] = useState(0);

  useEffect(() => {
    if (!isTalking) {
      setJawOffset(0);
      return;
    }
    let frame = 0;
    const interval = setInterval(() => {
      frame++;
      // Open jaw down by 0 to 14px while talking
      setJawOffset(Math.abs(Math.sin(frame * 0.25)) * 14);
    }, 35);
    return () => clearInterval(interval);
  }, [isTalking]);

  // Color theme: Amber when listening, Cyan when standby/speaking
  const cyan = '#00f7ff';
  const amber = '#ffaa00';
  const activeColor = isListening ? amber : cyan;
  const redAccent = '#ff2255';

  return (
    <div className="flex flex-col items-center justify-center select-none py-2">
      {/* ── Holographic 3D Viewport ── */}
      <div
        ref={containerRef}
        className="relative flex items-center justify-center rounded-2xl overflow-hidden"
        style={{
          width: 360,
          height: 420,
          perspective: 1000,
          background: 'radial-gradient(circle at center, rgba(0,25,50,0.4) 0%, rgba(2,6,16,0.92) 85%)',
          border: `1px solid ${activeColor}33`,
          boxShadow: `0 0 30px ${activeColor}22, inset 0 0 50px rgba(0,10,25,0.9)`,
        }}
      >
        {/* Hologram Blueprint Grid */}
        <div
          className="absolute inset-0 pointer-events-none opacity-20"
          style={{
            backgroundImage: `linear-gradient(${activeColor}22 1px, transparent 1px), linear-gradient(90deg, ${activeColor}22 1px, transparent 1px)`,
            backgroundSize: '24px 24px',
          }}
        />

        {/* Outer Corner Frame Brackets */}
        <div className="absolute top-3 left-3 w-4 h-4 border-t-2 border-l-2" style={{ borderColor: activeColor }} />
        <div className="absolute top-3 right-3 w-4 h-4 border-t-2 border-r-2" style={{ borderColor: activeColor }} />
        <div className="absolute bottom-3 left-3 w-4 h-4 border-b-2 border-l-2" style={{ borderColor: activeColor }} />
        <div className="absolute bottom-3 right-3 w-4 h-4 border-b-2 border-r-2" style={{ borderColor: activeColor }} />

        {/* ── 3D Tilting Hologram Group ── */}
        <div
          className="relative transition-transform duration-100 ease-out"
          style={{
            width: 320,
            height: 380,
            transformStyle: 'preserve-3d',
            transform: `rotateX(${tilt.rx}deg) rotateY(${tilt.ry}deg)`,
            filter: `drop-shadow(0 0 12px ${activeColor}aa) drop-shadow(0 0 25px ${activeColor}44)`,
          }}
        >
          <svg
            width="320"
            height="380"
            viewBox="0 0 320 380"
            className="w-full h-full overflow-visible"
          >
            <defs>
              {/* Eye Glow Radial Gradient */}
              <radialGradient id="eyeGlow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor={activeColor} stopOpacity="1" />
                <stop offset="50%" stopColor={activeColor} stopOpacity="0.8" />
                <stop offset="100%" stopColor={activeColor} stopOpacity="0" />
              </radialGradient>
              {/* Arc Reactor Glow Gradient */}
              <radialGradient id="arcGlow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#ffffff" stopOpacity="1" />
                <stop offset="40%" stopColor={activeColor} stopOpacity="0.9" />
                <stop offset="100%" stopColor={activeColor} stopOpacity="0" />
              </radialGradient>
            </defs>

            {/* =========================================================
               IRON MAN HELMET & SUIT WIREFRAME CONTOURS (Exact Schematic)
               ========================================================= */}

            {/* ── 1. HELMET UPPER CRANIUM (CYAN CONTOUR) ── */}
            <path
              d="
                M 160,30
                C 115,30 95,55 95,90
                L 95,135
                C 95,145 105,152 110,155
                L 160,165
                L 210,155
                C 215,152 225,145 225,135
                L 225,90
                C 225,55 205,30 160,30 Z
              "
              fill="none"
              stroke={activeColor}
              strokeWidth="1.8"
            />

            {/* Forehead Ridge / Crest Detail Lines */}
            <path
              d="M 125,48 L 160,62 L 195,48"
              fill="none"
              stroke={activeColor}
              strokeWidth="1.2"
              opacity="0.8"
            />
            <line x1="160" y1="30" x2="160" y2="62" stroke={activeColor} strokeWidth="1.2" opacity="0.8" />

            {/* Brow Line Contour */}
            <path
              d="M 100,88 L 135,100 L 160,94 L 185,100 L 220,88"
              fill="none"
              stroke={activeColor}
              strokeWidth="1.5"
            />

            {/* Cheekbone Side Contours */}
            <path d="M 98,110 L 118,140 L 128,145" fill="none" stroke={activeColor} strokeWidth="1.2" opacity="0.75" />
            <path d="M 222,110 L 202,140 L 192,145" fill="none" stroke={activeColor} strokeWidth="1.2" opacity="0.75" />

            {/* ── 2. GLOWING EYE SLITS ── */}
            {/* Left Eye */}
            <path
              d="M 112,106 L 142,112 L 144,116 L 115,112 Z"
              fill={activeColor}
              stroke={activeColor}
              strokeWidth="1"
              style={{ filter: isTalking ? `drop-shadow(0 0 8px ${activeColor})` : `drop-shadow(0 0 4px ${activeColor})` }}
            />
            {/* Right Eye */}
            <path
              d="M 208,106 L 178,112 L 176,116 L 205,112 Z"
              fill={activeColor}
              stroke={activeColor}
              strokeWidth="1"
              style={{ filter: isTalking ? `drop-shadow(0 0 8px ${activeColor})` : `drop-shadow(0 0 4px ${activeColor})` }}
            />

            {/* Nose Ridge Detail */}
            <path d="M 160,94 L 155,124 L 160,130 L 165,124 Z" fill="none" stroke={activeColor} strokeWidth="1.2" opacity="0.85" />

            {/* ── 3. ANIMATED TALKING LOWER JAW ── */}
            <g style={{ transform: `translateY(${jawOffset}px)`, transition: 'transform 0.04s ease-out' }}>
              {/* Lower Jawline Contour */}
              <path
                d="
                  M 120,152
                  L 125,178
                  L 142,192
                  L 160,196
                  L 178,192
                  L 195,178
                  L 200,152
                  L 160,165 Z
                "
                fill="rgba(0,15,30,0.6)"
                stroke={activeColor}
                strokeWidth="1.8"
              />
              {/* Chin Triangular Lines */}
              <path d="M 142,192 L 160,172 L 178,192" fill="none" stroke={activeColor} strokeWidth="1.2" opacity="0.75" />
              <line x1="160" y1="172" x2="160" y2="196" stroke={activeColor} strokeWidth="1.2" opacity="0.75" />

              {/* Mouth Slot / Speaker Vent Glow */}
              <line
                x1="138" y1="162" x2="182" y2="162"
                stroke={activeColor}
                strokeWidth={isTalking ? "3" : "1.5"}
                opacity={isTalking ? 1 : 0.6}
              />
            </g>

            {/* ── 4. COLLAR & NECK (RED WIREFRAME ACCENTS) ── */}
            {/* Neck Cylindrical Wireframe Lines */}
            <path d="M 132,198 L 130,225 L 190,225 L 188,198" fill="none" stroke={redAccent} strokeWidth="1.4" opacity="0.85" />
            <path d="M 130,212 L 190,212" stroke={redAccent} strokeWidth="1.2" opacity="0.75" />

            {/* Red Collar Joint Ribs */}
            <path d="M 138,202 L 148,225" stroke={redAccent} strokeWidth="1.2" opacity="0.8" />
            <path d="M 182,202 L 172,225" stroke={redAccent} strokeWidth="1.2" opacity="0.8" />
            <circle cx="160" cy="208" r="3" fill={redAccent} opacity="0.9" />

            {/* ── 5. SHOULDERS & CHEST CONTOUR ── */}
            {/* Left & Right Shoulder Outline (Cyan Blueprint) */}
            <path
              d="
                M 60,265
                C 85,245 110,230 130,225
                L 190,225
                C 210,230 235,245 260,265
                L 275,310
                L 245,340
                L 160,345
                L 75,340
                L 45,310 Z
              "
              fill="none"
              stroke={activeColor}
              strokeWidth="1.6"
            />

            {/* Chest Armor Ribs & Panel Lines */}
            <path d="M 130,225 L 110,270 L 60,265" fill="none" stroke={activeColor} strokeWidth="1.2" opacity="0.75" />
            <path d="M 190,225 L 210,270 L 260,265" fill="none" stroke={activeColor} strokeWidth="1.2" opacity="0.75" />

            {/* Red Shoulder Socket Circles */}
            <circle cx="95" cy="260" r="10" fill="none" stroke={redAccent} strokeWidth="1.4" />
            <circle cx="225" cy="260" r="10" fill="none" stroke={redAccent} strokeWidth="1.4" />
            <circle cx="95" cy="260" r="4" fill={redAccent} opacity="0.8" />
            <circle cx="225" cy="260" r="4" fill={redAccent} opacity="0.8" />

            {/* V-shaped Chest Armor Trim Lines */}
            <path d="M 110,270 L 160,305 L 210,270" fill="none" stroke={redAccent} strokeWidth="1.4" />
            <path d="M 125,285 L 160,320 L 195,285" fill="none" stroke={activeColor} strokeWidth="1.2" opacity="0.8" />

            {/* ── 6. GLOWING ARC REACTOR CORE (CHEST CENTER) ── */}
            <g style={{ transform: 'translate(160px, 288px)' }}>
              {/* Outer Glowing Ring */}
              <circle
                r="30"
                fill="none"
                stroke={activeColor}
                strokeWidth="2"
                style={{ filter: `drop-shadow(0 0 10px ${activeColor})` }}
              />
              {/* Outer Ticked Ring */}
              <circle
                r="25"
                fill="none"
                stroke={activeColor}
                strokeWidth="1"
                strokeDasharray="4 3"
                opacity="0.85"
              />
              {/* Middle Solid Ring */}
              <circle
                r="18"
                fill="none"
                stroke={activeColor}
                strokeWidth="1.5"
              />
              {/* Arc Reactor Vanes (10 Radial Lines) */}
              {Array.from({ length: 10 }).map((_, i) => {
                const angle = (i * 360) / 10;
                return (
                  <line
                    key={i}
                    x1={Math.cos((angle * Math.PI) / 180) * 18}
                    y1={Math.sin((angle * Math.PI) / 180) * 18}
                    x2={Math.cos((angle * Math.PI) / 180) * 25}
                    y2={Math.sin((angle * Math.PI) / 180) * 25}
                    stroke={activeColor}
                    strokeWidth="1.5"
                  />
                );
              })}
              {/* Inner Core Halo */}
              <circle
                r="12"
                fill="url(#arcGlow)"
                style={{ filter: isTalking ? `drop-shadow(0 0 12px ${activeColor})` : `drop-shadow(0 0 6px ${activeColor})` }}
              />
              {/* Core Center Ring */}
              <circle r="6" fill="none" stroke="#ffffff" strokeWidth="1.5" />
              <circle r="2.5" fill="#ffffff" />
            </g>

            {/* ── 7. BACKGROUND HOLOGRAM SCHEMATIC CIRCLES ── */}
            <g opacity="0.35" style={{ transform: 'translate(45px, 90px)' }}>
              <circle r="22" fill="none" stroke={activeColor} strokeWidth="0.8" strokeDasharray="3 3" />
              <circle r="14" fill="none" stroke={activeColor} strokeWidth="0.8" />
              <line x1="-22" y1="0" x2="22" y2="0" stroke={activeColor} strokeWidth="0.8" />
              <line x1="0" y1="-22" x2="0" y2="22" stroke={activeColor} strokeWidth="0.8" />
            </g>

            <g opacity="0.35" style={{ transform: 'translate(275px, 90px)' }}>
              <circle r="20" fill="none" stroke={activeColor} strokeWidth="0.8" strokeDasharray="4 2" />
              <circle r="10" fill="none" stroke={activeColor} strokeWidth="0.8" />
            </g>
          </svg>
        </div>
      </div>
    </div>
  );
}
