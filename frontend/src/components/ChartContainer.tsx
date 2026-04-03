import { useRef, useEffect } from 'react';
import { createChart, CandlestickSeries, HistogramSeries, createSeriesMarkers, LineStyle } from 'lightweight-charts';
import type { IChartApi, CandlestickData, HistogramData, Time } from 'lightweight-charts';
import type { ChartOverlay } from '../types';

interface ChartContainerProps {
  data: CandlestickData[];
  volumeData: HistogramData[];
  dark: boolean;
  overlay?: ChartOverlay | null;
}

export function ChartContainer({ data, volumeData, dark, overlay }: ChartContainerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Remove previous chart instance to prevent memory leak
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight || 400;

    const chart = createChart(containerRef.current, {
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

    chartRef.current = chart;

    // Add candlestick series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    });
    candleSeries.setData(data);

    // Add volume histogram series
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: '',
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.7, bottom: 0 },
    });
    volumeSeries.setData(volumeData);

    // --- Overlay annotations (active mode per D-16) ---
    if (overlay) {
      // 1. Take-profit horizontal dashed line (green)
      if (overlay.take_profit !== null) {
        candleSeries.createPriceLine({
          price: overlay.take_profit,
          color: '#22c55e',
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: 'TP',
        });
      }

      // 2. Stop-loss horizontal dashed line (red)
      if (overlay.stop_loss !== null) {
        candleSeries.createPriceLine({
          price: overlay.stop_loss,
          color: '#ef4444',
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: 'SL',
        });
      }

      // 3. Entry marker dot (blue circle at analysis date)
      // Only render if entry_price is known — don't fake a price
      if (overlay.entry_price !== null) {
        createSeriesMarkers(candleSeries, [
          {
            time: overlay.analysis_date as Time,
            position: 'belowBar',
            color: '#3b82f6',
            shape: 'circle',
            text: overlay.strategy_name ?? overlay.signal,
            size: 2,
          },
        ]);
      }

      // 4. Expiry marker (amber arrowDown above bar at expiry date)
      if (overlay.expiry_date !== null) {
        createSeriesMarkers(candleSeries, [
          {
            time: overlay.expiry_date as Time,
            position: 'aboveBar',
            color: '#f59e0b',
            shape: 'arrowDown',
            text: 'Expiry',
            size: 1,
          },
        ]);
      }
    }

    chart.timeScale().fitContent();

    // Resize observer
    function handleResize() {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
      }
    }
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, volumeData, dark, overlay]);

  return <div ref={containerRef} className="w-full h-full" />;
}
