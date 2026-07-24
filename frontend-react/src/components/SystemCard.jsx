import { useState, useEffect } from 'react';

function StatRow({ label, value, color = 'cyan' }) {
  const colorMap = {
    cyan:  'bg-[rgba(0,247,255,0.7)]',
    green: 'bg-[rgba(0,255,136,0.7)]',
    amber: 'bg-[rgba(255,170,0,0.7)]',
    red:   'bg-[rgba(255,51,102,0.7)]',
  };
  const pct = Math.min(100, Math.max(0, parseFloat(value) || 0));

  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between">
        <span className="font-orbitron text-[9px] text-[rgba(0,247,255,0.5)] tracking-widest uppercase">{label}</span>
        <span className="font-orbitron text-[9px] text-[#c8f0ff]">{value}</span>
      </div>
      <div className="h-1 rounded-full bg-[rgba(255,255,255,0.06)] overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${colorMap[color]}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function SystemCard({ totalCommands, successCount }) {
  const [uptime, setUptime] = useState(0);
  const [memPct] = useState(Math.round(40 + Math.random() * 35));
  const [cpuPct] = useState(Math.round(20 + Math.random() * 40));

  useEffect(() => {
    const id = setInterval(() => setUptime(s => s + 1), 1000);
    return () => clearInterval(id);
  }, []);

  const formatUptime = (s) => {
    const h = Math.floor(s / 3600).toString().padStart(2, '0');
    const m = Math.floor((s % 3600) / 60).toString().padStart(2, '0');
    const sec = (s % 60).toString().padStart(2, '0');
    return `${h}:${m}:${sec}`;
  };

  const successRate = totalCommands > 0
    ? Math.round((successCount / totalCommands) * 100)
    : 100;

  return (
    <div className="glass-card rounded-lg p-5 flex flex-col gap-4 h-full">

      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-[rgba(0,247,255,0.12)]">
        <div className="flex items-center gap-2">
          <span className="text-lg">💻</span>
          <span className="font-orbitron text-xs tracking-[0.2em] text-glow-cyan">SYSTEM STATUS</span>
        </div>
        <span className="font-orbitron text-[9px] text-glow-green tracking-widest">● NOMINAL</span>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: 'Commands', value: totalCommands, icon: '⚡' },
          { label: 'Success Rate', value: `${successRate}%`, icon: '✅' },
          { label: 'Uptime', value: formatUptime(uptime), icon: '⏱' },
          { label: 'Sessions', value: '1', icon: '🔗' },
        ].map(({ label, value, icon }) => (
          <div key={label} className="rounded bg-[rgba(0,10,25,0.6)] border border-[rgba(0,247,255,0.08)] p-3">
            <div className="text-base mb-1">{icon}</div>
            <div className="font-orbitron text-sm text-glow-cyan">{value}</div>
            <div className="font-rajdhani text-[10px] text-[rgba(0,247,255,0.4)] tracking-wider mt-0.5">{label}</div>
          </div>
        ))}
      </div>

      {/* Performance bars */}
      <div className="flex flex-col gap-2 pt-1">
        <StatRow label="CPU Usage" value={`${cpuPct}%`} color={cpuPct > 70 ? 'red' : 'cyan'} />
        <StatRow label="Memory"    value={`${memPct}%`} color={memPct > 80 ? 'amber' : 'green'} />
        <StatRow label="Success"   value={`${successRate}%`} color="green" />
      </div>

      {/* Module status */}
      <div className="flex flex-col gap-1.5 pt-1 border-t border-[rgba(0,247,255,0.08)]">
        {[
          { name: 'Voice Recognition', ok: true },
          { name: 'Speaker ID',        ok: true },
          { name: 'Vision Module',     ok: true },
          { name: 'Intent Engine',     ok: true },
        ].map(({ name, ok }) => (
          <div key={name} className="flex items-center justify-between">
            <span className="font-rajdhani text-xs text-[rgba(0,247,255,0.6)]">{name}</span>
            <span className={`font-orbitron text-[9px] ${ok ? 'text-glow-green' : 'text-glow-red'}`}>
              {ok ? '● ACTIVE' : '○ INACTIVE'}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
