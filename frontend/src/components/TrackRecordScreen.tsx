import { useState, useRef, useEffect } from 'react';
import { createChart, LineSeries } from 'lightweight-charts';
import type { IChartApi, Time } from 'lightweight-charts';
import { useDashboardSummary, useDashboardTrades, useEquityCurve } from '../hooks/useDashboard';
import type { DashboardTradeItem } from '../types';

interface TrackRecordScreenProps {
  dark: boolean;
  onNavigateChart: () => void;
}

function StatCard({ label, value, colorClass }: { label: string; value: string; colorClass?: string }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 shadow-sm">
      <span className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide block mb-1">{label}</span>
      <span className={`text-2xl font-bold ${colorClass ?? 'text-gray-900 dark:text-gray-100'}`}>{value}</span>
    </div>
  );
}

function formatPnl(value: number | null): { text: string; colorClass: string } {
  if (value === null) return { text: '--', colorClass: 'text-gray-500 dark:text-gray-400' };
  const sign = value >= 0 ? '+' : '';
  return {
    text: `${sign}${value.toFixed(2)}%`,
    colorClass: value >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400',
  };
}

export function TrackRecordScreen({ dark, onNavigateChart }: TrackRecordScreenProps) {
  const [tickerFilter, setTickerFilter] = useState<string | undefined>(undefined);
  const [typeFilter, setTypeFilter] = useState<string | undefined>(undefined);

  const { summary, loading: summaryLoading } = useDashboardSummary(tickerFilter, typeFilter);
  const { trades, loading: tradesLoading } = useDashboardTrades(tickerFilter, typeFilter);
  const { curve, loading: curveLoading } = useEquityCurve(tickerFilter, typeFilter);

  // Equity curve chart refs
  const curveContainerRef = useRef<HTMLDivElement>(null);
  const curveChartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!curveContainerRef.current) return;

    // Clean up previous chart
    if (curveChartRef.current) {
      curveChartRef.current.remove();
      curveChartRef.current = null;
    }

    // Don't render chart if no data
    if (!curve || curve.points.length === 0) return;

    const width = curveContainerRef.current.clientWidth;
    const height = curveContainerRef.current.clientHeight || 256;

    const chart = createChart(curveContainerRef.current, {
      width,
      height,
      layout: {
        background: { color: 'transparent' },
        textColor: dark ? '#9ca3af' : '#4b5563',
      },
      grid: {
        vertLines: { color: dark ? '#374151' : '#e5e7eb' },
        horzLines: { color: dark ? '#374151' : '#e5e7eb' },
      },
      rightPriceScale: {
        borderColor: dark ? '#374151' : '#e5e7eb',
      },
      timeScale: {
        borderColor: dark ? '#374151' : '#e5e7eb',
      },
    });

    curveChartRef.current = chart;

    const lineSeries = chart.addSeries(LineSeries, {
      color: '#22c55e',
      lineWidth: 2,
    });

    lineSeries.setData(
      curve.points.map(p => ({ time: p.time as Time, value: p.value }))
    );

    // Add zero baseline price line
    lineSeries.createPriceLine({
      price: 0,
      color: '#6b7280',
      lineWidth: 1,
      lineStyle: 2, // Dashed
      axisLabelVisible: true,
      title: '0',
    });

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (curveContainerRef.current && curveChartRef.current) {
        curveChartRef.current.applyOptions({ width: curveContainerRef.current.clientWidth });
      }
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(curveContainerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
    };
  }, [curve, dark]);

  // Empty state
  const isEmptyState = !summaryLoading && summary && summary.total_trades === 0 && !tickerFilter && !typeFilter;

  if (isEmptyState) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-12 text-center">
        <div className="text-gray-400 dark:text-gray-500 mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 mx-auto mb-4 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <p className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">No paper trades recorded yet</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
            Run an analysis and execute a trade from the Chart screen to start building your track record.
          </p>
        </div>
        <button
          onClick={onNavigateChart}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          Go to Chart
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-full">
      {/* Paper Trading Disclaimer Banner — always visible, not dismissable */}
      <div className="bg-yellow-50 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-200 border-b border-yellow-200 dark:border-yellow-800 px-4 py-2 text-center text-sm font-medium flex-shrink-0">
        Paper Trading Results -- Not Real Money
      </div>

      <div className="flex-1 p-6 space-y-6">
        {/* Filter Bar */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Active ticker filter */}
          {tickerFilter && (
            <div className="flex items-center gap-2 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 rounded-lg px-3 py-1.5">
              <span className="text-sm text-blue-700 dark:text-blue-300 font-medium">Showing: {tickerFilter}</span>
              <button
                onClick={() => setTickerFilter(undefined)}
                className="text-blue-500 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-200 text-xs font-medium ml-1"
              >
                Clear filter
              </button>
            </div>
          )}

          {/* Type toggle buttons */}
          <div className="flex rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700">
            {(['All', 'Equity', 'Options'] as const).map(label => {
              const value = label === 'All' ? undefined : label === 'Equity' ? 'equity' : 'option';
              const isActive = typeFilter === value;
              return (
                <button
                  key={label}
                  onClick={() => setTypeFilter(value)}
                  className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Summary Stats Cards */}
        <section>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">Performance Summary</h2>
          {summaryLoading ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Array.from({ length: 7 }).map((_, i) => (
                <div key={i} className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 shadow-sm">
                  <div className="animate-pulse bg-gray-200 dark:bg-gray-700 rounded h-3 w-16 mb-2" />
                  <div className="animate-pulse bg-gray-200 dark:bg-gray-700 rounded h-7 w-20" />
                </div>
              ))}
            </div>
          ) : summary ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard label="Total Trades" value={String(summary.total_trades)} />
                <StatCard
                  label="Win Rate"
                  value={`${summary.win_rate.toFixed(1)}%`}
                  colorClass={summary.win_rate >= 50 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}
                />
                <StatCard
                  label="Expectancy"
                  value={`${summary.expectancy >= 0 ? '+' : ''}${summary.expectancy.toFixed(2)}%`}
                  colorClass={summary.expectancy >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}
                />
                <StatCard
                  label="Avg Winner"
                  value={`+${summary.avg_winner.toFixed(2)}%`}
                  colorClass="text-green-600 dark:text-green-400"
                />
                <StatCard
                  label="Avg Loser"
                  value={`${summary.avg_loser <= 0 ? '' : '-'}${Math.abs(summary.avg_loser).toFixed(2)}%`}
                  colorClass="text-red-600 dark:text-red-400"
                />
                <StatCard
                  label="Profit Factor"
                  value={summary.profit_factor.toFixed(2)}
                  colorClass={summary.profit_factor >= 1 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}
                />
                <StatCard
                  label="Aggregate P&L"
                  value={`${summary.aggregate_pnl >= 0 ? '+' : ''}${summary.aggregate_pnl.toFixed(2)}%`}
                  colorClass={summary.aggregate_pnl >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}
                />
              </div>
              {summary.disclaimer && (
                <p className="mt-3 text-sm text-yellow-600 dark:text-yellow-400">{summary.disclaimer}</p>
              )}
            </>
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400">Unable to load summary data.</p>
          )}
        </section>

        {/* Equity Curve Chart */}
        <section>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">Equity Curve</h2>
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-2 shadow-sm">
            {curveLoading ? (
              <div className="h-64 flex items-center justify-center">
                <div className="animate-pulse text-sm text-gray-400 dark:text-gray-500">Loading chart...</div>
              </div>
            ) : curve && curve.points.length > 0 ? (
              <div ref={curveContainerRef} className="h-64 w-full" />
            ) : (
              <div className="h-64 flex items-center justify-center">
                <p className="text-sm text-gray-400 dark:text-gray-500">No equity curve data yet</p>
              </div>
            )}
          </div>
        </section>

        {/* Trade History Table */}
        <section>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">Trade History</h2>
          {tradesLoading ? (
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <div className="space-y-2">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="animate-pulse bg-gray-200 dark:bg-gray-700 rounded h-8" />
                ))}
              </div>
            </div>
          ) : trades && trades.trades.length > 0 ? (
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 dark:bg-gray-700">
                    <tr>
                      {['Ticker', 'Direction', 'Type', 'Entry Date', 'Outcome', 'P&L %', 'Strategy'].map(col => (
                        <th key={col} className="px-4 py-3 text-left text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide font-medium">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                    {trades.trades.map((trade: DashboardTradeItem) => {
                      const pnl = formatPnl(trade.is_legacy ? null : trade.pnl_pct);
                      return (
                        <tr
                          key={trade.id}
                          className={`hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${trade.is_legacy ? 'opacity-50' : ''}`}
                        >
                          {/* Ticker — clickable for drill-down */}
                          <td className="px-4 py-3">
                            <button
                              onClick={() => setTickerFilter(trade.ticker)}
                              className="text-blue-600 dark:text-blue-400 hover:underline cursor-pointer font-medium"
                            >
                              {trade.ticker}
                            </button>
                          </td>
                          {/* Direction badge */}
                          <td className="px-4 py-3">
                            <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                              trade.direction === 'BUY'
                                ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400'
                                : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400'
                            }`}>
                              {trade.direction}
                            </span>
                          </td>
                          {/* Type */}
                          <td className="px-4 py-3 text-gray-600 dark:text-gray-300 capitalize">
                            {trade.trade_type}
                          </td>
                          {/* Entry Date */}
                          <td className="px-4 py-3 text-gray-600 dark:text-gray-300">
                            {trade.entry_date ?? '--'}
                          </td>
                          {/* Outcome + Legacy badge */}
                          <td className="px-4 py-3">
                            {trade.is_legacy ? (
                              <span className="inline-flex items-center gap-1">
                                <span className="bg-gray-200 dark:bg-gray-600 text-gray-500 dark:text-gray-400 text-xs px-1.5 py-0.5 rounded">Legacy</span>
                              </span>
                            ) : trade.outcome ? (
                              <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                                trade.outcome === 'WIN'
                                  ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400'
                                  : trade.outcome === 'LOSS'
                                  ? 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400'
                                  : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
                              }`}>
                                {trade.outcome}
                              </span>
                            ) : (
                              <span className="text-gray-400 dark:text-gray-500">--</span>
                            )}
                          </td>
                          {/* P&L % */}
                          <td className={`px-4 py-3 font-medium ${pnl.colorClass}`}>
                            {pnl.text}
                          </td>
                          {/* Strategy */}
                          <td className="px-4 py-3 text-gray-600 dark:text-gray-300">
                            {trade.strategy_name ?? '--'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-8 text-center">
              <p className="text-sm text-gray-400 dark:text-gray-500">
                {tickerFilter
                  ? `No trades found for ${tickerFilter}`
                  : 'No trade history available'}
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
