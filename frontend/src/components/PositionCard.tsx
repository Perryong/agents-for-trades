import type { Position } from '../types';

interface PositionCardProps {
  position: Position;
  onClick?: () => void;
}

function fmt(val: number | null): string {
  if (val == null) return '—';
  return val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function PositionCard({ position: pos, onClick }: PositionCardProps) {
  const pnlColor = pos.pnl_pct == null ? 'text-text-primary'
    : pos.pnl_pct >= 0 ? 'text-accent-green' : 'text-accent-red';
  const pnlText = pos.pnl_pct != null ? `${pos.pnl_pct >= 0 ? '+' : ''}${pos.pnl_pct.toFixed(2)}%` : '—';
  const entryPrice = pos.fill_price ?? pos.entry_price;

  return (
    <div
      onClick={onClick}
      className="p-2 border-b border-border-subtle cursor-pointer hover:bg-bg-hover transition-colors"
    >
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[13px] font-mono font-medium text-text-primary">{pos.ticker}</span>
        <span className={`text-[11px] font-medium uppercase ${pos.direction === 'BUY' ? 'text-accent-green' : 'text-accent-red'}`}>
          {pos.direction}
        </span>
        <span className="flex-1" />
        <span className={`text-[13px] font-mono font-medium ${pnlColor}`}>{pnlText}</span>
      </div>
      <div className="flex items-center gap-3 text-[11px] text-text-tertiary font-mono">
        <span>Entry {fmt(entryPrice)}</span>
        {pos.stop_loss != null && <span>Stop <span className="text-accent-red">{fmt(pos.stop_loss)}</span></span>}
      </div>
    </div>
  );
}
