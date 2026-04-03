import { useState, useEffect } from 'react';
import type { DashboardSummary, DashboardTradesData, EquityCurveData } from '../types';

function buildQuery(ticker?: string, tradeType?: string): string {
  const params = new URLSearchParams();
  if (ticker) params.set('ticker', ticker);
  if (tradeType) params.set('type', tradeType);
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

interface UseDashboardSummaryResult {
  summary: DashboardSummary | null;
  loading: boolean;
}

export function useDashboardSummary(ticker?: string, tradeType?: string): UseDashboardSummaryResult {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/dashboard/summary${buildQuery(ticker, tradeType)}`)
      .then(res => {
        if (!res.ok) throw new Error(`Dashboard summary fetch error ${res.status}`);
        return res.json();
      })
      .then((data: DashboardSummary) => {
        setSummary(data);
        setLoading(false);
      })
      .catch((err: unknown) => {
        console.error('useDashboardSummary error:', err instanceof Error ? err.message : String(err));
        setSummary(null);
        setLoading(false);
      });
  }, [ticker, tradeType]);

  return { summary, loading };
}

interface UseDashboardTradesResult {
  trades: DashboardTradesData | null;
  loading: boolean;
}

export function useDashboardTrades(ticker?: string, tradeType?: string): UseDashboardTradesResult {
  const [trades, setTrades] = useState<DashboardTradesData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/dashboard/trades${buildQuery(ticker, tradeType)}`)
      .then(res => {
        if (!res.ok) throw new Error(`Dashboard trades fetch error ${res.status}`);
        return res.json();
      })
      .then((data: DashboardTradesData) => {
        setTrades(data);
        setLoading(false);
      })
      .catch((err: unknown) => {
        console.error('useDashboardTrades error:', err instanceof Error ? err.message : String(err));
        setTrades(null);
        setLoading(false);
      });
  }, [ticker, tradeType]);

  return { trades, loading };
}

interface UseEquityCurveResult {
  curve: EquityCurveData | null;
  loading: boolean;
}

export function useEquityCurve(ticker?: string, tradeType?: string): UseEquityCurveResult {
  const [curve, setCurve] = useState<EquityCurveData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/dashboard/equity-curve${buildQuery(ticker, tradeType)}`)
      .then(res => {
        if (!res.ok) throw new Error(`Equity curve fetch error ${res.status}`);
        return res.json();
      })
      .then((data: EquityCurveData) => {
        setCurve(data);
        setLoading(false);
      })
      .catch((err: unknown) => {
        console.error('useEquityCurve error:', err instanceof Error ? err.message : String(err));
        setCurve(null);
        setLoading(false);
      });
  }, [ticker, tradeType]);

  return { curve, loading };
}
