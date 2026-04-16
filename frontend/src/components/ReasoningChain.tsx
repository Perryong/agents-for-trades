import type { AgentSignalSummary } from '../types';

interface ReasoningChainProps {
  signals: AgentSignalSummary[];
  expanded: boolean;
}

const SIGNAL_COLORS: Record<string, string> = {
  BUY: 'text-accent-green',
  SELL: 'text-accent-red',
  HOLD: 'text-text-tertiary',
  'NO TRADE': 'text-text-tertiary',
  bullish: 'text-accent-green',
  bearish: 'text-accent-red',
  neutral: 'text-text-tertiary',
};

function getMajoritySignal(signals: AgentSignalSummary[]): string {
  const counts: Record<string, number> = {};
  for (const s of signals) {
    const key = s.signal.toLowerCase();
    counts[key] = (counts[key] || 0) + 1;
  }
  let maxKey = '';
  let maxCount = 0;
  for (const [key, count] of Object.entries(counts)) {
    if (count > maxCount) { maxKey = key; maxCount = count; }
  }
  return maxKey;
}

function isDissenting(signal: string, majority: string): boolean {
  const norm = signal.toLowerCase();
  const bullish = ['buy', 'bullish'];
  const bearish = ['sell', 'bearish'];
  if (bullish.includes(majority)) return !bullish.includes(norm);
  if (bearish.includes(majority)) return !bearish.includes(norm);
  return norm !== majority;
}

export function ReasoningChain({ signals, expanded }: ReasoningChainProps) {
  const majority = getMajoritySignal(signals);
  const riskJudge = signals.find(s => s.agent_name.toLowerCase().includes('risk judge'));
  const agents = signals.filter(s => s !== riskJudge);

  return (
    <div className={`transition-[max-height] duration-150 ease-out overflow-hidden ${expanded ? 'max-h-[600px]' : 'max-h-0'}`}>
      <div className="pt-3 mt-2 border-t border-border-subtle space-y-2">
        {agents.map((s, i) => {
          const dissent = isDissenting(s.signal, majority);
          const color = SIGNAL_COLORS[s.signal] ?? SIGNAL_COLORS[s.signal.toLowerCase()] ?? 'text-text-tertiary';

          return (
            <div key={i} className="flex items-start gap-2">
              <span className={`text-[13px] font-medium min-w-[140px] flex-shrink-0 ${dissent ? 'text-accent-amber' : 'text-text-primary'}`}>
                {s.agent_name}
              </span>
              <span className={`text-[13px] font-mono flex-shrink-0 ${color}`}>
                {s.signal} {s.confidence.toFixed(0)}%
              </span>
              <span className="text-[13px] text-text-secondary truncate">{s.rationale}</span>
            </div>
          );
        })}

        {/* Risk Judge Resolution */}
        {riskJudge && (
          <div className="pt-2 mt-2 border-t border-border-subtle">
            <p className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-1">Risk Judge Resolution</p>
            <p className="text-[13px] text-text-secondary">{riskJudge.rationale || 'Signals synthesized into final recommendation.'}</p>
          </div>
        )}

        {!riskJudge && agents.length > 0 && (
          <div className="pt-2 mt-2 border-t border-border-subtle">
            <p className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-1">Risk Judge Resolution</p>
            <p className="text-[13px] text-text-secondary">
              Majority signal: {majority}. {agents.filter(s => isDissenting(s.signal, majority)).length} dissenting agent(s).
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
