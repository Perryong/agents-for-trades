import { useRegime } from '../hooks/useRegime';

const REGIME_COLORS: Record<string, string> = {
  Broadening: 'bg-accent-green/15 text-accent-green border-accent-green/30',
  Concentration: 'bg-accent-amber/15 text-accent-amber border-accent-amber/30',
  Transitional: 'bg-accent-amber/15 text-accent-amber border-accent-amber/30',
  Contraction: 'bg-accent-red/15 text-accent-red border-accent-red/30',
  Inflationary: 'bg-accent-red/15 text-accent-red border-accent-red/30',
};

export function RegimeBadge() {
  const { regime, loading } = useRegime();

  if (loading || !regime) return null;

  const colorClass = REGIME_COLORS[regime.regime] ?? REGIME_COLORS.Transitional;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-sm border text-[11px] font-medium ${colorClass}`}
      title={`${regime.regime} regime (${regime.confidence.toFixed(0)}% confidence)\nBreadth: ${regime.breadth_score.toFixed(0)}/100 (${regime.breadth_label})\nUpdated: ${new Date(regime.computed_at).toLocaleTimeString()}`}
    >
      {regime.regime}
      <span className="font-mono text-[10px] opacity-70">{regime.breadth_score.toFixed(0)}</span>
    </span>
  );
}
