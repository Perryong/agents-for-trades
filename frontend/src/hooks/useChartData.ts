import { useState, useEffect, useRef } from 'react';
import type { CandlestickData, HistogramData, Time } from 'lightweight-charts';
import type { ChartTimeframe } from '../types';
import { TIMEFRAME_CONFIG } from '../types';

interface ChartDataCache {
  candles: CandlestickData[];
  volumes: HistogramData[];
}

interface UseChartDataResult {
  bars: CandlestickData[] | null;
  volumeData: HistogramData[] | null;
  loading: boolean;
  error: string | null;
}

function getStartDate(timeframe: ChartTimeframe): string {
  const config = TIMEFRAME_CONFIG[timeframe];
  const now = new Date();
  if (config.daysBack === 0) {
    // 1D: today's date
    return now.toISOString().slice(0, 10);
  }
  const start = new Date(now);
  start.setDate(start.getDate() - config.daysBack);
  return start.toISOString().slice(0, 10);
}

export function useChartData(ticker: string, timeframe: ChartTimeframe): UseChartDataResult {
  const [bars, setBars] = useState<CandlestickData[] | null>(null);
  const [volumeData, setVolumeData] = useState<HistogramData[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Client-side cache keyed by `${ticker}-${timeframe}` (per D-21)
  const cache = useRef(new Map<string, ChartDataCache>());

  useEffect(() => {
    if (!ticker) {
      setBars(null);
      setVolumeData(null);
      setLoading(false);
      setError(null);
      return;
    }

    const cacheKey = `${ticker}-${timeframe}`;

    // Cache hit: set data immediately, skip fetch
    const cached = cache.current.get(cacheKey);
    if (cached) {
      setBars(cached.candles);
      setVolumeData(cached.volumes);
      setLoading(false);
      setError(null);
      return;
    }

    // Cache miss: fetch from Alpaca
    const config = TIMEFRAME_CONFIG[timeframe];
    const startDate = getStartDate(timeframe);
    const is15Min = config.alpacaTimeframe === '15Min';

    setLoading(true);
    setError(null);
    setBars(null);
    setVolumeData(null);

    const url = new URL(`https://data.alpaca.markets/v2/stocks/${ticker}/bars`);
    url.searchParams.set('timeframe', config.alpacaTimeframe);
    url.searchParams.set('start', startDate);
    url.searchParams.set('feed', 'iex');
    url.searchParams.set('limit', '1000');
    url.searchParams.set('sort', 'asc');

    const alpacaKey = import.meta.env.VITE_ALPACA_KEY as string | undefined;
    const alpacaSecret = import.meta.env.VITE_ALPACA_SECRET as string | undefined;

    fetch(url.toString(), {
      headers: {
        'APCA-API-KEY-ID': alpacaKey ?? '',
        'APCA-API-SECRET-KEY': alpacaSecret ?? '',
      },
    })
      .then(res => {
        if (!res.ok) {
          return res.text().then(text => {
            throw new Error(`Alpaca API error ${res.status}: ${text}`);
          });
        }
        return res.json();
      })
      .then((data: { bars: Array<{ t: string; o: number; h: number; l: number; c: number; v: number }> }) => {
        const rawBars = data.bars ?? [];

        const candles: CandlestickData[] = rawBars.map(bar => ({
          // For 15Min bars use Unix timestamp; for daily bars use date string
          time: is15Min
            ? (Math.floor(new Date(bar.t).getTime() / 1000) as unknown as Time)
            : (bar.t.slice(0, 10) as Time),
          open: bar.o,
          high: bar.h,
          low: bar.l,
          close: bar.c,
        }));

        const volumes: HistogramData[] = rawBars.map((bar, i) => ({
          time: candles[i].time,
          value: bar.v,
          color: bar.c >= bar.o ? '#22c55e33' : '#ef444433',
        }));

        // Store in cache
        cache.current.set(cacheKey, { candles, volumes });

        setBars(candles);
        setVolumeData(volumes);
        setLoading(false);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : String(err));
        setLoading(false);
      });
  }, [ticker, timeframe]);

  return { bars, volumeData, loading, error };
}
