import { useState, useEffect } from 'react';

export interface RegimeData {
  regime: string;
  confidence: number;
  breadth_score: number;
  breadth_label: string;
  computed_at: string;
}

export function useRegime(): { regime: RegimeData | null; loading: boolean } {
  const [regime, setRegime] = useState<RegimeData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/regime')
      .then(r => r.ok ? r.json() : null)
      .then((data: RegimeData | null) => { setRegime(data); setLoading(false); })
      .catch(() => setLoading(false));

    // Refresh every 15 minutes
    const id = setInterval(() => {
      fetch('/api/regime')
        .then(r => r.ok ? r.json() : null)
        .then((data: RegimeData | null) => { if (data) setRegime(data); })
        .catch(() => {});
    }, 15 * 60_000);

    return () => clearInterval(id);
  }, []);

  return { regime, loading };
}
