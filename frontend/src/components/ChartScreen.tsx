import { useState, useEffect, useRef } from 'react';
import type { ChartTimeframe, BracketOrderParams } from '../types';
import { TIMEFRAME_CONFIG } from '../types';
import { useChartData } from '../hooks/useChartData';
import { useOverlay } from '../hooks/useOverlay';
import { useTrade } from '../hooks/useTrade';
import { useTradeStatus } from '../hooks/useTradeStatus';
import { useTradeMarker } from '../hooks/useTradeMarker';
import { useLivePrice } from '../hooks/useLivePrice';
import { ChartContainer } from './ChartContainer';
import { ChartTickerPicker } from './ChartTickerPicker';
import { TradeSidebar } from './TradeSidebar';

const TIMEFRAMES: ChartTimeframe[] = ['1D', '1M', '3M', '6M', '1Y'];

interface ChartScreenProps {
  initialTicker?: string;
  onViewAnalysis?: () => void;
}

export function ChartScreen({ initialTicker, onViewAnalysis }: ChartScreenProps) {
  const [ticker, setTicker] = useState(initialTicker ?? '');
  // Default to 6M per D-25 passive mode
  const [timeframe, setTimeframe] = useState<ChartTimeframe>('6M');
  const hasSetSmartDefault = useRef(false);

  // Trade execution state
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
  const { overlay: analysisOverlay } = useOverlay(ticker);

  // Position-based overlay fallback (Epic 8.4): if no analysis overlay, check for open position
  const [positionOverlay, setPositionOverlay] = useState<typeof analysisOverlay>(null);
  useEffect(() => {
    if (analysisOverlay || !ticker) { setPositionOverlay(null); return; }
    fetch('/api/positions')
      .then(r => r.ok ? r.json() : [])
      .then((positions: Array<{ ticker: string; direction: string; fill_price: number | null; entry_price: number | null; stop_loss: number | null; target_price: number | null; strategy_name: string | null }>) => {
        const pos = positions.find(p => p.ticker.toUpperCase() === ticker.toUpperCase());
        if (pos) {
          setPositionOverlay({
            ticker: pos.ticker,
            analysis_date: new Date().toISOString().slice(0, 10),
            signal: pos.direction,
            entry_price: pos.fill_price ?? pos.entry_price ?? null,
            take_profit: pos.target_price ?? null,
            stop_loss: pos.stop_loss ?? null,
            expiry_date: null,
            strategy_name: pos.strategy_name ?? null,
            options_legs: '',
            final_trade_decision: '',
          });
        } else {
          setPositionOverlay(null);
        }
      })
      .catch(() => setPositionOverlay(null));
  }, [ticker, analysisOverlay]);

  const overlay = analysisOverlay ?? positionOverlay;
  const { submitBracketTrade, isSubmitting } = useTrade();
  const tradeStatus = useTradeStatus(ticker, currentOrderId);
  const livePrice = useLivePrice(overlay ? ticker : null);

  // Derive trade fill/exit markers from tradeStatus for chart rendering
  const tradeMarker = useTradeMarker(
    tradeStatus,
    overlay?.signal ?? 'BUY',
  );

  const isActiveMode = overlay !== null;

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

  const handleBracketTrade = async (params: BracketOrderParams) => {
    try {
      const response = await submitBracketTrade(params);
      setCurrentOrderId(response.order_id);
    } catch (err) {
      console.error('Bracket trade submission failed:', err instanceof Error ? err.message : String(err));
    }
  };

  const handleClosePosition = async () => {
    if (!ticker) return;
    try {
      await fetch(`/api/trades/${encodeURIComponent(ticker)}/close`, { method: 'POST' });
      // Polling in useTradeStatus will pick up the status change
    } catch (err) {
      console.error('Close position failed:', err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="flex flex-row h-full">
      {/* Left: chart area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar: ticker picker + timeframe presets */}
        <div className="flex items-start justify-between gap-4 px-4 py-3 border-b border-border-subtle bg-bg-primary flex-shrink-0">
          <ChartTickerPicker value={ticker} onChange={setTicker} />

          <div className="flex items-center gap-1 flex-shrink-0">
            {TIMEFRAMES.map(tf => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-3 py-1.5 text-sm font-medium rounded-sm transition-colors ${
                  timeframe === tf
                    ? 'bg-accent-blue text-white'
                    : 'bg-bg-primary text-text-secondary hover:bg-bg-hover'
                }`}
              >
                {TIMEFRAME_CONFIG[tf].label}
              </button>
            ))}
          </div>
        </div>

        {/* Chart area */}
        <div className="flex-1 relative overflow-hidden bg-bg-base">
          {!ticker ? (
            <div className="absolute inset-0 flex items-center justify-center text-text-tertiary text-sm">
              Enter a ticker symbol to view chart
            </div>
          ) : loading ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="flex flex-col items-center gap-3">
                <div className="w-8 h-8 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
                <span className="text-sm text-text-secondary">Loading chart data...</span>
              </div>
            </div>
          ) : error ? (
            <div className="absolute inset-0 flex items-center justify-center px-6">
              <div className="max-w-md text-center">
                <p className="text-accent-red text-sm font-medium mb-1">Failed to load chart data</p>
                <p className="text-text-secondary text-xs">{error}</p>
              </div>
            </div>
          ) : bars && volumeData ? (
            <ChartContainer data={bars} volumeData={volumeData} overlay={overlay} tradeMarker={tradeMarker} />
          ) : null}
        </div>
      </div>

      {/* Right: sidebar — only in active mode */}
      {isActiveMode && overlay && (
        <TradeSidebar
          overlay={overlay}
          tradeStatus={tradeStatus}
          isSubmitting={isSubmitting}
          onExecute={handleBracketTrade}
          onClosePosition={handleClosePosition}
          livePrice={livePrice}
          onViewAnalysis={onViewAnalysis ?? (() => {})}
        />
      )}
    </div>
  );
}
