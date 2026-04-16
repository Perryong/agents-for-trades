import { useState, useEffect, useCallback } from 'react';

interface UseConfigResult {
  config: Record<string, unknown> | null;
  loading: boolean;
  update: (key: string, value: unknown) => Promise<boolean>;
}

export function useConfig(): UseConfigResult {
  const [config, setConfig] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchConfig = useCallback(async () => {
    try {
      const res = await fetch('/api/config');
      if (res.ok) setConfig(await res.json());
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchConfig(); }, [fetchConfig]);

  const update = useCallback(async (key: string, value: unknown): Promise<boolean> => {
    try {
      const res = await fetch(`/api/config/${key}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value }),
      });
      if (res.ok) {
        setConfig(prev => prev ? { ...prev, [key]: value } : prev);
        return true;
      }
    } catch { /* ignore */ }
    return false;
  }, []);

  return { config, loading, update };
}
