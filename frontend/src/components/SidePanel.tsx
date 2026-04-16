import { usePositions } from '../hooks/usePositions';
import { PositionCard } from './PositionCard';
import { QuickStatsGrid } from './QuickStatsGrid';

interface SidePanelProps {
  onNavigateChart?: (ticker: string) => void;
}

export function SidePanel({ onNavigateChart }: SidePanelProps) {
  const { positions, stats, loading } = usePositions();

  return (
    <aside className="w-[320px] flex-shrink-0 border-l border-border-subtle bg-bg-secondary overflow-y-auto">
      {/* Positions */}
      <div className="border-b border-border-subtle">
        <div className="p-4 pb-2">
          <h3 className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider">Positions</h3>
        </div>
        {loading ? (
          <div className="px-4 pb-4">
            <div className="h-12 bg-bg-hover rounded-sm animate-pulse" />
          </div>
        ) : positions.length === 0 ? (
          <p className="px-4 pb-4 text-[13px] text-text-tertiary">No open positions</p>
        ) : (
          positions.map(pos => (
            <PositionCard
              key={pos.id}
              position={pos}
              onClick={() => onNavigateChart?.(pos.ticker)}
            />
          ))
        )}
      </div>

      {/* Quick Stats */}
      <div className="p-4">
        <h3 className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-3">Quick Stats</h3>
        <QuickStatsGrid stats={stats} />
      </div>
    </aside>
  );
}
