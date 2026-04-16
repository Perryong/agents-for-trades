import { useState, useEffect, useCallback, useRef } from 'react';
import type { Position, QuickStats } from '../types';

interface UsePositionsResult {
  positions: Position[];
  stats: QuickStats | null;
  loading: boolean;
}

export function usePositions(): UsePositionsResult {
  const [positions, setPositions] = useState<Position[]>([]);
  const [stats, setStats] = useState<QuickStats | null>(null);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<number | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [posRes, statsRes] = await Promise.all([
        fetch('/api/positions'),
        fetch('/api/positions/stats'),
      ]);
      if (posRes.ok) setPositions(await posRes.json());
      if (statsRes.ok) setStats(await statsRes.json());
    } catch { /* ignore fetch errors */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    fetchData();
    intervalRef.current = window.setInterval(fetchData, 30_000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchData]);

  return { positions, stats, loading };
}
