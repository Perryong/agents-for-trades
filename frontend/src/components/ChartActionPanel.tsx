import type { ChartOverlay, TradeStatus } from '../types';

interface ChartActionPanelProps {
  overlay: ChartOverlay;
  onViewAnalysis: () => void;
  ticker: string;
  onExecute: () => void;
  tradeStatus: TradeStatus | null;
  canExecuteOptions: boolean;
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

function Spinner() {
  return (
    <span className="inline-block w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin align-middle mr-1" />
  );
}

export function ChartActionPanel({
  overlay,
  onViewAnalysis,
  onExecute,
  tradeStatus,
  canExecuteOptions,
}: ChartActionPanelProps) {
  const legsText = overlay.options_legs
    ? overlay.options_legs.length > 60
      ? overlay.options_legs.slice(0, 60) + '...'
      : overlay.options_legs
    : null;

  const isHoldSignal = overlay.signal.toUpperCase() === 'HOLD';
  const isOptionsSignal = overlay.options_legs && overlay.options_legs.length > 0;

  // Determine button disabled state and tooltip
  let executeDisabled = false;
  let executeTitle = 'Execute paper trade via Alpaca';

  if (isHoldSignal) {
    executeDisabled = true;
    executeTitle = 'No trade signal';
  } else if (isOptionsSignal && !canExecuteOptions) {
    executeDisabled = true;
    executeTitle = 'Options contract could not be determined from agent output';
  }

  const status = tradeStatus?.status ?? 'idle';

  const renderExecuteButton = () => {
    if (status === 'submitted') {
      return (
        <span className="px-4 py-1.5 rounded text-xs font-semibold bg-amber-600 text-white flex items-center gap-1">
          <Spinner />
          Submitted...
        </span>
      );
    }

    if (status === 'filled') {
      const fillPrice = tradeStatus?.fill_price;
      const priceText = fillPrice != null ? `$${fillPrice.toFixed(2)}` : '...';
      return (
        <span className="px-4 py-1.5 rounded text-xs font-semibold bg-green-700 text-white">
          Filled @ {priceText}
        </span>
      );
    }

    if (status === 'rejected') {
      const reason = tradeStatus?.rejection_reason ?? 'Unknown reason';
      return (
        <div className="flex items-center gap-2">
          <span className="px-2 py-1 rounded text-xs font-semibold bg-red-700 text-white">
            Rejected: {reason}
          </span>
          <button
            onClick={onExecute}
            className="px-3 py-1 rounded text-xs font-semibold bg-gray-600 hover:bg-gray-500 text-white transition-colors"
          >
            Retry
          </button>
        </div>
      );
    }

    if (status === 'error') {
      return (
        <div className="flex items-center gap-2">
          <span className="px-2 py-1 rounded text-xs font-semibold bg-red-700 text-white">
            Error
          </span>
          <button
            onClick={onExecute}
            className="px-3 py-1 rounded text-xs font-semibold bg-gray-600 hover:bg-gray-500 text-white transition-colors"
          >
            Retry
          </button>
        </div>
      );
    }

    // idle state
    return (
      <button
        onClick={onExecute}
        disabled={executeDisabled}
        title={executeTitle}
        className={`px-4 py-1.5 rounded text-xs font-semibold transition-colors ${
          executeDisabled
            ? 'bg-gray-600 text-gray-400 cursor-not-allowed opacity-60'
            : 'bg-green-700 hover:bg-green-600 text-white cursor-pointer'
        }`}
      >
        Execute Paper Trade
      </button>
    );
  };

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
          {renderExecuteButton()}

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
