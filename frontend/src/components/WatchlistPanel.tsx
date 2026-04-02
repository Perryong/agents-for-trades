import type { ScreenerPick, ScreenerStatus } from '../types';
import { PickCard } from './PickCard';

interface WatchlistPanelProps {
  status: ScreenerStatus;
  picks: ScreenerPick[];
  screenedAt: string | null;
  errorMsg: string | null;
  onRefresh: () => void;
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
  return (
    <div>
      {/* Header section */}
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Screener
          </h2>
          {screenedAt && screenedAt !== '' && (
            <p
              className={`text-xs ${
                isStale(screenedAt)
                  ? 'text-amber-500'
                  : 'text-gray-500 dark:text-gray-400'
              }`}
            >
              Screened {getRelativeTime(screenedAt)}
              {isStale(screenedAt) && ' (stale)'}
            </p>
          )}
        </div>
        <button
          onClick={onRefresh}
          disabled={status === 'loading'}
          className="px-3 py-1.5 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
        >
          {status === 'loading' ? 'Screening...' : 'Refresh'}
        </button>
      </div>

      {/* Error banner */}
      {status === 'error' && errorMsg && (
        <div className="mb-4 p-3 rounded-md bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 text-sm">
          {errorMsg}
          <button onClick={onRefresh} className="ml-2 underline font-medium">
            Retry
          </button>
        </div>
      )}

      {/* Loading skeleton — only on first load (no existing picks) */}
      {status === 'loading' && picks.length === 0 && (
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
            Screening market...
          </p>
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className="animate-pulse rounded-lg bg-gray-200 dark:bg-gray-700 h-32"
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {status === 'idle' && picks.length === 0 && (
        <p className="text-center text-gray-500 dark:text-gray-400 py-12">
          Click Refresh to screen the market
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
