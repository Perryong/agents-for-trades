import { useState } from 'react';
import type { TradeRequest, TradeResponse } from '../types';

interface UseTradeResult {
  submitTrade: (req: TradeRequest) => Promise<TradeResponse>;
  isSubmitting: boolean;
}

export function useTrade(): UseTradeResult {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submitTrade = async (req: TradeRequest): Promise<TradeResponse> => {
    setIsSubmitting(true);
    try {
      const res = await fetch('/api/trades', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
      });

      if (!res.ok) {
        let detail = `HTTP ${res.status}`;
        try {
          const errBody = await res.json() as { detail?: string };
          if (errBody.detail) detail = errBody.detail;
        } catch {
          // ignore JSON parse failure
        }
        throw new Error(detail);
      }

      const data = await res.json() as TradeResponse;
      return data;
    } finally {
      setIsSubmitting(false);
    }
  };

  return { submitTrade, isSubmitting };
}
