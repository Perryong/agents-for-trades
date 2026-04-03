interface TradeConfirmModalProps {
  open: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  ticker: string;
  direction: string;
  quantity: number;
  orderType: string;
  tradeType: string;
  strategyName?: string;
}

export function TradeConfirmModal({
  open,
  onConfirm,
  onCancel,
  ticker,
  direction,
  quantity,
  orderType,
  tradeType,
  strategyName,
}: TradeConfirmModalProps) {
  if (!open) return null;

  const isBuy = direction.toUpperCase().includes('BUY');
  const directionClass = isBuy
    ? 'bg-green-600 text-white'
    : 'bg-red-600 text-white';
  const confirmClass = isBuy
    ? 'bg-green-600 hover:bg-green-500 text-white'
    : 'bg-red-600 hover:bg-red-500 text-white';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      role="dialog"
      aria-modal="true"
      aria-label="Confirm trade"
    >
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-sm mx-4 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Confirm Paper Trade
        </h2>

        <div className="space-y-3 mb-6">
          {/* Ticker */}
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500 dark:text-gray-400">Ticker</span>
            <span className="text-sm font-semibold text-gray-900 dark:text-white">{ticker}</span>
          </div>

          {/* Direction */}
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500 dark:text-gray-400">Direction</span>
            <span className={`px-2 py-0.5 rounded text-xs font-bold ${directionClass}`}>
              {direction.toUpperCase()}
            </span>
          </div>

          {/* Quantity */}
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500 dark:text-gray-400">Quantity</span>
            <span className="text-sm font-semibold text-gray-900 dark:text-white">{quantity}</span>
          </div>

          {/* Order Type */}
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500 dark:text-gray-400">Order Type</span>
            <span className="text-sm font-semibold text-gray-900 dark:text-white">{orderType}</span>
          </div>

          {/* Trade Type */}
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500 dark:text-gray-400">Trade Type</span>
            <span className="text-sm font-semibold text-gray-900 dark:text-white capitalize">{tradeType}</span>
          </div>

          {/* Strategy Name (optional) */}
          {strategyName && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-500 dark:text-gray-400">Strategy</span>
              <span className="text-sm font-semibold text-gray-900 dark:text-white">{strategyName}</span>
            </div>
          )}
        </div>

        <p className="text-xs text-gray-400 dark:text-gray-500 mb-5">
          This is a paper trade on your Alpaca paper trading account. No real funds will be used.
        </p>

        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 px-4 py-2 rounded text-sm font-medium bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className={`flex-1 px-4 py-2 rounded text-sm font-medium transition-colors ${confirmClass}`}
          >
            Confirm Trade
          </button>
        </div>
      </div>
    </div>
  );
}
