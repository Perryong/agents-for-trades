import type { ScoreSummary } from '../types';

interface ScoringCardProps {
  summary: ScoreSummary;
}

function formatPct(value: number, prefix = ''): string {
  const sign = prefix === '+' ? (value >= 0 ? '+' : '') : '';
  return `${sign}${value.toFixed(1)}%`;
}

function formatFactor(value: number): string {
  return value.toFixed(2);
}

export function ScoringCard({ summary }: ScoringCardProps) {
  const winRateColor = summary.win_rate >= 50 ? 'text-accent-green' : 'text-accent-red';
  const expectancyColor = summary.expectancy >= 0 ? 'text-accent-green' : 'text-accent-red';

  return (
    <div className="bg-bg-elevated border border-border-subtle rounded-sm p-3">
      {/* Row 1: Win Rate, Expectancy, Profit Factor */}
      <div className="grid grid-cols-3 gap-3 mb-2">
        <div className="flex flex-col gap-0.5">
          <span className="text-xs text-text-secondary">Win Rate</span>
          <span className={`text-sm font-semibold ${winRateColor}`}>
            {formatPct(summary.win_rate)}
          </span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-xs text-text-secondary">Expectancy</span>
          <span className={`text-sm font-semibold ${expectancyColor}`}>
            {summary.expectancy >= 0
              ? `+${summary.expectancy.toFixed(2)}%`
              : `${summary.expectancy.toFixed(2)}%`}
          </span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-xs text-text-secondary">Profit Factor</span>
          <span className="text-sm font-semibold text-text-primary">
            {formatFactor(summary.profit_factor)}
          </span>
        </div>
      </div>

      {/* Row 2: Avg Winner, Avg Loser, Total Closed */}
      <div className="grid grid-cols-3 gap-3">
        <div className="flex flex-col gap-0.5">
          <span className="text-xs text-text-secondary">Avg Winner</span>
          <span className="text-sm font-semibold text-accent-green">
            {`+${summary.avg_winner.toFixed(2)}%`}
          </span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-xs text-text-secondary">Avg Loser</span>
          <span className="text-sm font-semibold text-accent-red">
            {summary.avg_loser <= 0
              ? `${summary.avg_loser.toFixed(2)}%`
              : `-${summary.avg_loser.toFixed(2)}%`}
          </span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-xs text-text-secondary">Total Closed</span>
          <span className="text-sm font-semibold text-text-primary">
            {summary.total_closed}
          </span>
        </div>
      </div>

      {/* Disclaimer — shown when <5 trades per D-08 */}
      {summary.disclaimer && (
        <p className="mt-2 text-xs text-accent-amber/80">
          {summary.disclaimer}
        </p>
      )}
    </div>
  );
}
