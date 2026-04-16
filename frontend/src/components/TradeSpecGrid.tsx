import type { RecommendationTradeSpec } from '../types';

interface TradeSpecGridProps {
  spec: RecommendationTradeSpec;
  direction?: string | null;
}

function fmt(val: number | null): string {
  if (val == null) return '—';
  return val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function TradeSpecGrid({ spec, direction }: TradeSpecGridProps) {
  const rr = spec.risk_reward != null
    ? spec.risk_reward.toFixed(1)
    : spec.entry_price != null && spec.stop_loss != null && spec.target_price != null && spec.entry_price !== spec.stop_loss
      ? (direction === 'SELL'
          ? Math.abs(spec.entry_price - spec.target_price) / Math.abs(spec.stop_loss - spec.entry_price)
          : Math.abs(spec.target_price - spec.entry_price) / Math.abs(spec.entry_price - spec.stop_loss)
        ).toFixed(1)
      : '—';

  return (
    <div className="grid grid-cols-5 gap-2">
      <div>
        <p className="text-[11px] text-text-tertiary uppercase tracking-wider">Entry</p>
        <p className="text-[13px] font-mono text-text-primary">{fmt(spec.entry_price)}</p>
      </div>
      <div>
        <p className="text-[11px] text-text-tertiary uppercase tracking-wider">Stop</p>
        <p className="text-[13px] font-mono text-accent-red">{fmt(spec.stop_loss)}</p>
      </div>
      <div>
        <p className="text-[11px] text-text-tertiary uppercase tracking-wider">Target</p>
        <p className="text-[13px] font-mono text-accent-green">{fmt(spec.target_price)}</p>
      </div>
      <div>
        <p className="text-[11px] text-text-tertiary uppercase tracking-wider">Size</p>
        <p className="text-[13px] font-mono text-text-primary">{spec.position_size ?? '—'}</p>
      </div>
      <div>
        <p className="text-[11px] text-text-tertiary uppercase tracking-wider">R:R</p>
        <p className="text-[13px] font-mono text-text-primary">{rr}</p>
      </div>
    </div>
  );
}
