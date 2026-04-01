import type { AnalysisStatus } from '../types';

interface ReportPaneProps {
  content: string | null;
  status: AnalysisStatus;
}

export function ReportPane({ content, status }: ReportPaneProps) {
  if (status === 'error') {
    return (
      <div className="text-red-500 dark:text-red-400 text-sm">
        An error occurred during analysis.
      </div>
    );
  }

  if (status === 'idle') {
    return (
      <div className="text-gray-400 dark:text-gray-500 text-sm">
        Run an analysis to see reports here.
      </div>
    );
  }

  if (!content) {
    return (
      <div className="text-gray-400 dark:text-gray-500 text-sm animate-pulse">
        Waiting for results...
      </div>
    );
  }

  return (
    <div className="prose prose-sm max-w-none">
      <pre className="whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-200 bg-gray-50 dark:bg-gray-800 p-4 rounded-lg overflow-auto border border-gray-200 dark:border-gray-700">
        {content}
      </pre>
    </div>
  );
}
