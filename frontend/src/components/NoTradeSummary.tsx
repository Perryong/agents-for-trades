import type { Recommendation } from '../types';

interface NoTradeSummaryProps {
  recommendations: Recommendation[];
}

export function NoTradeSummary({ recommendations }: NoTradeSummaryProps) {
  const noTradeRecs = recommendations.filter(r => !r.direction);
  const allPending = recommendations.filter(r => r.direction && r.status === 'pending');

  // Only show when there are no actionable recommendations
  if (allPending.length > 0) return null;
  if (recommendations.length === 0) return null;
  if (noTradeRecs.length === 0) return null;

  return (
    <div className="p-6 text-center">
      <p className="text-[18px] font-semibold text-text-primary mb-2">0 recommendations today</p>
      <p className="text-[13px] text-text-secondary mb-4">
        No opportunities met criteria — discipline is a feature
      </p>

      {/* Evaluation table */}
      {noTradeRecs.length > 0 && (
        <div className="text-left max-w-lg mx-auto">
          <p className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-2">Evaluated Tickers</p>
          <div className="space-y-1">
            {noTradeRecs.map(rec => (
              <div key={rec.id} className="flex items-center gap-3 py-1 border-b border-border-subtle">
                <span className="text-[13px] font-mono font-medium text-text-primary w-16">{rec.ticker}</span>
                <span className={`text-[13px] font-mono ${rec.confidence < 50 ? 'text-accent-amber' : 'text-text-secondary'}`}>
                  {rec.confidence.toFixed(0)}%
                </span>
                <span className="text-[13px] text-text-secondary flex-1 truncate">
                  {rec.no_trade_reason || 'Below threshold'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
