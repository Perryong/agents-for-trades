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
  const winRateColor = summary.win_rate >= 50 ? 'text-green-400' : 'text-red-400';
  const expectancyColor = summary.expectancy >= 0 ? 'text-green-400' : 'text-red-400';

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-3">
      {/* Row 1: Win Rate, Expectancy, Profit Factor */}
      <div className="grid grid-cols-3 gap-3 mb-2">
        <div className="flex flex-col gap-0.5">
          <span className="text-xs text-gray-400">Win Rate</span>
          <span className={`text-sm font-semibold ${winRateColor}`}>
            {formatPct(summary.win_rate)}
          </span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-xs text-gray-400">Expectancy</span>
          <span className={`text-sm font-semibold ${expectancyColor}`}>
            {summary.expectancy >= 0
              ? `+${summary.expectancy.toFixed(2)}%`
              : `${summary.expectancy.toFixed(2)}%`}
          </span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-xs text-gray-400">Profit Factor</span>
          <span className="text-sm font-semibold text-gray-200">
            {formatFactor(summary.profit_factor)}
          </span>
        </div>
      </div>

      {/* Row 2: Avg Winner, Avg Loser, Total Closed */}
      <div className="grid grid-cols-3 gap-3">
        <div className="flex flex-col gap-0.5">
          <span className="text-xs text-gray-400">Avg Winner</span>
          <span className="text-sm font-semibold text-green-400">
            {`+${summary.avg_winner.toFixed(2)}%`}
          </span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-xs text-gray-400">Avg Loser</span>
          <span className="text-sm font-semibold text-red-400">
            {summary.avg_loser <= 0
              ? `${summary.avg_loser.toFixed(2)}%`
              : `-${summary.avg_loser.toFixed(2)}%`}
          </span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-xs text-gray-400">Total Closed</span>
          <span className="text-sm font-semibold text-gray-200">
            {summary.total_closed}
          </span>
        </div>
      </div>

      {/* Disclaimer — shown when <5 trades per D-08 */}
      {summary.disclaimer && (
        <p className="mt-2 text-xs text-yellow-400/80">
          {summary.disclaimer}
        </p>
      )}
    </div>
  );
}
