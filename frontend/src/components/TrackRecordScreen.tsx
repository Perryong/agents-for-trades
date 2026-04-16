import { useState, useRef, useEffect } from 'react';
import { createChart, LineSeries } from 'lightweight-charts';
import type { IChartApi, Time } from 'lightweight-charts';
import { useDashboardSummary, useDashboardTrades, useEquityCurve, useRollingWinRate } from '../hooks/useDashboard';
import { BiggestSurprise } from './BiggestSurprise';
import { AgentPerformanceTable } from './AgentPerformanceTable';
import type { DashboardTradeItem } from '../types';

interface TrackRecordScreenProps {
  onNavigateChart: () => void;
}

function StatCard({ label, value, colorClass }: { label: string; value: string; colorClass?: string }) {
  return (
    <div className="bg-bg-primary rounded-sm border border-border-subtle p-4 shadow-sm">
      <span className="text-xs text-text-secondary uppercase tracking-wide block mb-1">{label}</span>
      <span className={`text-2xl font-bold ${colorClass ?? 'text-text-primary'}`}>{value}</span>
    </div>
  );
}

function formatPnl(value: number | null): { text: string; colorClass: string } {
  if (value === null) return { text: '--', colorClass: 'text-text-secondary' };
  const sign = value >= 0 ? '+' : '';
  return {
    text: `${sign}${value.toFixed(2)}%`,
    colorClass: value >= 0 ? 'text-accent-green' : 'text-accent-red',
  };
}

