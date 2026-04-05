import { useState } from 'react';
import type { ChartOverlay, TradeStatus, LivePriceData, BracketOrderParams } from '../types';

interface TradeSidebarProps {
  overlay: ChartOverlay;
  tradeStatus: TradeStatus | null;
  isSubmitting: boolean;
  onExecute: (params: BracketOrderParams) => Promise<void>;
  onClosePosition: () => void;
  livePrice: LivePriceData | null;
  onViewAnalysis: () => void;
}

function SignalBadge({ signal }: { signal: string }) {
  const upper = signal.toUpperCase();
  if (upper.includes('BUY')) {
    return (
      <span
        className="px-2 py-0.5 rounded text-xs font-bold bg-green-600 text-white"
        aria-label={`Signal: ${signal}`}
      >
        {signal}
      </span>
    );
  }
  if (upper.includes('SELL')) {
    return (
      <span
        className="px-2 py-0.5 rounded text-xs font-bold bg-red-600 text-white"
        aria-label={`Signal: ${signal}`}
      >
        {signal}
      </span>
    );
  }
  return (
    <span
      className="px-2 py-0.5 rounded text-xs font-bold bg-gray-500 text-white"
      aria-label={`Signal: ${signal}`}
    >
      {signal}
    </span>
  );
}

function Spinner() {
  return (
    <span className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin align-middle mr-1" />
  );
}

