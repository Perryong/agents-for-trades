import type { AnalysisStatus } from '../types';

interface GlobalStatusBarProps {
  status: AnalysisStatus;
  completedCount: number;
  totalCount: number;
  ticker: string;
  onCancel: () => void;
}

export function GlobalStatusBar({ status, completedCount, totalCount, ticker, onCancel }: GlobalStatusBarProps) {
  if (status !== 'running' && status !== 'cancelling') return null;

  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-accent-blue/10 border-b border-accent-blue/30 text-sm">
      <div className="w-2 h-2 rounded-full bg-accent-blue animate-pulse flex-shrink-0" />
      <span className="text-accent-blue flex-1">
        {status === 'cancelling'
          ? 'Cancelling...'
          : `Analyzing ${ticker}... ${completedCount}/${totalCount} agents done`}
      </span>
      {status === 'running' && (
        <button
          onClick={onCancel}
          aria-label="Cancel analysis"
          className="text-accent-blue hover:text-accent-red font-medium transition-colors"
        >
          Cancel
        </button>
      )}
    </div>
  );
}
