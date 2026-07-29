import { useEffect, useRef, useState } from 'react';

/* ──────────────────────────────────────────────────────────
   RoboticHead  —  pure CSS/SVG 3D robotic AI head
   Props:
     isTalking  – jaw animates open/close when true
     isListening – eye glow + head colour shifts amber
     wsStatus   – 'online' | 'offline'
   ────────────────────────────────────────────────────────── */

/* Waveform bars that pulse when talking */
function WaveformBars({ active, color }) {
  return (
    <div className="flex items-end justify-center gap-[3px]" style={{ height: 36 }}>
      {Array.from({ length: 20 }, (_, i) => (
        <div
          key={i}
          style={{
            width: 3,
            borderRadius: 2,
            background: color,
            boxShadow: active ? `0 0 6px ${color}` : 'none',
            height: active ? `${10 + Math.sin(i * 0.9) * 18 + 4}px` : '4px',
            transition: `height ${0.08 + (i % 4) * 0.04}s ease`,
            animationDelay: `${i * 0.05}s`,
            opacity: active ? 1 : 0.3,
          }}
        />
      ))}
    </div>
  );
}

/* HUD ring with tick marks */
function HudRing({ size, opacity = 0.3, rotate = 0, dashed = false }) {
  return (
    <div
      style={{
        position: 'absolute',
        width: size,
        height: size,
        top: '50%',
        left: '50%',
        transform: `translate(-50%,-50%) rotate(${rotate}deg)`,
        border: `1px ${dashed ? 'dashed' : 'solid'} rgba(0,247,255,${opacity})`,
        borderRadius: '50%',
        pointerEvents: 'none',
      }}
    />
  );
}

/* Corner bracket decoration */
function CornerBrackets({ color = 'rgba(0,247,255,0.4)', size = 12 }) {
  const s = size;
  const corners = [
    { top: 0, left: 0, borderTop: `2px solid ${color}`, borderLeft: `2px solid ${color}` },
    { top: 0, right: 0, borderTop: `2px solid ${color}`, borderRight: `2px solid ${color}` },
    { bottom: 0, left: 0, borderBottom: `2px solid ${color}`, borderLeft: `2px solid ${color}` },
    { bottom: 0, right: 0, borderBottom: `2px solid ${color}`, borderRight: `2px solid ${color}` },
  ];
  return (
    <>
      {corners.map((style, i) => (
        <div key={i} style={{ position: 'absolute', width: s, height: s, ...style }} />
      ))}
    </>
  );
}