export function TradeSidebar({
  overlay,
  tradeStatus,
  isSubmitting,
  onExecute,
  onClosePosition,
  livePrice,
  onViewAnalysis,
}: TradeSidebarProps) {
  const [entryPrice, setEntryPrice] = useState<number | null>(overlay.entry_price);
  const [targetPrice, setTargetPrice] = useState<number | null>(overlay.take_profit);
  const [stopLoss, setStopLoss] = useState<number | null>(overlay.stop_loss);
  const [quantity, setQuantity] = useState<number>(100);
  const [tif, setTif] = useState<string>('GTC');
  const [showCloseConfirm, setShowCloseConfirm] = useState(false);
  const [optionsExpanded, setOptionsExpanded] = useState(false);

  const status = tradeStatus?.status ?? 'idle';
  const isFilled = status === 'filled';
  const isClosed = status === 'closed';
  const isFieldsDisabled = isFilled || isClosed;

  // Live price display
  const price = livePrice?.price;
  const open = livePrice?.open;
  const changePct = livePrice?.change_pct;

  let changeDisplay = '--';
  let changeColor = 'text-gray-400';
  if (price != null && open != null && changePct != null) {
    const changeDollar = price - open;
    const sign = changeDollar >= 0 ? '+' : '';
    const pctSign = changePct >= 0 ? '+' : '';
    changeDisplay = `${sign}${changeDollar.toFixed(2)} (${pctSign}${changePct.toFixed(2)}%)`;
    changeColor = changePct >= 0 ? 'text-green-400' : 'text-red-400';
  }

  // Live P&L calculation (for filled/open position)
  const fillPrice = tradeStatus?.fill_price;
  let pnlDisplay = '--';
  let pnlColor = 'text-gray-400';
  if (isFilled && fillPrice != null && price != null) {
    const direction = overlay.signal.toUpperCase();
    const pnlDollar = direction.includes('BUY')
      ? (price - fillPrice) * quantity
      : (fillPrice - price) * quantity;
    const pnlPct = (pnlDollar / (fillPrice * quantity)) * 100;
    const dollarSign = pnlDollar >= 0 ? '+' : '';
    const pctSign = pnlPct >= 0 ? '+' : '';
    pnlDisplay = `${dollarSign}$${pnlDollar.toFixed(2)} (${pctSign}${pnlPct.toFixed(2)}%)`;
    pnlColor = pnlDollar >= 0 ? 'text-green-400' : 'text-red-400';
  }

  const handleExecuteClick = async () => {
    await onExecute({
      ticker: overlay.ticker,
      direction: overlay.signal,
      trade_type: 'equity',
      entry_price: entryPrice,
      target_price: targetPrice!,
      stop_loss: stopLoss!,
      quantity,
      tif,
      strategy_name: overlay.strategy_name ?? undefined,
      analysis_date: overlay.analysis_date,
      confidence_text: overlay.final_trade_decision,
    });
  };

  const isExecuteDisabled = targetPrice == null || stopLoss == null || isSubmitting;

  const inputClasses = `bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-full`;
  const disabledInputClasses = `${inputClasses} opacity-50 cursor-not-allowed`;

  const renderExecuteButton = () => {
    if (isSubmitting || status === 'submitted') {
      return (
        <button
          disabled
          aria-disabled="true"
          className="w-full py-3 text-base font-medium rounded-lg bg-amber-600 text-white flex items-center justify-center cursor-not-allowed"
        >
          <Spinner />
          Order Submitted...
        </button>
      );
    }

    if (isFilled) {
      const priceText = fillPrice != null ? `$${fillPrice.toFixed(2)}` : '...';
      return (
        <div className="space-y-2">
          <button
            disabled
            aria-disabled="true"
            className="w-full py-3 text-base font-medium rounded-lg bg-green-700 text-white cursor-not-allowed"
          >
            Filled @ {priceText}
          </button>

          {showCloseConfirm ? (
            <div className="flex gap-2">
              <button
                onClick={() => setShowCloseConfirm(false)}
                className="bg-gray-700 hover:bg-gray-600 text-gray-200 text-sm font-medium flex-1 py-2.5 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  onClosePosition();
                  setShowCloseConfirm(false);
                }}
                aria-label="Confirm close position"
                className="bg-red-600 hover:bg-red-500 text-white text-sm font-medium flex-1 py-2.5 rounded-lg transition-colors"
              >
                Confirm Close
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowCloseConfirm(true)}
              className="bg-red-700 hover:bg-red-600 text-white text-sm font-medium w-full py-2.5 rounded-lg transition-colors"
            >
              Close Position
            </button>
          )}
        </div>
      );
    }

    if (isClosed) {
      const closeReason = tradeStatus?.close_reason ?? '';
      return (
        <div className="space-y-1">
          <button
            disabled
            aria-disabled="true"
            className="w-full py-3 text-base font-medium rounded-lg bg-green-700 text-white cursor-not-allowed"
          >
            Closed
          </button>
          {closeReason && (
            <p className="text-xs text-center text-gray-400">{closeReason}</p>
          )}
        </div>
      );
    }

    if (status === 'rejected') {
      const reason = tradeStatus?.rejection_reason ?? 'Unknown reason';
      return (
        <div className="space-y-2">
          <div className="w-full py-3 text-base font-medium rounded-lg bg-red-700 text-white text-center">
            Rejected: {reason}
          </div>
          <button
            onClick={handleExecuteClick}
            className="w-full py-2.5 text-sm font-medium rounded-lg bg-gray-700 hover:bg-gray-600 text-white transition-colors"
          >
            Retry Order
          </button>
        </div>
      );
    }

    if (status === 'error') {
      return (
        <div className="space-y-2">
          <div className="w-full py-3 text-base font-medium rounded-lg bg-red-700 text-white text-center">
            Error
          </div>
          <button
            onClick={handleExecuteClick}
            className="w-full py-2.5 text-sm font-medium rounded-lg bg-gray-700 hover:bg-gray-600 text-white transition-colors"
          >
            Retry Order
          </button>
        </div>
      );
    }

    if (status === 'expired') {
      return (
        <button
          disabled
          aria-disabled="true"
          className="w-full py-3 text-base font-medium rounded-lg bg-gray-700 text-white cursor-not-allowed"
        >
          Expired
        </button>
      );
    }

    // idle state
    return (
      <button
        onClick={handleExecuteClick}
        disabled={isExecuteDisabled}
        aria-disabled={isExecuteDisabled}
        className={`w-full py-3 text-base font-medium rounded-lg transition-colors ${
          isExecuteDisabled
            ? 'bg-gray-600 text-gray-400 cursor-not-allowed opacity-60'
            : 'bg-blue-600 hover:bg-blue-500 text-white cursor-pointer'
        }`}
      >
        Execute Paper Trade
      </button>
    );
  };

  const hasOptionsLegs = overlay.options_legs && overlay.options_legs.length > 0;

  return (
    <div className="w-80 flex-shrink-0 border-l border-gray-700 bg-gray-900 flex flex-col h-full">
      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">

        {/* LivePriceHeader */}
        <div className="bg-gray-800 rounded-lg px-4 py-3">
          <div className="flex items-center justify-between">
            <span
              className="text-2xl font-bold text-gray-100"
              aria-live="polite"
            >
              {price != null ? `$${price.toFixed(2)}` : '--'}
            </span>
            <span className={`text-sm ${changeColor}`}>
              {changeDisplay}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-gray-400 font-medium">{overlay.ticker}</span>
            <span className="text-xs text-gray-400">Paper</span>
          </div>
        </div>

        {/* SignalMetadata */}
        <div className="flex flex-wrap items-center gap-2">
          <SignalBadge signal={overlay.signal} />
          <span className="text-xs text-gray-400">{overlay.analysis_date}</span>
          {overlay.strategy_name && (
            <span className="text-xs text-gray-300 font-medium">{overlay.strategy_name}</span>
          )}
        </div>

        {/* Divider */}
        <div className="border-t border-gray-700" />

        {/* OrderForm */}
        <div className="space-y-3">
          {/* Entry Price */}
          <div className="flex flex-col gap-1">
            <label
              htmlFor="entry-price"
              className="text-xs uppercase tracking-wide text-gray-400"
            >
              Entry Price
            </label>
            <input
              id="entry-price"
              type="number"
              step="0.01"
              value={entryPrice ?? ''}
              onChange={e => setEntryPrice(e.target.value === '' ? null : parseFloat(e.target.value))}
              disabled={isFieldsDisabled}
              className={isFieldsDisabled ? disabledInputClasses : inputClasses}
            />
          </div>

          {/* Target Price */}
          <div className="flex flex-col gap-1">
            <label
              htmlFor="target-price"
              className="text-xs uppercase tracking-wide text-gray-400"
            >
              Target Price
            </label>
            <input
              id="target-price"
              type="number"
              step="0.01"
              value={targetPrice ?? ''}
              onChange={e => setTargetPrice(e.target.value === '' ? null : parseFloat(e.target.value))}
              disabled={isFieldsDisabled}
              className={isFieldsDisabled ? disabledInputClasses : inputClasses}
            />
          </div>

          {/* Stop-Loss */}
          <div className="flex flex-col gap-1">
            <label
              htmlFor="stop-loss"
              className="text-xs uppercase tracking-wide text-gray-400"
            >
              Stop-Loss
            </label>
            <input
              id="stop-loss"
              type="number"
              step="0.01"
              value={stopLoss ?? ''}
              onChange={e => setStopLoss(e.target.value === '' ? null : parseFloat(e.target.value))}
              disabled={isFieldsDisabled}
              className={isFieldsDisabled ? disabledInputClasses : inputClasses}
            />
          </div>

          {/* Quantity */}
          <div className="flex flex-col gap-1">
            <label
              htmlFor="quantity"
              className="text-xs uppercase tracking-wide text-gray-400"
            >
              Quantity
            </label>
            <input
              id="quantity"
              type="number"
              step="1"
              min="1"
              value={quantity}
              onChange={e => setQuantity(parseInt(e.target.value, 10) || 1)}
              disabled={isFieldsDisabled}
              className={isFieldsDisabled ? disabledInputClasses : inputClasses}
            />
          </div>

          {/* Time-in-Force */}
          <div className="flex flex-col gap-1">
            <label
              htmlFor="tif"
              className="text-xs uppercase tracking-wide text-gray-400"
            >
              Time-in-Force
            </label>
            <select
              id="tif"
              value={tif}
              onChange={e => setTif(e.target.value)}
              disabled={isFieldsDisabled}
              className={isFieldsDisabled ? disabledInputClasses : inputClasses}
            >
              <option value="GTC">GTC</option>
              <option value="DAY">DAY</option>
            </select>
          </div>
        </div>

        {/* OptionsLegsPanel (conditional) */}
        {hasOptionsLegs && (
          <div className="border-t border-gray-700 pt-3">
            <button
              onClick={() => setOptionsExpanded(prev => !prev)}
              className="flex items-center justify-between w-full text-xs text-gray-300 hover:text-gray-100 transition-colors"
            >
              <span>{overlay.strategy_name ?? 'Options Legs'}</span>
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                className={`transition-transform ${optionsExpanded ? 'rotate-180' : ''}`}
              >
                <path
                  d="M4 6l4 4 4-4"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>

            {optionsExpanded && (
              <div className="mt-2 font-mono text-xs text-gray-300 whitespace-pre-wrap bg-gray-900 rounded p-3 border border-gray-700">
                {overlay.options_legs}
              </div>
            )}
          </div>
        )}

        {/* OpenPositionPanel (only when filled) */}
        {isFilled && (
          <div className="border-t border-gray-700 pt-3 space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs uppercase tracking-wide text-gray-400">Open Position</span>
              <span className="text-sm text-gray-100">
                {fillPrice != null ? `$${fillPrice.toFixed(2)}` : '--'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs uppercase tracking-wide text-gray-400">Live P&amp;L</span>
              <span className={`text-sm ${pnlColor}`}>{pnlDisplay}</span>
            </div>
          </div>
        )}

      </div>

      {/* Fixed bottom: ExecuteButton + View Full Analysis */}
      <div className="flex-shrink-0 px-4 py-4 border-t border-gray-700 space-y-2">
        {renderExecuteButton()}

        <button
          onClick={onViewAnalysis}
          className="w-full text-sm text-blue-400 hover:text-blue-300 hover:underline transition-colors text-center"
        >
          View Full Analysis
        </button>
      </div>
    </div>
  );
}
