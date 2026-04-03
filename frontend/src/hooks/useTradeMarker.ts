import type { TradeStatus } from '../types';

export interface TradeMarkerProps {
  fillDate: string;
  fillPrice: number;
  direction: string;
  closeDate?: string;
  closePrice?: number;
}

/**
 * Derives trade fill/exit marker data from a TradeStatus and signal direction.
 * Returns a tradeMarker object ready for ChartContainer, or null when no filled trade.
 *
 * - Entry marker: present when status === 'filled' and fill_price + fill_time available
 * - Exit marker: appended when outcome is set AND close_time is not null
 *   (close_time is a typed field on TradeStatus — no unsafe casts needed)
 */
export function useTradeMarker(
  tradeStatus: TradeStatus | null,
  direction: string,
): TradeMarkerProps | null {
  if (
    !tradeStatus ||
    tradeStatus.status !== 'filled' ||
    tradeStatus.fill_price === null ||
    tradeStatus.fill_time === null
  ) {
    return null;
  }

  const marker: TradeMarkerProps = {
    fillDate: tradeStatus.fill_time.slice(0, 10),
    fillPrice: tradeStatus.fill_price,
    direction,
  };

  // Add exit info when the trade was closed (outcome set, close_time is typed — no as-any)
  if (tradeStatus.outcome !== null && tradeStatus.close_time !== null && tradeStatus.close_price !== null) {
    marker.closeDate = tradeStatus.close_time.slice(0, 10);
    marker.closePrice = tradeStatus.close_price;
  }

  return marker;
}
