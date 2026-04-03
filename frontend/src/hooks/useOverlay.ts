import { useState, useEffect } from 'react';
import type { ChartOverlay } from '../types';

interface UseOverlayResult {
  overlay: ChartOverlay | null;
  loading: boolean;
}

export function useOverlay(ticker: string): UseOverlayResult {
  const [overlay, setOverlay] = useState<ChartOverlay | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!ticker) {
      setOverlay(null);
      setLoading(false);
      return;
    }

    setLoading(true);

    fetch(`/api/chart/${ticker}/overlay`)
      .then(res => {
        if (res.status === 404) {
          // Passive mode — no analysis exists for this ticker
          setOverlay(null);
          setLoading(false);
          return null;
        }
        if (!res.ok) {
          throw new Error(`Overlay fetch error ${res.status}`);
        }
        return res.json();
      })
      .then((data: ChartOverlay | null) => {
        if (data !== null) {
          setOverlay(data);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        console.error('useOverlay error:', err instanceof Error ? err.message : String(err));
        setOverlay(null);
        setLoading(false);
      });
  }, [ticker]);

  return { overlay, loading };
}