export function TrackRecordScreen({ onNavigateChart }: TrackRecordScreenProps) {
  const [tickerFilter, setTickerFilter] = useState<string | undefined>(undefined);
  const [typeFilter, setTypeFilter] = useState<string | undefined>(undefined);

  const { summary, loading: summaryLoading } = useDashboardSummary(tickerFilter, typeFilter);
  const { trades, loading: tradesLoading } = useDashboardTrades(tickerFilter, typeFilter);
  const { curve, loading: curveLoading } = useEquityCurve(tickerFilter, typeFilter);
  const { rolling } = useRollingWinRate(4);

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
        background: { color: '#131313' },
        textColor: '#888888',
      },
      grid: {
        vertLines: { color: '#2e2e2e' },
        horzLines: { color: '#2e2e2e' },
      },
      rightPriceScale: {
        borderColor: '#2e2e2e',
      },
      timeScale: {
        borderColor: '#2e2e2e',
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
  }, [curve]);

  // Empty state
  const isEmptyState = !summaryLoading && summary && summary.total_trades === 0 && !tickerFilter && !typeFilter;

  if (isEmptyState) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-12 text-center">
        <div className="text-text-tertiary mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 mx-auto mb-4 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <p className="text-lg font-medium text-text-secondary mb-2">No paper trades recorded yet</p>
          <p className="text-sm text-text-secondary mb-6">
            Run an analysis and execute a trade from the Chart screen to start building your track record.
          </p>
        </div>
        <button
          onClick={onNavigateChart}
          className="px-4 py-2 bg-accent-blue hover:bg-accent-blue/80 text-white text-sm font-medium rounded-sm transition-colors"
        >
          Go to Chart
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-full">
      {/* Paper Trading Disclaimer Banner — always visible, not dismissable */}
      <div className="bg-accent-amber/10 text-accent-amber border-b border-accent-amber/30 px-4 py-2 text-center text-sm font-medium flex-shrink-0">
        Paper Trading Results -- Not Real Money
      </div>

      <div className="flex-1 p-6 space-y-6">
        {/* Filter Bar */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Active ticker filter */}
          {tickerFilter && (
            <div className="flex items-center gap-2 bg-accent-blue/10 border border-accent-blue/30 rounded-sm px-3 py-1.5">
              <span className="text-sm text-accent-blue font-medium">Showing: {tickerFilter}</span>
              <button
                onClick={() => setTickerFilter(undefined)}
                className="text-accent-blue hover:text-accent-blue/70 text-xs font-medium ml-1"
              >
                Clear filter
              </button>
            </div>
          )}

          {/* Type toggle buttons */}
          <div className="flex rounded-sm overflow-hidden border border-border-subtle">
            {(['All', 'Equity', 'Options'] as const).map(label => {
              const value = label === 'All' ? undefined : label === 'Equity' ? 'equity' : 'option';
              const isActive = typeFilter === value;
              return (
                <button
                  key={label}
                  onClick={() => setTypeFilter(value)}
                  className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-accent-blue text-white'
                      : 'bg-bg-primary text-text-secondary hover:bg-bg-hover'
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Summary Stats Cards */}
        {/* Win Rate Hero + Rolling */}
        <section className="mb-6">
          <div className="flex items-end gap-8 mb-4">
            {summary && (
              <div>
                <p className="text-[11px] text-text-tertiary uppercase tracking-wider mb-1">Win Rate</p>
                <p className={`text-[32px] font-mono font-bold ${
                  summary.win_rate >= 70 ? 'text-accent-green'
                    : summary.win_rate >= 50 ? 'text-accent-amber'
                    : 'text-accent-red'
                }`}>
                  {summary.win_rate.toFixed(1)}%
                </p>
              </div>
            )}
            {rolling && rolling.weeks.length > 0 && (
              <div className="flex items-end gap-2">
                {rolling.weeks.map((w, i) => (
                  <div key={i} className="text-center">
                    <p className={`text-[14px] font-mono font-medium ${
                      w.win_rate >= 70 ? 'text-accent-green'
                        : w.win_rate >= 50 ? 'text-accent-amber'
                        : w.trade_count === 0 ? 'text-text-tertiary'
                        : 'text-accent-red'
                    }`}>
                      {w.trade_count > 0 ? `${w.win_rate.toFixed(0)}%` : '—'}
                    </p>
                    <p className="text-[10px] text-text-tertiary">{w.week_start.slice(5)}</p>
                  </div>
                ))}
                <p className="text-[11px] text-text-tertiary ml-1">4-week rolling</p>
              </div>
            )}
          </div>
          {summary && summary.total_closed < 5 && (
            <p className="text-[13px] text-accent-amber">Need more trades for reliable metrics</p>
          )}
        </section>

        <section>
          <h2 className="text-lg font-semibold text-text-primary mb-3">Performance Summary</h2>
          {summaryLoading ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Array.from({ length: 9 }).map((_, i) => (
                <div key={i} className="bg-bg-primary rounded-sm border border-border-subtle p-4 shadow-sm">
                  <div className="animate-pulse bg-bg-hover rounded h-3 w-16 mb-2" />
                  <div className="animate-pulse bg-bg-hover rounded h-7 w-20" />
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
                  colorClass={summary.win_rate >= 70 ? 'text-accent-green' : summary.win_rate >= 50 ? 'text-accent-amber' : 'text-accent-red'}
                />
                <StatCard
                  label="Expectancy"
                  value={`${summary.expectancy >= 0 ? '+' : ''}${summary.expectancy.toFixed(2)}%`}
                  colorClass={summary.expectancy >= 0 ? 'text-accent-green' : 'text-accent-red'}
                />
                <StatCard
                  label="Avg Winner"
                  value={`+${summary.avg_winner.toFixed(2)}%`}
                  colorClass="text-accent-green"
                />
                <StatCard
                  label="Avg Loser"
                  value={`${summary.avg_loser <= 0 ? '' : '-'}${Math.abs(summary.avg_loser).toFixed(2)}%`}
                  colorClass="text-accent-red"
                />
                <StatCard
                  label="Profit Factor"
                  value={summary.profit_factor.toFixed(2)}
                  colorClass={summary.profit_factor >= 1 ? 'text-accent-green' : 'text-accent-red'}
                />
                <StatCard
                  label="Aggregate P&L"
                  value={`${summary.aggregate_pnl >= 0 ? '+' : ''}${summary.aggregate_pnl.toFixed(2)}%`}
                  colorClass={summary.aggregate_pnl >= 0 ? 'text-accent-green' : 'text-accent-red'}
                />
                <StatCard
                  label="Risk-Reward"
                  value={summary.avg_risk_reward != null ? `${summary.avg_risk_reward.toFixed(2)}:1` : '--'}
                />
                <StatCard
                  label="Avg R-Multiple"
                  value={summary.avg_r_multiple != null
                    ? `${summary.avg_r_multiple >= 0 ? '+' : ''}${summary.avg_r_multiple.toFixed(2)}`
                    : '--'}
                  colorClass={summary.avg_r_multiple != null
                    ? (summary.avg_r_multiple >= 0 ? 'text-accent-green' : 'text-accent-red')
                    : undefined}
                />
              </div>
              {summary.disclaimer && (
                <p className="mt-3 text-sm text-accent-amber">{summary.disclaimer}</p>
              )}
            </>
          ) : (
            <p className="text-sm text-text-secondary">Unable to load summary data.</p>
          )}
        </section>

        {/* Equity Curve Chart */}
        <section>
          <h2 className="text-lg font-semibold text-text-primary mb-3">Equity Curve</h2>
          <div className="bg-bg-primary rounded-sm border border-border-subtle p-2 shadow-sm">
            {curveLoading ? (
              <div className="h-64 flex items-center justify-center">
                <div className="animate-pulse text-sm text-text-tertiary">Loading chart...</div>
              </div>
            ) : curve && curve.points.length > 0 ? (
              <div ref={curveContainerRef} className="h-64 w-full" />
            ) : (
              <div className="h-64 flex items-center justify-center">
                <p className="text-sm text-text-tertiary">No equity curve data yet</p>
              </div>
            )}
          </div>
        </section>

        {/* Biggest Surprise + Agent Performance (Epic 8) */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <BiggestSurprise />
          <AgentPerformanceTable />
        </section>

        {/* Trade History Table */}
        <section>
          <h2 className="text-lg font-semibold text-text-primary mb-3">Trade History</h2>
          {tradesLoading ? (
            <div className="bg-bg-primary rounded-sm border border-border-subtle p-4">
              <div className="space-y-2">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="animate-pulse bg-bg-hover rounded h-8" />
                ))}
              </div>
            </div>
          ) : trades && trades.trades.length > 0 ? (
            <div className="bg-bg-primary rounded-sm border border-border-subtle shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-bg-base">
                    <tr>
                      {['Ticker', 'Direction', 'Type', 'Entry Date', 'Outcome', 'Close Reason', 'P&L %', 'Strategy'].map(col => (
                        <th key={col} className="px-4 py-3 text-left text-xs text-text-secondary uppercase tracking-wide font-medium">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-subtle">
                    {trades.trades.map((trade: DashboardTradeItem) => {
                      const pnl = formatPnl(trade.is_legacy ? null : trade.pnl_pct);
                      return (
                        <tr
                          key={trade.id}
                          className={`hover:bg-bg-hover transition-colors ${trade.is_legacy ? 'opacity-50' : ''}`}
                        >
                          {/* Ticker — clickable for drill-down */}
                          <td className="px-4 py-3">
                            <button
                              onClick={() => setTickerFilter(trade.ticker)}
                              className="text-accent-blue hover:underline cursor-pointer font-medium"
                            >
                              {trade.ticker}
                            </button>
                          </td>
                          {/* Direction badge */}
                          <td className="px-4 py-3">
                            <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                              trade.direction === 'BUY'
                                ? 'bg-accent-green/15 text-accent-green'
                                : 'bg-accent-red/15 text-accent-red'
                            }`}>
                              {trade.direction}
                            </span>
                          </td>
                          {/* Type */}
                          <td className="px-4 py-3 text-text-secondary capitalize">
                            {trade.trade_type}
                          </td>
                          {/* Entry Date */}
                          <td className="px-4 py-3 text-text-secondary">
                            {trade.entry_date ?? '--'}
                          </td>
                          {/* Outcome + Legacy badge */}
                          <td className="px-4 py-3">
                            {trade.is_legacy ? (
                              <span className="inline-flex items-center gap-1">
                                <span className="bg-bg-hover text-text-secondary text-xs px-1.5 py-0.5 rounded">Legacy</span>
                              </span>
                            ) : trade.outcome ? (
                              <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                                trade.outcome === 'WIN'
                                  ? 'bg-accent-green/15 text-accent-green'
                                  : trade.outcome === 'LOSS'
                                  ? 'bg-accent-red/15 text-accent-red'
                                  : 'bg-bg-hover text-text-secondary'
                              }`}>
                                {trade.outcome}
                              </span>
                            ) : (
                              <span className="text-text-tertiary">--</span>
                            )}
                          </td>
                          {/* Close Reason -- D-19 */}
                          <td className="px-4 py-3">
                            {trade.close_reason === 'Target Hit' ? (
                              <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-accent-green/15 text-accent-green">
                                Target Hit
                              </span>
                            ) : trade.close_reason === 'Stop-Loss' ? (
                              <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-accent-red/15 text-accent-red">
                                Stop-Loss
                              </span>
                            ) : trade.close_reason === 'Manual Close' ? (
                              <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-bg-hover text-text-secondary">
                                Manual Close
                              </span>
                            ) : trade.close_reason === 'Expired' ? (
                              <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-bg-hover text-text-tertiary">
                                Expired
                              </span>
                            ) : (
                              <span className="text-text-tertiary">--</span>
                            )}
                          </td>
                          {/* P&L % */}
                          <td className={`px-4 py-3 font-medium ${pnl.colorClass}`}>
                            {pnl.text}
                          </td>
                          {/* Strategy */}
                          <td className="px-4 py-3 text-text-secondary">
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
            <div className="bg-bg-primary rounded-sm border border-border-subtle p-8 text-center">
              <p className="text-sm text-text-tertiary">
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
