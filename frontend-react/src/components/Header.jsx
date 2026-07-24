import { useClock } from '../hooks/useClock';

const statusConfig = {
  online:  { label: 'SYSTEM ONLINE',  cls: 'status-online',  textCls: 'text-glow-green' },
  offline: { label: 'RECONNECTING…',  cls: 'status-offline', textCls: 'text-glow-red' },
  listening: { label: 'LISTENING…',   cls: 'status-listen',  textCls: 'text-glow-amber' },
};

export default function Header({ wsStatus }) {
  const { time, date, weather } = useClock();
  const cfg = statusConfig[wsStatus] ?? statusConfig.offline;

  return (
    <header className="glass-card relative z-10 flex items-center justify-between px-6 py-4 mb-5">

      {/* ── Logo ── */}
      <div className="flex items-center gap-4">
        <div className="relative flex items-center justify-center w-12 h-12 rounded-full arc-reactor shadow-cyan-glow">
          <svg viewBox="0 0 40 40" width="28" height="28">
            <polygon points="20,4 34,32 6,32" fill="none" stroke="#00f7ff" strokeWidth="2" opacity="0.9"/>
            <circle cx="20" cy="20" r="6" fill="rgba(0,247,255,0.3)" stroke="#00f7ff" strokeWidth="1.5"/>
          </svg>
        </div>
        <div>
          <h1 className="font-orbitron text-2xl font-bold text-glow-cyan tracking-[0.2em]">PRIME</h1>
          <p className="font-rajdhani text-[10px] text-[#4a8fa8] tracking-[0.2em] uppercase">Autonomous Intelligence System</p>
        </div>
      </div>

      {/* ── Status + Clock ── */}
      <div className="flex items-center gap-6">

        {/* Connection status */}
        <div className="flex items-center gap-2 px-4 py-2 glass-card rounded-sm">
          <span className={`w-2.5 h-2.5 rounded-full animate-pulse ${cfg.cls}`} />
          <span className={`font-orbitron text-[10px] tracking-widest ${cfg.textCls}`}>
            {cfg.label}
          </span>
        </div>

        {/* Weather */}
        <div className="hidden md:flex items-center gap-2 px-3 py-2 glass-card rounded-sm">
          <span className="text-xl">{weather.icon}</span>
          <div>
            <div className="font-orbitron text-sm text-glow-green">{weather.temp}</div>
            <div className="font-rajdhani text-[10px] text-[#4a8fa8] truncate max-w-[70px]">{weather.city}</div>
          </div>
        </div>

        {/* Clock */}
        <div className="text-right px-4 py-2 glass-card rounded-sm">
          <div className="font-orbitron text-xl text-glow-cyan tracking-[0.15em]">{time}</div>
          <div className="font-rajdhani text-[10px] text-[#4a8fa8] tracking-wider">{date}</div>
        </div>
      </div>
    </header>
  );
}
