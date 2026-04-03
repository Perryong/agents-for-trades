import { useRef, useEffect, useState } from 'react';
import { createChart, LineSeries, LineStyle } from 'lightweight-charts';
import type { IChartApi } from 'lightweight-charts';
import type { CalibrationData } from '../types';

interface CalibrationChartProps {
  calibration: CalibrationData;
}

const BUCKET_LABELS = ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%'];

// Perfect-calibration midpoints: confidence equals win rate at 10, 30, 50, 70, 90
const PERFECT_CALIBRATION = [10, 30, 50, 70, 90];

export function CalibrationChart({ calibration }: CalibrationChartProps) {
  const [expanded, setExpanded] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!expanded) {
      // Destroy chart when collapsed to free resources
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
      return;
    }

    if (!containerRef.current) return;
    if (calibration.message) return; // No chart for insufficient data

    // Clean up any previous chart
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 160,
      layout: {
        background: { color: 'transparent' },
        textColor: '#9ca3af',
      },
      grid: {
        vertLines: { color: '#374151' },
        horzLines: { color: '#374151' },
      },
      rightPriceScale: {
        autoScale: true,
        borderColor: '#374151',
      },
      timeScale: {
        visible: false,
        borderColor: '#374151',
      },
    });

    chartRef.current = chart;

    // Actual win rate line series (blue)
    const actualSeries = chart.addSeries(LineSeries, {
      color: '#3b82f6',
      lineWidth: 2,
      pointMarkersVisible: true,
      pointMarkersRadius: 4,
    });

    const actualData = calibration.buckets.map((b, i) => ({
      time: ((i + 1) * 86400) as unknown as import('lightweight-charts').Time,
      value: b.actual_win_rate,
    }));
    actualSeries.setData(actualData);

    // Perfect calibration diagonal reference line (gray dashed)
    const perfectSeries = chart.addSeries(LineSeries, {
      color: '#6b7280',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      pointMarkersVisible: false,
    });

    const perfectData = PERFECT_CALIBRATION.map((v, i) => ({
      time: ((i + 1) * 86400) as unknown as import('lightweight-charts').Time,
      value: v,
    }));
    perfectSeries.setData(perfectData);

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
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [calibration, expanded]);

  return (
    <div className="mt-2">
      {/* Collapsible toggle */}
      <button
        onClick={() => setExpanded(prev => !prev)}
        className="text-xs text-blue-400 hover:text-blue-300 cursor-pointer transition-colors"
      >
        {expanded ? 'Hide Calibration' : 'Show Calibration'}
      </button>

      {expanded && (
        <div className="mt-2 bg-gray-800/50 rounded p-2">
          {calibration.message ? (
            // Insufficient data message per D-11
            <p className="text-xs text-gray-400 py-2 text-center">
              {calibration.message}
            </p>
          ) : (
            <>
              {/* Chart container */}
              <div ref={containerRef} style={{ height: 160 }} />

              {/* Bucket labels below chart */}
              <div className="flex justify-between mt-1 px-1">
                {BUCKET_LABELS.map(label => (
                  <span key={label} className="text-xs text-gray-500">
                    {label}
                  </span>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
