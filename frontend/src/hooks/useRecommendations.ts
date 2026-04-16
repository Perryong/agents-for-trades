import { useState, useEffect, useCallback, useRef } from 'react';
import type { Recommendation } from '../types';

interface UseRecommendationsResult {
  recommendations: Recommendation[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
  approve: (id: number) => Promise<void>;
  skip: (id: number) => Promise<void>;
}

export function useRecommendations(): UseRecommendationsResult {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<number | null>(null);

  const fetchRecommendations = useCallback(async () => {
    try {
      const res = await fetch('/api/recommendations');
      if (!res.ok) {
        if (res.status === 404) {
          setRecommendations([]);
          setError(null);
          return;
        }
        throw new Error(`HTTP ${res.status}`);
      }
      const data: Recommendation[] = await res.json();
      // Sort by confidence descending
      data.sort((a, b) => b.confidence - a.confidence);
      setRecommendations(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to fetch');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRecommendations();
    intervalRef.current = window.setInterval(fetchRecommendations, 30_000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchRecommendations]);

  // Check for expired recommendations every 60 seconds
  useEffect(() => {
    const checkExpiry = () => {
      const now = Date.now();
      setRecommendations(prev => prev.map(r => {
        if (r.status !== 'pending' || !r.valid_until) return r;
        try {
          if (new Date(r.valid_until).getTime() < now) return { ...r, status: 'expired' as const };
        } catch { /* ignore parse errors */ }
        return r;
      }));
    };
    const id = window.setInterval(checkExpiry, 60_000);
    return () => clearInterval(id);
  }, []);

  const approve = useCallback(async (id: number) => {
    const res = await fetch(`/api/recommendations/${id}/approve`, { method: 'POST' });
    if (!res.ok) { console.error('Failed to approve recommendation', id, res.status); return; }
    setRecommendations(prev =>
      prev.map(r => r.id === id ? { ...r, status: 'approved' as const } : r)
    );
  }, []);

  const skip = useCallback(async (id: number) => {
    const res = await fetch(`/api/recommendations/${id}/skip`, { method: 'POST' });
    if (!res.ok) { console.error('Failed to skip recommendation', id, res.status); return; }
    setRecommendations(prev =>
      prev.map(r => r.id === id ? { ...r, status: 'skipped' as const } : r)
    );
  }, []);

  return { recommendations, loading, error, refresh: fetchRecommendations, approve, skip };
}
