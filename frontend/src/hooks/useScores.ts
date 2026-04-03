import { useState, useEffect } from 'react';
import type { ScoreSummary, CalibrationData } from '../types';

interface UseScoreSummaryResult {
  summary: ScoreSummary | null;
  loading: boolean;
}

export function useScoreSummary(): UseScoreSummaryResult {
  const [summary, setSummary] = useState<ScoreSummary | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);

    fetch('/api/scores/summary')
      .then(res => {
        if (!res.ok) {
          throw new Error(`Score summary fetch error ${res.status}`);
        }
        return res.json();
      })
      .then((data: ScoreSummary) => {
        setSummary(data);
        setLoading(false);
      })
      .catch((err: unknown) => {
        console.error('useScoreSummary error:', err instanceof Error ? err.message : String(err));
        setSummary(null);
        setLoading(false);
      });
  }, []);

  return { summary, loading };
}

interface UseCalibrationResult {
  calibration: CalibrationData | null;
  loading: boolean;
}

export function useCalibration(): UseCalibrationResult {
  const [calibration, setCalibration] = useState<CalibrationData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);

    fetch('/api/scores/calibration')
      .then(res => {
        if (!res.ok) {
          throw new Error(`Calibration fetch error ${res.status}`);
        }
        return res.json();
      })
      .then((data: CalibrationData) => {
        setCalibration(data);
        setLoading(false);
      })
      .catch((err: unknown) => {
        console.error('useCalibration error:', err instanceof Error ? err.message : String(err));
        setCalibration(null);
        setLoading(false);
      });
  }, []);

  return { calibration, loading };
}
