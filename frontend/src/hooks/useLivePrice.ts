import { useState, useEffect, useRef } from 'react';
import type { LivePriceData } from '../types';

export function useLivePrice(ticker: string | null): LivePriceData | null {
  const [livePrice, setLivePrice] = useState<LivePriceData | null>(null);
  const intervalRef = useRef<ReturnType<typeof window.setInterval> | null>(null);

  useEffect(() => {
    // Clear previous interval
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (!ticker) {
      setLivePrice(null);
      return;
    }

    const fetchPrice = () => {
      fetch(`/api/price/${encodeURIComponent(ticker)}/live`)
        .then(res => {
          if (!res.ok) return null;
          return res.json();
        })
        .then((data: LivePriceData | null) => {
          if (data) {
            setLivePrice(data);
          }
        })
        .catch(() => {
          // Silently fail per UI-SPEC: show "--" for price on error
        });
    };

    // Fetch immediately, then every 5 seconds
    fetchPrice();
    intervalRef.current = window.setInterval(fetchPrice, 5000);

    return () => {
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [ticker]);

  return livePrice;
}
