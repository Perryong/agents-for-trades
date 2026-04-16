import type { AgentSignalSummary } from '../types';

interface ConsensusIndicatorProps {
  signals: AgentSignalSummary[];
}

const SIGNAL_COLORS: Record<string, string> = {
  BUY: 'bg-accent-green',
  SELL: 'bg-accent-red',
  HOLD: 'bg-text-tertiary',
  'NO TRADE': 'bg-text-tertiary',
  bullish: 'bg-accent-green',
  bearish: 'bg-accent-red',
  neutral: 'bg-text-tertiary',
};

function getColor(signal: string): string {
  return SIGNAL_COLORS[signal] ?? SIGNAL_COLORS[signal.toLowerCase()] ?? 'bg-text-tertiary';
}

export function ConsensusIndicator({ signals }: ConsensusIndicatorProps) {
  const bullish = signals.filter(s => ['BUY', 'bullish'].includes(s.signal)).length;
  const bearish = signals.filter(s => ['SELL', 'bearish'].includes(s.signal)).length;
  const neutral = signals.length - bullish - bearish;

  const parts: string[] = [];
  if (bullish > 0) parts.push(`${bullish} bullish`);
  if (bearish > 0) parts.push(`${bearish} bearish`);
  if (neutral > 0) parts.push(`${neutral} neutral`);
  const tooltip = `${bullish + bearish + neutral} agents: ${parts.join(', ')}`;

  return (
    <div className="flex items-center gap-1" title={tooltip}>
      {signals.map((s, i) => (
        <span
          key={i}
          className={`w-2 h-2 rounded-full ${getColor(s.signal)}`}
        />
      ))}
    </div>
  );
}
