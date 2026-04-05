import { useState, useEffect, useRef } from 'react';
import type { TradeStatus, OrderStatus } from '../types';

// 'filled' intentionally excluded: bracket orders remain open after fill.
// Polling continues until a bracket leg fills (Target Hit / Stop-Loss) or
// the user manually closes the position, transitioning to 'closed'.
const TERMINAL_STATUSES: OrderStatus[] = ['rejected', 'error', 'closed', 'expired'];

const INITIAL_STATUS: TradeStatus = {
  status: 'idle',
  fill_price: null,
  fill_time: null,
  close_time: null,
  rejection_reason: null,
  order_id: null,
  close_price: null,
  pnl_pct: null,
  outcome: null,
  close_reason: null,
};

export function useTradeStatus(ticker: string, orderId: string | null): TradeStatus {
  const [tradeStatus, setTradeStatus] = useState<TradeStatus>(INITIAL_STATUS);
  const intervalRef = useRef<ReturnType<typeof window.setInterval> | null>(null);

  useEffect(() => {
    // Clear any existing interval when orderId changes
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (!orderId || !ticker) {
      // No active order — reset to idle
      setTradeStatus(INITIAL_STATUS);
      return;
    }

    // Set submitted immediately when orderId is first set
    setTradeStatus(prev => ({ ...prev, status: 'submitted', order_id: orderId }));

    const poll = () => {
      fetch(`/api/trades/${encodeURIComponent(ticker)}/status?order_id=${encodeURIComponent(orderId)}`)
        .then(res => {
          if (!res.ok) {
            throw new Error(`Status poll error ${res.status}`);
          }
          return res.json();
        })
        .then((data: Partial<TradeStatus> & { status: string }) => {
          const status = data.status as OrderStatus;
          setTradeStatus({
            status,
            fill_price: data.fill_price ?? null,
            fill_time: data.fill_time ?? null,
            close_time: data.close_time ?? null,
            rejection_reason: data.rejection_reason ?? null,
            order_id: data.order_id ?? orderId,
            close_price: data.close_price ?? null,
            pnl_pct: data.pnl_pct ?? null,
            outcome: data.outcome ?? null,
            close_reason: data.close_reason ?? null,
          });

          // Stop polling when terminal state is reached
          if (TERMINAL_STATUSES.includes(status)) {
            if (intervalRef.current !== null) {
              clearInterval(intervalRef.current);
              intervalRef.current = null;
            }
          }

          // After fill, slow polling to every 10s (bracket legs may take time)
          if (status === 'filled' && intervalRef.current !== null) {
            clearInterval(intervalRef.current);
            intervalRef.current = window.setInterval(poll, 10000);
          }
        })
        .catch((err: unknown) => {
          console.error('useTradeStatus poll error:', err instanceof Error ? err.message : String(err));
          setTradeStatus(prev => ({ ...prev, status: 'error' }));
          if (intervalRef.current !== null) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
        });
    };

    // Poll immediately, then every 3 seconds
    poll();
    intervalRef.current = window.setInterval(poll, 3000);

    return () => {
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [ticker, orderId]);

  return tradeStatus;
}
