export default function HistoryCard({ history }) {
  return (
    <div className="glass-card rounded-lg p-5 flex flex-col gap-4 h-full">

      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-[rgba(0,247,255,0.12)]">
        <div className="flex items-center gap-2">
          <span className="text-lg">📜</span>
          <span className="font-orbitron text-xs tracking-[0.2em] text-glow-cyan">COMMAND HISTORY</span>
        </div>
        <span className="font-orbitron text-[9px] text-[rgba(0,247,255,0.4)] tracking-widest">
          {history.length} ENTRIES
        </span>
      </div>

      {/* History list */}
      <div className="flex-1 overflow-y-auto flex flex-col gap-2 pr-1 max-h-60">
        {history.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-2 opacity-40">
            <div className="text-3xl">📭</div>
            <p className="font-orbitron text-[9px] tracking-widest text-[rgba(0,247,255,0.5)]">NO COMMANDS YET</p>
          </div>
        ) : (
          [...history].reverse().map((item, i) => (
            <div
              key={i}
              className={`history-item ${item.success ? 'success' : 'fail'} rounded-sm px-2 py-1.5 bg-[rgba(0,10,25,0.5)]`}
            >
              <div className="flex items-center justify-between mb-0.5">
                <span className={`font-orbitron text-[8px] tracking-widest ${item.success ? 'text-glow-green' : 'text-glow-red'}`}>
                  {item.success ? '✓ SUCCESS' : '✗ FAILED'}
                </span>
                <span className="font-orbitron text-[8px] text-[rgba(0,247,255,0.3)]">{item.time}</span>
              </div>
              <p className="font-rajdhani text-xs text-[#c8f0ff] leading-snug">{item.text}</p>
            </div>
          ))
        )}
      </div>

      {/* Footer stats */}
      <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[rgba(0,247,255,0.08)]">
        <div className="text-center">
          <div className="font-orbitron text-lg text-glow-green">
            {history.filter(h => h.success).length}
          </div>
          <div className="font-orbitron text-[8px] text-[rgba(0,247,255,0.4)] tracking-widest">SUCCESS</div>
        </div>
        <div className="text-center">
          <div className="font-orbitron text-lg text-glow-red">
            {history.filter(h => !h.success).length}
          </div>
          <div className="font-orbitron text-[8px] text-[rgba(0,247,255,0.4)] tracking-widest">FAILED</div>
        </div>
      </div>
    </div>
  );
}
