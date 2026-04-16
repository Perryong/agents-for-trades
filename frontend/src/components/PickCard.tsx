import type { ScreenerPick } from '../types';

interface PickCardProps {
  pick: ScreenerPick;
  onAnalyze: (ticker: string) => void;
}

const SCORE_BAR_COLOR: Record<string, string> = {
  green: 'bg-accent-green',
  yellow: 'bg-accent-amber',
  red: 'bg-accent-red',
};

function scoreColor(score: number): string {
  if (score >= 0.7) return 'green';
  if (score >= 0.4) return 'yellow';
  return 'red';
}

export function PickCard({ pick, onAnalyze }: PickCardProps) {
  const colorKey = scoreColor(pick.score);
  const barColorClass = SCORE_BAR_COLOR[colorKey];

  const volumeValue =
    pick.key_metrics?.volume_ratio ?? pick.key_metrics?.volume_score;
  const momentumValue =
    pick.key_metrics?.momentum_5d ?? pick.key_metrics?.momentum_score;

  return (
    <div className="rounded-sm border border-border-subtle bg-bg-elevated p-4 space-y-3">
      {/* Header row */}
      <div className="flex justify-between items-center">
        <span className="text-lg font-bold text-text-primary">
          {pick.ticker}
        </span>
        <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-accent-blue/15 text-accent-blue">
          {Math.round(pick.confidence * 100)}%
        </span>
      </div>

      {/* Score bar */}
      <div>
        <div className="flex justify-between text-xs text-text-secondary mb-1">
          <span>Score</span>
          <span>{pick.score.toFixed(2)}</span>
        </div>
        <div className="w-full bg-bg-hover rounded-full h-2">
          <div
            className={`${barColorClass} h-2 rounded-full`}
            style={{ width: `${Math.round(pick.score * 100)}%` }}
          />
        </div>
      </div>

      {/* Rationale */}
      <p className="text-sm text-text-secondary line-clamp-2">
        {pick.rationale}
      </p>

      {/* Metrics row */}
      <div className="flex gap-4 text-xs text-text-secondary">
        <span>
          Vol:{' '}
          {volumeValue !== undefined ? `${volumeValue.toFixed(1)}x` : '—'}
        </span>
        <span>
          Mom:{' '}
          {momentumValue !== undefined
            ? `${momentumValue > 0 ? '+' : ''}${(momentumValue * 100).toFixed(1)}%`
            : '—'}
        </span>
        <span>{pick.sector ?? '—'}</span>
      </div>

      {/* Analyze button */}
      <button
        onClick={() => onAnalyze(pick.ticker)}
        className="w-full py-1.5 px-3 bg-accent-blue text-white rounded-sm text-sm font-medium hover:bg-accent-blue/80 transition-colors"
      >
        Analyze {pick.ticker}
      </button>
    </div>
  );
}