/* The 3D robotic head built with CSS perspective + SVG */
function RoboticHead3D({ isTalking, isListening }) {
  const cyan = '#00f7ff';
  const amber = '#ffaa00';
  const activeColor = isListening ? amber : cyan;

  // Jaw animation: open when talking
  const [jawAngle, setJawAngle] = useState(0);
  const jawRef = useRef(null);

  useEffect(() => {
    if (!isTalking) {
      setJawAngle(0);
      return;
    }
    // Oscillate jaw between 0° and 18° while talking
    let frame = 0;
    const id = setInterval(() => {
      frame++;
      setJawAngle(Math.abs(Math.sin(frame * 0.22)) * 18);
    }, 40);
    return () => clearInterval(id);
  }, [isTalking]);

  // Subtle idle head bob
  const [bobY, setBobY] = useState(0);
  useEffect(() => {
    let t = 0;
    const id = setInterval(() => {
      t += 0.025;
      setBobY(Math.sin(t) * 3);
    }, 30);
    return () => clearInterval(id);
  }, []);

  return (
    <div
      style={{
        width: 220,
        height: 260,
        position: 'relative',
        transform: `translateY(${bobY}px)`,
        transition: 'transform 0.1s ease',
        filter: `drop-shadow(0 0 18px ${activeColor}88) drop-shadow(0 0 40px ${activeColor}44)`,
      }}
    >
      <svg
        width="220"
        height="260"
        viewBox="0 0 220 260"
        style={{ overflow: 'visible' }}
      >
        <defs>
          {/* Head metal gradient — gives 3D depth */}
          <linearGradient id="headGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%"   stopColor="#0a1628" />
            <stop offset="40%"  stopColor="#0d2040" />
            <stop offset="70%"  stopColor="#071530" />
            <stop offset="100%" stopColor="#020810" />
          </linearGradient>
          {/* Highlight gradient for 3D sheen */}
          <linearGradient id="sheenGrad" x1="0%" y1="0%" x2="60%" y2="100%">
            <stop offset="0%"   stopColor={`${activeColor}22`} />
            <stop offset="50%"  stopColor={`${activeColor}08`} />
            <stop offset="100%" stopColor="transparent" />
          </linearGradient>
          {/* Eye glow */}
          <radialGradient id="eyeGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%"   stopColor={activeColor} stopOpacity="1" />
            <stop offset="60%"  stopColor={activeColor} stopOpacity="0.5" />
            <stop offset="100%" stopColor={activeColor} stopOpacity="0" />
          </radialGradient>
          {/* Visor gradient */}
          <linearGradient id="visorGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%"   stopColor={`${activeColor}30`} />
            <stop offset="100%" stopColor={`${activeColor}08`} />
          </linearGradient>
          {/* Jaw gradient */}
          <linearGradient id="jawGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%"   stopColor="#0d2040" />
            <stop offset="100%" stopColor="#050f20" />
          </linearGradient>
          {/* Speaker grill gradient */}
          <linearGradient id="grillGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%"   stopColor={`${activeColor}40`} />
            <stop offset="100%" stopColor={`${activeColor}10`} />
          </linearGradient>
        </defs>

        {/* ── NECK ── */}
        <rect x="90" y="220" width="40" height="30" rx="4"
          fill="url(#headGrad)"
          stroke={`${activeColor}40`} strokeWidth="0.5"
        />
        {/* Neck detail lines */}
        {[228, 234, 240].map(y => (
          <line key={y} x1="90" y1={y} x2="130" y2={y}
            stroke={`${activeColor}25`} strokeWidth="0.5" />
        ))}

        {/* ── MAIN HEAD SHAPE ── */}
        {/* Outer frame / armour plate */}
        <path
          d="M 30 70 L 30 210 Q 30 220 40 220 L 180 220 Q 190 220 190 210 L 190 70 Q 190 50 170 45 L 110 30 L 50 45 Q 30 50 30 70 Z"
          fill="url(#headGrad)"
          stroke={activeColor}
          strokeWidth="0.8"
          strokeOpacity="0.6"
        />

        {/* Left side armour panel */}
        <path
          d="M 30 70 L 30 200 L 50 210 L 50 75 Z"
          fill="#060f1e"
          stroke={`${activeColor}30`}
          strokeWidth="0.5"
        />
        {/* Right side armour panel */}
        <path
          d="M 190 70 L 190 200 L 170 210 L 170 75 Z"
          fill="#060f1e"
          stroke={`${activeColor}30`}
          strokeWidth="0.5"
        />

        {/* Top antenna strip */}
        <rect x="95" y="22" width="30" height="10" rx="2"
          fill="#071530" stroke={`${activeColor}50`} strokeWidth="0.8"
        />
        <line x1="110" y1="12" x2="110" y2="22"
          stroke={activeColor} strokeWidth="1.5" opacity="0.7"
        />
        {/* Antenna tip — blinking */}
        <circle cx="110" cy="10" r="3"
          fill={isTalking ? activeColor : `${activeColor}60`}
          style={{ filter: isTalking ? `drop-shadow(0 0 4px ${activeColor})` : 'none' }}
        />

        {/* 3D sheen highlight (simulates light hitting top-left) */}
        <path
          d="M 50 45 Q 30 50 30 70 L 30 170 L 90 120 L 90 40 Z"
          fill="url(#sheenGrad)"
        />

        {/* ── FACE PLATE — slightly inset ── */}
        <rect x="48" y="60" width="124" height="152" rx="8"
          fill="#030c1a"
          stroke={`${activeColor}35`}
          strokeWidth="0.6"
        />

        {/* ── VISOR BAR (eyes area) ── */}
        <rect x="48" y="72" width="124" height="58" rx="4"
          fill="url(#visorGrad)"
          stroke={`${activeColor}50`}
          strokeWidth="0.8"
        />
        {/* Visor scan line */}
        <line x1="48" y1="101" x2="172" y2="101"
          stroke={`${activeColor}20`} strokeWidth="0.5" strokeDasharray="4 6"
        />

        {/* ── LEFT EYE ── */}
        {/* Eye socket */}
        <ellipse cx="82" cy="101" rx="22" ry="16"
          fill="#020810"
          stroke={activeColor}
          strokeWidth="1"
          strokeOpacity="0.7"
        />
        {/* Eye glow halo */}
        <ellipse cx="82" cy="101" rx="20" ry="14"
          fill="url(#eyeGlow)"
          opacity={isListening ? 0.7 : 0.4}
        />
        {/* Eye iris */}
        <ellipse cx="82" cy="101" rx="10" ry="9"
          fill={`${activeColor}30`}
          stroke={activeColor}
          strokeWidth="1.2"
        />
        {/* Eye pupil */}
        <ellipse cx="82" cy="101" rx="5" ry="5"
          fill={activeColor}
          opacity={isTalking ? 1 : 0.8}
          style={{ filter: `drop-shadow(0 0 3px ${activeColor})` }}
        />
        {/* Eye glint */}
        <ellipse cx="78" cy="97" rx="2" ry="1.5"
          fill="white" opacity="0.4"
        />

        {/* ── RIGHT EYE ── */}
        <ellipse cx="138" cy="101" rx="22" ry="16"
          fill="#020810"
          stroke={activeColor}
          strokeWidth="1"
          strokeOpacity="0.7"
        />
        <ellipse cx="138" cy="101" rx="20" ry="14"
          fill="url(#eyeGlow)"
          opacity={isListening ? 0.7 : 0.4}
        />
        <ellipse cx="138" cy="101" rx="10" ry="9"
          fill={`${activeColor}30`}
          stroke={activeColor}
          strokeWidth="1.2"
        />
        <ellipse cx="138" cy="101" rx="5" ry="5"
          fill={activeColor}
          opacity={isTalking ? 1 : 0.8}
          style={{ filter: `drop-shadow(0 0 3px ${activeColor})` }}
        />
        <ellipse cx="134" cy="97" rx="2" ry="1.5"
          fill="white" opacity="0.4"
        />

        {/* ── NOSE BRIDGE ── */}
        <path
          d="M 100 128 L 110 140 L 120 128"
          fill="none"
          stroke={`${activeColor}40`}
          strokeWidth="1"
        />

        {/* ── CHEEK PANEL DETAILS (left) ── */}
        <rect x="52" y="135" width="20" height="8" rx="2"
          fill={`${activeColor}15`} stroke={`${activeColor}35`} strokeWidth="0.5"
        />
        {[138,142,146].map(y => (
          <line key={y} x1="53" y1={y} x2="71" y2={y}
            stroke={`${activeColor}30`} strokeWidth="0.5" />
        ))}
        {/* ── CHEEK PANEL DETAILS (right) ── */}
        <rect x="148" y="135" width="20" height="8" rx="2"
          fill={`${activeColor}15`} stroke={`${activeColor}35`} strokeWidth="0.5"
        />
        {[138,142,146].map(y => (
          <line key={y} x1="149" y1={y} x2="167" y2={y}
            stroke={`${activeColor}30`} strokeWidth="0.5" />
        ))}

        {/* ── JAW (animated) ── */}
        {/* The pivot is at the top of the jaw (y=175) */}
        <g
          style={{
            transformOrigin: '110px 175px',
            transform: `rotate(${jawAngle}deg)`,
            transition: 'transform 0.04s linear',
          }}
        >
          {/* Jaw plate */}
          <path
            d="M 55 175 L 55 215 Q 55 222 65 222 L 155 222 Q 165 222 165 215 L 165 175 Z"
            fill="url(#jawGrad)"
            stroke={activeColor}
            strokeWidth="0.7"
            strokeOpacity="0.5"
          />

          {/* Speaker grill — animated when talking */}
          <rect x="65" y="182" width="90" height="28" rx="4"
            fill="url(#grillGrad)"
            stroke={`${activeColor}40`}
            strokeWidth="0.6"
          />
          {/* Grill lines */}
          {Array.from({ length: 6 }, (_, i) => (
            <line key={i}
              x1="68" y1={186 + i * 4} x2="152" y2={186 + i * 4}
              stroke={`${activeColor}${isTalking ? '60' : '25'}`}
              strokeWidth="0.8"
            />
          ))}
          {/* LED dots on jaw */}
          {[-28, -14, 0, 14, 28].map((dx, i) => (
            <circle key={i}
              cx={110 + dx} cy="215"
              r="2"
              fill={isTalking && i % 2 === 0 ? activeColor : `${activeColor}40`}
              style={{
                filter: isTalking && i % 2 === 0 ? `drop-shadow(0 0 3px ${activeColor})` : 'none',
              }}
            />
          ))}
        </g>

        {/* ── TOP HEAD PANEL (forehead details) ── */}
        {/* Central forehead jewel */}
        <circle cx="110" cy="52" r="6"
          fill={`${activeColor}20`}
          stroke={activeColor}
          strokeWidth="0.8"
          strokeOpacity="0.6"
        />
        <circle cx="110" cy="52" r="3"
          fill={isTalking ? activeColor : `${activeColor}60`}
          style={{ filter: isTalking ? `drop-shadow(0 0 5px ${activeColor})` : 'none' }}
        />
        {/* Forehead hex pattern */}
        <line x1="75" y1="55" x2="95" y2="55"
          stroke={`${activeColor}30`} strokeWidth="0.8" />
        <line x1="125" y1="55" x2="145" y2="55"
          stroke={`${activeColor}30`} strokeWidth="0.8" />

        {/* ── STATUS INDICATOR STRIPS ── */}
        {/* Left side vertical LED strip */}
        {[80, 95, 110, 125, 140, 155].map((y, i) => (
          <circle key={i}
            cx="36" cy={y} r="2"
            fill={`${activeColor}${isTalking && i % 2 === 0 ? '80' : '30'}`}
          />
        ))}
        {/* Right side vertical LED strip */}
        {[80, 95, 110, 125, 140, 155].map((y, i) => (
          <circle key={i}
            cx="184" cy={y} r="2"
            fill={`${activeColor}${isTalking && i % 2 === 1 ? '80' : '30'}`}
          />
        ))}
      </svg>
    </div>
  );
}

