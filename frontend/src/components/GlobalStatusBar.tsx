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
    <div className="flex items-center gap-3 px-4 py-2 bg-blue-50 dark:bg-blue-900/30 border-b border-blue-200 dark:border-blue-800 text-sm">
      <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse flex-shrink-0" />
      <span className="text-blue-700 dark:text-blue-300 flex-1">
        {status === 'cancelling'
          ? 'Cancelling...'
          : `Analyzing ${ticker}... ${completedCount}/${totalCount} agents done`}
      </span>
      {status === 'running' && (
        <button
          onClick={onCancel}
          aria-label="Cancel analysis"
          className="text-blue-600 dark:text-blue-400 hover:text-red-600 dark:hover:text-red-400 font-medium transition-colors"
        >
          Cancel
        </button>
      )}
    </div>
  );
}
