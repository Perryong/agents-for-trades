import { useState, useEffect, useRef } from 'react';
import type { ChartTimeframe } from '../types';
import { TIMEFRAME_CONFIG } from '../types';
import { useChartData } from '../hooks/useChartData';
import { useOverlay } from '../hooks/useOverlay';
import { useTrade } from '../hooks/useTrade';
import { useTradeStatus } from '../hooks/useTradeStatus';
import { useTradeMarker } from '../hooks/useTradeMarker';
import { useScoreSummary, useCalibration } from '../hooks/useScores';
import { ChartContainer } from './ChartContainer';
import { ChartTickerPicker } from './ChartTickerPicker';
import { ChartActionPanel } from './ChartActionPanel';
import { TradeConfirmModal } from './TradeConfirmModal';

const TIMEFRAMES: ChartTimeframe[] = ['1D', '1M', '3M', '6M', '1Y'];

interface ChartScreenProps {
  dark: boolean;
  initialTicker?: string;
  onViewAnalysis?: () => void;
}

export function ChartScreen({ dark, initialTicker, onViewAnalysis }: ChartScreenProps) {
  const [ticker, setTicker] = useState(initialTicker ?? '');
  // Default to 6M per D-25 passive mode
  const [timeframe, setTimeframe] = useState<ChartTimeframe>('6M');
  const hasSetSmartDefault = useRef(false);

  // Trade execution state
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [currentOrderId, setCurrentOrderId] = useState<string | null>(null);

  // Sync ticker when initialTicker prop changes (e.g. auto-navigate from Analysis)
  useEffect(() => {
    if (initialTicker && initialTicker !== ticker) {
      setTicker(initialTicker);
      // Reset smart default flag so it recalculates for the new ticker
      hasSetSmartDefault.current = false;
    }
  }, [initialTicker]); // eslint-disable-line react-hooks/exhaustive-deps

  const { bars, volumeData, loading, error } = useChartData(ticker, timeframe);
  const { overlay } = useOverlay(ticker);
  const { submitTrade, isSubmitting } = useTrade();
  const tradeStatus = useTradeStatus(ticker, currentOrderId);
  const { summary: scoreSummary } = useScoreSummary();
  const { calibration } = useCalibration();

  // Auto-close check: fires once on mount per D-09 (fire-and-forget)
  useEffect(() => {
    fetch('/api/trades/check-autoclose', { method: 'POST' }).catch(() => {});
  }, []);

  // Derive trade fill/exit markers from tradeStatus for chart rendering
  const tradeMarker = useTradeMarker(
    tradeStatus,
    overlay?.signal ?? 'BUY',
  );

  const isActiveMode = overlay !== null;

  // Determine if options execution is possible: check for "LEG 1:" pattern in options_legs
  const canExecuteOptions = overlay
    ? /LEG\s+1:/i.test(overlay.options_legs)
    : false;

  // Smart default timeframe in active mode (per D-25)
  useEffect(() => {
    if (overlay && !hasSetSmartDefault.current) {
      hasSetSmartDefault.current = true;
      const entryDate = new Date(overlay.analysis_date);
      const now = new Date();
      const daysDiff = Math.floor((now.getTime() - entryDate.getTime()) / (1000 * 60 * 60 * 24));
      if (daysDiff < 14) {
        setTimeframe('1M');
      } else if (daysDiff < 42) {
        setTimeframe('3M');
      } else {
        setTimeframe('6M');
      }
    }
  }, [overlay]);

  const handleExecute = () => {
    setShowConfirmModal(true);
  };

  const handleConfirmTrade = async () => {
    if (!overlay) return;
    setShowConfirmModal(false);

    try {
      const response = await submitTrade({
        ticker: overlay.ticker,
        direction: overlay.signal,
        trade_type: 'equity',
        strategy_name: overlay.strategy_name ?? undefined,
        analysis_date: overlay.analysis_date,
        confidence_text: overlay.final_trade_decision ?? undefined,
      });
      setCurrentOrderId(response.order_id);
    } catch (err) {
      console.error('Trade submission failed:', err instanceof Error ? err.message : String(err));
    }
  };

  const handleCancelModal = () => {
    setShowConfirmModal(false);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Trade confirmation modal */}
      {overlay && (
        <TradeConfirmModal
          open={showConfirmModal}
          onConfirm={handleConfirmTrade}
          onCancel={handleCancelModal}
          ticker={overlay.ticker}
          direction={overlay.signal}
          quantity={100}
          orderType="Market"
          tradeType="equity"
          strategyName={overlay.strategy_name ?? undefined}
        />
      )}

      {/* Top bar: ticker picker + timeframe presets */}
      <div className="flex items-start justify-between gap-4 px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 flex-shrink-0">
        <ChartTickerPicker value={ticker} onChange={setTicker} />

        <div className="flex items-center gap-1 flex-shrink-0">
          {TIMEFRAMES.map(tf => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                timeframe === tf
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-300 dark:hover:bg-gray-600'
              }`}
            >
              {TIMEFRAME_CONFIG[tf].label}
            </button>
          ))}
        </div>
      </div>

      {/* Chart area */}
      <div className="flex-1 relative overflow-hidden bg-gray-50 dark:bg-gray-900">
        {!ticker ? (
          <div className="absolute inset-0 flex items-center justify-center text-gray-400 dark:text-gray-500 text-sm">
            Enter a ticker symbol to view chart
          </div>
        ) : loading ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-gray-500 dark:text-gray-400">Loading chart data...</span>
            </div>
          </div>
        ) : error ? (
          <div className="absolute inset-0 flex items-center justify-center px-6">
            <div className="max-w-md text-center">
              <p className="text-red-600 dark:text-red-400 text-sm font-medium mb-1">Failed to load chart data</p>
              <p className="text-gray-500 dark:text-gray-400 text-xs">{error}</p>
            </div>
          </div>
        ) : bars && volumeData ? (
          <ChartContainer data={bars} volumeData={volumeData} dark={dark} overlay={overlay} tradeMarker={tradeMarker} />
        ) : null}
      </div>

      {/* Action panel — pinned bottom, only in active mode */}
      {isActiveMode && overlay && (
        <ChartActionPanel
          overlay={overlay}
          onViewAnalysis={onViewAnalysis ?? (() => {})}
          ticker={overlay.ticker}
          onExecute={handleExecute}
          tradeStatus={isSubmitting ? { ...tradeStatus, status: 'submitted' } : tradeStatus}
          canExecuteOptions={canExecuteOptions}
          scoreSummary={scoreSummary}
          calibration={calibration}
        />
      )}
    </div>
  );
}
