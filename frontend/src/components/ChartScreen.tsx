import { useState } from 'react';
import type { ChartTimeframe } from '../types';
import { TIMEFRAME_CONFIG } from '../types';
import { useChartData } from '../hooks/useChartData';
import { ChartContainer } from './ChartContainer';
import { ChartTickerPicker } from './ChartTickerPicker';

const TIMEFRAMES: ChartTimeframe[] = ['1D', '1M', '3M', '6M', '1Y'];

interface ChartScreenProps {
  dark: boolean;
}

export function ChartScreen({ dark }: ChartScreenProps) {
  const [ticker, setTicker] = useState('');
  // Default to 6M per D-25 passive mode
  const [timeframe, setTimeframe] = useState<ChartTimeframe>('6M');

  const { bars, volumeData, loading, error } = useChartData(ticker, timeframe);

  return (
    <div className="flex flex-col h-full">
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
          <ChartContainer data={bars} volumeData={volumeData} dark={dark} />
        ) : null}
      </div>
    </div>
  );
}
