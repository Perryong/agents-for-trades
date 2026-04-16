import type { Recommendation } from '../types';
import { ConsensusIndicator } from './ConsensusIndicator';
import { TradeSpecGrid } from './TradeSpecGrid';
import { ReasoningChain } from './ReasoningChain';

interface RecommendationCardProps {
  recommendation: Recommendation;
  focused?: boolean;
  expanded?: boolean;
  onToggleExpand?: () => void;
  onApprove?: () => void;
  onSkip?: () => void;
}

function timeRemaining(validUntil: string | null): { text: string; urgent: boolean } {
  if (!validUntil) return { text: '', urgent: false };
  try {
    const diff = new Date(validUntil).getTime() - Date.now();
    if (diff <= 0) return { text: 'Expired', urgent: true };
    const mins = Math.floor(diff / 60_000);
    if (mins < 60) return { text: `${mins}m left`, urgent: mins < 30 };
    const hrs = Math.floor(mins / 60);
    return { text: `${hrs}h ${mins % 60}m left`, urgent: false };
  } catch {
    return { text: '', urgent: false };
  }
}

function isStalePreMarket(createdAt: string | undefined): boolean {
  if (!createdAt) return false;
  try {
    const age = Date.now() - new Date(createdAt).getTime();
    return age > 2 * 60 * 60 * 1000; // > 2 hours old
  } catch { return false; }
}

const STATUS_CLASSES: Record<string, string> = {
  pending: '',
  approved: 'bg-accent-green/5 border-accent-green/20',
  skipped: 'opacity-50',
  expired: 'opacity-30',
};

export function RecommendationCard({ recommendation: rec, focused, expanded, onToggleExpand, onApprove, onSkip }: RecommendationCardProps) {
  const isNoTrade = !rec.direction;
  const { text: countdown, urgent } = timeRemaining(rec.valid_until);
  const statusClass = STATUS_CLASSES[rec.status] ?? '';
  const isPending = rec.status === 'pending';
  const stale = isStalePreMarket((rec as any).created_at);

  return (
    <div
      onClick={onToggleExpand}
      className={`bg-bg-elevated border border-border-subtle rounded-sm p-3 cursor-pointer transition-colors hover:border-border-default ${statusClass} ${focused ? 'ring-1 ring-accent-blue' : ''}`}
    >
      {/* Top row: ticker, direction, strategy, confidence */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[16px] font-mono font-medium text-text-primary">{rec.ticker}</span>

        {/* Trade type badge */}
        <span className={`px-1.5 py-0.5 rounded-sm text-[10px] font-medium uppercase ${
          rec.trade_type === 'option'
            ? 'bg-accent-amber/15 text-accent-amber'
            : 'bg-accent-blue/15 text-accent-blue'
        }`}>
          {rec.trade_type === 'option' ? 'Options' : 'Equity'}
        </span>

        {isNoTrade ? (
          <span className="text-[11px] font-medium text-text-tertiary uppercase">No Trade</span>
        ) : (
          <span className={`text-[11px] font-medium uppercase ${rec.direction === 'BUY' ? 'text-accent-green' : 'text-accent-red'}`}>
            {rec.direction}
          </span>
        )}

        {rec.strategy && (
          <span className="text-[11px] text-text-secondary">{rec.strategy}</span>
        )}

        <span className="flex-1" />

        <span className="text-[14px] font-mono font-medium text-text-primary">{rec.confidence.toFixed(0)}%</span>
      </div>

      {/* Middle: consensus + countdown + status/actions */}
      <div className="flex items-center gap-3 mb-2">
        {rec.agent_signals.length > 0 && (
          <ConsensusIndicator signals={rec.agent_signals} />
        )}
        {stale && isPending && (
          <span className="text-[10px] font-medium text-accent-amber bg-accent-amber/10 px-1.5 py-0.5 rounded-sm">
            Pre-market analysis — verify at open
          </span>
        )}
        {countdown && (
          <span className={`text-[11px] font-mono ${urgent ? 'text-accent-amber' : 'text-text-secondary'}`}>
            {countdown}
          </span>
        )}

        <span className="flex-1" />

        {rec.status === 'approved' && (
          <span className="text-[11px] font-medium text-accent-green">Approved</span>
        )}
        {rec.status === 'skipped' && (
          <span className="text-[11px] font-medium text-text-tertiary">Skipped</span>
        )}
        {rec.status === 'expired' && (
          <span className="text-[11px] font-medium text-text-tertiary">Expired</span>
        )}
        {isPending && !isNoTrade && (
          <div className="flex items-center gap-2">
            <button
              onClick={(e) => { e.stopPropagation(); onApprove?.(); }}
              className="text-[11px] font-medium text-accent-green hover:text-accent-green/80 transition-colors"
            >
              Approve <span className="text-text-tertiary">A</span>
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onSkip?.(); }}
              className="text-[11px] font-medium text-text-secondary hover:text-text-primary transition-colors"
            >
              Skip <span className="text-text-tertiary">S</span>
            </button>
          </div>
        )}
      </div>

      {/* Trade specs or no-trade reason */}
      {isNoTrade ? (
        rec.no_trade_reason && (
          <p className="text-[13px] text-text-secondary">{rec.no_trade_reason}</p>
        )
      ) : rec.trade_spec ? (
        <>
          <TradeSpecGrid spec={rec.trade_spec} direction={rec.direction} />
          {/* Options-specific details */}
          {rec.trade_type === 'option' && rec.trade_spec.strike && (
            <div className="flex items-center gap-3 mt-1 text-[11px] font-mono text-text-secondary">
              <span>{rec.trade_spec.contract_type?.toUpperCase()}</span>
              <span>${rec.trade_spec.strike}</span>
              <span>{rec.trade_spec.expiry}</span>
            </div>
          )}
        </>
      ) : null}

      {/* Reasoning chain (expandable) */}
      {rec.agent_signals.length > 0 && (
        <ReasoningChain signals={rec.agent_signals} expanded={!!expanded} />
      )}
    </div>
  );
}
