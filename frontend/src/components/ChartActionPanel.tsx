import type { ChartOverlay } from '../types';

interface ChartActionPanelProps {
  overlay: ChartOverlay;
  onViewAnalysis: () => void;
}

function SignalBadge({ signal }: { signal: string }) {
  const upper = signal.toUpperCase();
  if (upper.includes('BUY')) {
    return (
      <span className="px-2 py-0.5 rounded text-xs font-bold bg-green-600 text-white">
        {signal}
      </span>
    );
  }
  if (upper.includes('SELL')) {
    return (
      <span className="px-2 py-0.5 rounded text-xs font-bold bg-red-600 text-white">
        {signal}
      </span>
    );
  }
  return (
    <span className="px-2 py-0.5 rounded text-xs font-bold bg-gray-500 text-white">
      {signal}
    </span>
  );
}

export function ChartActionPanel({ overlay, onViewAnalysis }: ChartActionPanelProps) {
  const legsText = overlay.options_legs
    ? overlay.options_legs.length > 60
      ? overlay.options_legs.slice(0, 60) + '...'
      : overlay.options_legs
    : null;

  return (
    <div className="bg-gray-800 dark:bg-gray-900 border-t border-gray-700 px-6 py-3 flex-shrink-0">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        {/* Left: signal + date + strategy */}
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-4">
          <div className="flex items-center gap-2">
            <SignalBadge signal={overlay.signal} />
            <span className="text-xs text-gray-400">{overlay.analysis_date}</span>
          </div>

          {overlay.strategy_name && (
            <span className="text-xs text-gray-300 font-medium">{overlay.strategy_name}</span>
          )}

          {legsText && (
            <span className="text-xs text-gray-400 font-mono">{legsText}</span>
          )}
        </div>

        {/* Right: action buttons */}
        <div className="flex items-center gap-4">
          <button
            disabled
            title="Available in Phase 14"
            className="px-4 py-1.5 rounded text-xs font-semibold bg-gray-600 text-gray-400 cursor-not-allowed opacity-60"
          >
            Confirm Trade
          </button>

          <button
            onClick={onViewAnalysis}
            className="text-sm text-blue-400 hover:text-blue-300 hover:underline transition-colors"
          >
            View Full Analysis
          </button>
        </div>
      </div>
    </div>
  );
}
