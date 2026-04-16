import { useState, useEffect } from 'react';
import type { ScreenerPick, ScreenerStatus, ScreenerStrategyInfo } from '../types';
import { PickCard } from './PickCard';

interface WatchlistPanelProps {
  status: ScreenerStatus;
  picks: ScreenerPick[];
  screenedAt: string | null;
  errorMsg: string | null;
  onRefresh: (strategy: string, maxPicks: number) => void;
  onAnalyze: (ticker: string) => void;
}

function getRelativeTime(isoString: string): string {
  const diffMs = Date.now() - new Date(isoString).getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return 'just now';
  const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });
  if (diffMin < 60) return rtf.format(-diffMin, 'minute');
  return rtf.format(-Math.floor(diffMin / 60), 'hour');
}

function isStale(isoString: string): boolean {
  if (!isoString) return false;
  return Date.now() - new Date(isoString).getTime() > 15 * 60 * 1000;
}

export function WatchlistPanel({
  status,
  picks,
  screenedAt,
  errorMsg,
  onRefresh,
  onAnalyze,
}: WatchlistPanelProps) {
  const [strategies, setStrategies] = useState<ScreenerStrategyInfo[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState('momentum');
  const [maxPicks, setMaxPicks] = useState(5);

  // Fetch available strategies
  useEffect(() => {
    fetch('/api/screen/strategies')
      .then(r => r.ok ? r.json() : [])
      .then((data: ScreenerStrategyInfo[]) => {
        setStrategies(data);
        // Restore last used strategy from localStorage
        const saved = localStorage.getItem('screener_strategy');
        if (saved && data.some(s => s.name === saved)) setSelectedStrategy(saved);
      })
      .catch(() => {});
  }, []);

  const handleRefresh = () => {
    localStorage.setItem('screener_strategy', selectedStrategy);
    onRefresh(selectedStrategy, maxPicks);
  };

  return (
    <div>
      {/* Header + Strategy Picker */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">Screener</h2>
          {screenedAt && screenedAt !== '' && (
            <p className={`text-[11px] ${isStale(screenedAt) ? 'text-accent-amber' : 'text-text-secondary'}`}>
              Screened {getRelativeTime(screenedAt)}{isStale(screenedAt) && ' (stale)'}
            </p>
          )}
        </div>
        <button
          onClick={handleRefresh}
          disabled={status === 'loading'}
          className="px-3 py-1.5 bg-accent-blue text-white rounded-sm text-sm font-medium hover:bg-accent-blue/80 disabled:bg-bg-hover disabled:cursor-not-allowed transition-colors"
        >
          {status === 'loading' ? 'Screening...' : 'Scan'}
        </button>
      </div>

      {/* Strategy selector + max picks */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex-1">
          <select
            value={selectedStrategy}
            onChange={e => setSelectedStrategy(e.target.value)}
            className="w-full px-2 py-1 text-[13px] bg-bg-elevated border border-border-default rounded-sm text-text-primary"
          >
            {strategies.length > 0 ? (
              strategies.map(s => (
                <option key={s.name} value={s.name}>{s.display_name}</option>
              ))
            ) : (
              <option value="momentum">Momentum & Volume</option>
            )}
          </select>
        </div>
        <div className="flex items-center gap-1">
          <label className="text-[11px] text-text-tertiary">Picks:</label>
          <input
            type="number"
            value={maxPicks}
            onChange={e => setMaxPicks(Math.max(1, Math.min(10, parseInt(e.target.value) || 5)))}
            min={1}
            max={10}
            className="w-12 px-1 py-1 text-[13px] font-mono bg-bg-elevated border border-border-default rounded-sm text-text-primary text-center"
          />
        </div>
      </div>

      {/* Strategy description */}
      {strategies.length > 0 && (
        <p className="text-[11px] text-text-tertiary mb-3">
          {strategies.find(s => s.name === selectedStrategy)?.description ?? ''}
        </p>
      )}

      {/* Error banner */}
      {status === 'error' && errorMsg && (
        <div className="mb-4 p-3 rounded-sm bg-accent-red/10 border border-accent-red/30 text-accent-red text-sm">
          {errorMsg}
          <button onClick={handleRefresh} className="ml-2 underline font-medium">Retry</button>
        </div>
      )}

      {/* Loading skeleton */}
      {status === 'loading' && picks.length === 0 && (
        <div>
          <p className="text-sm text-text-secondary mb-3">Screening market...</p>
          <div className="space-y-3">
            {Array.from({ length: maxPicks }).map((_, i) => (
              <div key={i} className="animate-pulse rounded-sm bg-bg-hover h-32" />
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {status === 'idle' && picks.length === 0 && (
        <p className="text-center text-text-secondary py-12">
          Select a strategy and click Scan to screen the market
        </p>
      )}

      {/* Pick cards */}
      {picks.length > 0 && (
        <div className="space-y-3">
          {picks.map(pick => (
            <PickCard key={pick.ticker} pick={pick} onAnalyze={onAnalyze} />
          ))}
        </div>
      )}
    </div>
  );
}
