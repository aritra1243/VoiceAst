import { useEffect, useRef } from 'react';

/* Number of sniker / tick marks per ring */
const TICKS = 36; // every 10 degrees

function SnikerRing({ radius, tickLen = 6, color = 'rgba(0,247,255,0.4)' }) {
  const size = 2 * radius;
  const cx = radius;
  const cy = radius;

  const ticks = Array.from({ length: TICKS }, (_, i) => {
    const angle = (i * 360) / TICKS;
    const rad = (angle * Math.PI) / 180;
    const x1 = cx + (radius - 1) * Math.cos(rad);
    const y1 = cy + (radius - 1) * Math.sin(rad);
    const x2 = cx + (radius - 1 - tickLen) * Math.cos(rad);
    const y2 = cy + (radius - 1 - tickLen) * Math.sin(rad);
    // Emphasise every 30° (cardinal marks)
    const isMajor = i % 3 === 0;
    return { x1, y1, x2, y2, isMajor, angle };
  });

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className="absolute"
      style={{ top: '50%', left: '50%', transform: 'translate(-50%,-50%)' }}
    >
      {/* Ring circle */}
      <circle
        cx={cx} cy={cy} r={radius - 1}
        fill="none"
        stroke={color}
        strokeWidth={0.8}
      />
      {/* Sniker tick marks */}
      {ticks.map((t, i) => (
        <line
          key={i}
          x1={t.x1} y1={t.y1}
          x2={t.x2} y2={t.y2}
          stroke={t.isMajor ? 'rgba(0,247,255,0.7)' : 'rgba(0,247,255,0.25)'}
          strokeWidth={t.isMajor ? 1.5 : 0.8}
        />
      ))}
      {/* Cardinal degree labels at 0, 90, 180, 270 */}
      {[0, 90, 180, 270].map((deg) => {
        const rad = (deg * Math.PI) / 180;
        const lx = cx + (radius - 18) * Math.cos(rad);
        const ly = cy + (radius - 18) * Math.sin(rad);
        return (
          <text
            key={deg}
            x={lx} y={ly}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize="7"
            fill="rgba(0,247,255,0.5)"
            fontFamily="Orbitron, monospace"
          >
            {deg}°
          </text>
        );
      })}
    </svg>
  );
}

export default function ScannerCore({ isListening, wsStatus }) {
  const activeColor = isListening ? '#ffaa00' : '#00f7ff';

  return (
    <div className="flex flex-col items-center justify-center gap-4">

      {/* ── Scanner Label ── */}
      <div className="font-orbitron text-[9px] tracking-[0.4em] text-[rgba(0,247,255,0.5)] uppercase">
        Neural Scan Core v2.1
      </div>

      {/* ── Scanner Orb ── */}
      <div className="relative flex items-center justify-center" style={{ width: 320, height: 320 }}>

        {/* Outermost deco ring */}
        <div
          className="absolute rounded-full border border-[rgba(0,247,255,0.08)]"
          style={{ width: 316, height: 316 }}
        />

        {/* Sniker rings with tick marks — outer to inner */}
        <SnikerRing radius={148} tickLen={8} color="rgba(0,247,255,0.2)" />
        <SnikerRing radius={116} tickLen={6} color="rgba(0,247,255,0.25)" />
        <SnikerRing radius={84}  tickLen={5} color="rgba(0,247,255,0.3)" />
        <SnikerRing radius={56}  tickLen={4} color="rgba(0,247,255,0.35)" />

        {/* Rotating outer ring */}
        <div
          className="absolute rounded-full border border-dashed border-[rgba(0,247,255,0.2)] animate-spin-slow"
          style={{ width: 290, height: 290 }}
        />

        {/* Rotating inner ring (counter) */}
        <div
          className="absolute rounded-full animate-spin-reverse"
          style={{
            width: 220, height: 220,
            border: '1px solid rgba(0,247,255,0.15)',
          }}
        />

        {/* Radar sweep cone */}
        <div
          className="absolute rounded-full scanner-sweep"
          style={{ width: 296, height: 296 }}
        />

        {/* Cross-hair lines */}
        <div className="absolute" style={{ width: 296, height: 296 }}>
          {/* Horizontal */}
          <div
            className="absolute top-1/2 left-0 w-full"
            style={{ height: '1px', background: 'linear-gradient(90deg,transparent,rgba(0,247,255,0.15) 30%,rgba(0,247,255,0.4) 50%,rgba(0,247,255,0.15) 70%,transparent)' }}
          />
          {/* Vertical */}
          <div
            className="absolute left-1/2 top-0 h-full"
            style={{ width: '1px', background: 'linear-gradient(180deg,transparent,rgba(0,247,255,0.15) 30%,rgba(0,247,255,0.4) 50%,rgba(0,247,255,0.15) 70%,transparent)' }}
          />
        </div>

        {/* Arc Reactor center */}
        <div
          className="relative z-10 flex items-center justify-center rounded-full arc-reactor"
          style={{
            width: 96, height: 96,
            boxShadow: isListening
              ? '0 0 40px rgba(255,170,0,0.8), 0 0 80px rgba(255,170,0,0.4)'
              : undefined,
          }}
        >
          {/* Inner triangle */}
          <svg viewBox="0 0 60 60" width="52" height="52">
            <polygon
              points="30,6 54,48 6,48"
              fill="none"
              stroke={activeColor}
              strokeWidth="2"
              opacity="0.9"
            />
            <circle cx="30" cy="30" r="9"
              fill={isListening ? 'rgba(255,170,0,0.3)' : 'rgba(0,247,255,0.2)'}
              stroke={activeColor}
              strokeWidth="1.5"
            />
            <circle cx="30" cy="30" r="4"
              fill={isListening ? 'rgba(255,170,0,0.7)' : 'rgba(0,247,255,0.6)'}
            />
          </svg>
        </div>

        {/* Floating status text below orb */}
        <div
          className="absolute bottom-2 font-orbitron text-[9px] tracking-widest"
          style={{ color: activeColor, textShadow: `0 0 10px ${activeColor}` }}
        >
          {isListening ? '◉ PROCESSING INPUT' : wsStatus === 'online' ? '◎ STANDBY' : '⊘ OFFLINE'}
        </div>
      </div>

      {/* ── Waveform visualizer ── */}
      <div className="flex items-end gap-[3px] h-10">
        {Array.from({ length: 28 }, (_, i) => (
          <div
            key={i}
            className="viz-bar"
            style={{
              '--delay': `${0.3 + (i % 7) * 0.12}s`,
              height: isListening ? `${12 + Math.random() * 28}px` : '6px',
              transition: 'height 0.15s ease',
              opacity: isListening ? 1 : 0.35,
            }}
          />
        ))}
      </div>

      {/* ── Bottom label ── */}
      <div className="font-orbitron text-[8px] tracking-[0.35em] text-[rgba(0,247,255,0.35)] uppercase">
        ◀ Voice Analysis Engine ▶
      </div>
    </div>
  );
}
