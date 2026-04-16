import { useEffect, useState } from 'react';

interface SurpriseData {
  ticker: string;
  outcome: string;
  predicted_confidence: number;
  pnl_pct: number | null;
  reasoning: string;
}

export function BiggestSurprise() {
  const [surprise, setSurprise] = useState<SurpriseData | null>(null);

  useEffect(() => {
    fetch('/api/predictions/performance')
      .then(res => res.ok ? res.json() : [])
      .then((data: Array<{ ticker: string; outcome: string | null; predicted_confidence: number; pnl_pct: number | null }>) => {
        // Find the trade with largest gap between confidence and outcome
        const withOutcome = data.filter(d => d.outcome != null && d.pnl_pct != null);
        if (withOutcome.length === 0) return;

        let biggest: typeof withOutcome[0] | null = null;
        let biggestGap = 0;

        for (const d of withOutcome) {
          // Surprise = high confidence loss or low confidence win
          const expectedWin = d.predicted_confidence >= 50;
          const actualWin = d.outcome === 'WIN';
          if (expectedWin !== actualWin) {
            const gap = Math.abs(d.predicted_confidence - 50);
            if (gap > biggestGap) {
              biggestGap = gap;
              biggest = d;
            }
          }
        }

        if (biggest) {
          setSurprise({
            ticker: biggest.ticker,
            outcome: biggest.outcome!,
            predicted_confidence: biggest.predicted_confidence,
            pnl_pct: biggest.pnl_pct,
            reasoning: biggest.outcome === 'WIN'
              ? `Low confidence (${biggest.predicted_confidence.toFixed(0)}%) but won — the system was cautious but the trade worked.`
              : `High confidence (${biggest.predicted_confidence.toFixed(0)}%) but lost — guardrails activated correctly.`,
          });
        }
      })
      .catch(() => {});
  }, []);

  if (!surprise) return null;

  const outcomeColor = surprise.outcome === 'WIN' ? 'text-accent-green' : 'text-accent-red';
  const pnlText = surprise.pnl_pct != null
    ? `${surprise.pnl_pct >= 0 ? '+' : ''}${surprise.pnl_pct.toFixed(2)}%`
    : '';

  return (
    <div className="bg-bg-elevated border border-border-subtle rounded-sm p-3">
      <p className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-2">Biggest Surprise</p>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[16px] font-mono font-medium text-text-primary">{surprise.ticker}</span>
        <span className={`text-[13px] font-mono font-medium ${outcomeColor}`}>
          {surprise.outcome} {pnlText}
        </span>
        <span className="text-[11px] text-text-tertiary">@ {surprise.predicted_confidence.toFixed(0)}% confidence</span>
      </div>
      <p className="text-[13px] text-text-secondary">{surprise.reasoning}</p>
    </div>
  );
}