/* ── Main export — the full center panel ── */
export default function ScannerCore({ isListening, wsStatus, isTalking = false }) {
  const cyan  = '#00f7ff';
  const amber = '#ffaa00';
  const activeColor = isListening ? amber : cyan;

  return (
    <div className="flex flex-col items-center justify-center gap-3 select-none">

      {/* Label */}
      <div
        style={{
          fontFamily: 'Orbitron, monospace',
          fontSize: 9,
          letterSpacing: '0.4em',
          color: `${activeColor}88`,
          textTransform: 'uppercase',
        }}
      >
        PRIME · Neural Interface v3.0
      </div>

      {/* Head + HUD rings container */}
      <div style={{ position: 'relative', width: 320, height: 320, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>

        {/* HUD rings */}
        <HudRing size={310} opacity={0.08} />
        <HudRing size={280} opacity={0.12} dashed />
        <HudRing size={248} opacity={0.14} rotate={45} />

        {/* Rotating accent ring */}
        <div style={{
          position: 'absolute', width: 300, height: 300,
          borderRadius: '50%',
          border: '1px solid transparent',
          borderTop: `1px solid ${activeColor}30`,
          borderRight: `1px solid ${activeColor}15`,
          animation: 'spinSlow 12s linear infinite',
        }} />
        {/* Counter-rotating ring */}
        <div style={{
          position: 'absolute', width: 268, height: 268,
          borderRadius: '50%',
          border: `1px dashed ${activeColor}20`,
          animation: 'spinReverse 8s linear infinite',
        }} />

        {/* Corner brackets on a square frame */}
        <div style={{
          position: 'absolute', width: 240, height: 240,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{ position: 'relative', width: '100%', height: '100%' }}>
            <CornerBrackets color={`${activeColor}50`} size={14} />
          </div>
        </div>

        {/* Crosshair lines */}
        <div style={{ position: 'absolute', width: 300, height: 300 }}>
          <div style={{
            position: 'absolute', top: '50%', left: 0, right: 0, height: 1,
            background: `linear-gradient(90deg, transparent, ${activeColor}10 20%, ${activeColor}20 50%, ${activeColor}10 80%, transparent)`,
          }} />
          <div style={{
            position: 'absolute', left: '50%', top: 0, bottom: 0, width: 1,
            background: `linear-gradient(180deg, transparent, ${activeColor}10 20%, ${activeColor}20 50%, ${activeColor}10 80%, transparent)`,
          }} />
        </div>

        {/* The actual 3D head */}
        <RoboticHead3D isTalking={isTalking} isListening={isListening} />

        {/* Status tag */}
        <div
          style={{
            position: 'absolute', bottom: 8,
            fontFamily: 'Orbitron, monospace',
            fontSize: 9,
            letterSpacing: '0.3em',
            color: activeColor,
            textShadow: `0 0 8px ${activeColor}`,
            textTransform: 'uppercase',
          }}
        >
          {isTalking
            ? '◉ SPEAKING'
            : isListening
              ? '◎ PROCESSING'
              : wsStatus === 'online'
                ? '◎ STANDBY'
                : '⊘ OFFLINE'}
        </div>
      </div>

      {/* Waveform bars */}
      <WaveformBars active={isTalking || isListening} color={activeColor} />

      {/* Bottom label */}
      <div
        style={{
          fontFamily: 'Orbitron, monospace',
          fontSize: 8,
          letterSpacing: '0.35em',
          color: `${activeColor}40`,
          textTransform: 'uppercase',
        }}
      >
        ◀ Vocal Synthesis Engine ▶
      </div>

      {/* Inline keyframe styles */}
      <style>{`
        @keyframes spinSlow    { to { transform: rotate(360deg); } }
        @keyframes spinReverse { to { transform: rotate(-360deg); } }
      `}</style>
    </div>
  );
}
