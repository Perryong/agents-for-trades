import { useRef, useEffect } from 'react';
import { createChart, CandlestickSeries, HistogramSeries } from 'lightweight-charts';
import type { IChartApi, CandlestickData, HistogramData } from 'lightweight-charts';

interface ChartContainerProps {
  data: CandlestickData[];
  volumeData: HistogramData[];
  dark: boolean;
}

export function ChartContainer({ data, volumeData, dark }: ChartContainerProps) {
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
  }, [data, volumeData, dark]);

  return <div ref={containerRef} className="w-full h-full" />;
}
