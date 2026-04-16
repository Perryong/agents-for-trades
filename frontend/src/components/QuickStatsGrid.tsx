import type { QuickStats } from '../types';

interface QuickStatsGridProps {
  stats: QuickStats | null;
}

export function QuickStatsGrid({ stats }: QuickStatsGridProps) {
  const winRateColor = stats && stats.win_rate > 0 ? 'text-accent-green' : 'text-text-primary';
  const weekPnlColor = stats == null ? 'text-text-primary'
    : stats.week_pnl >= 0 ? 'text-accent-green' : 'text-accent-red';

  return (
    <div className="grid grid-cols-2 gap-3">
      <div>
        <p className="text-[11px] text-text-tertiary mb-1">Win Rate</p>
        <p className={`text-[16px] font-medium font-mono ${winRateColor}`}>
          {stats ? `${stats.win_rate.toFixed(1)}%` : '—'}
        </p>
      </div>
      <div>
        <p className="text-[11px] text-text-tertiary mb-1">Open Positions</p>
        <p className="text-[16px] font-medium font-mono text-text-primary">
          {stats ? stats.open_positions : '—'}
        </p>
      </div>
      <div>
        <p className="text-[11px] text-text-tertiary mb-1">Week P&L</p>
        <p className={`text-[16px] font-medium font-mono ${weekPnlColor}`}>
          {stats ? `${stats.week_pnl >= 0 ? '+' : ''}${stats.week_pnl.toFixed(2)}%` : '—'}
        </p>
      </div>
      <div>
        <p className="text-[11px] text-text-tertiary mb-1">Expectancy</p>
        <p className="text-[16px] font-medium font-mono text-text-primary">
          {stats ? stats.expectancy.toFixed(2) : '—'}
        </p>
      </div>
    </div>
  );
}
