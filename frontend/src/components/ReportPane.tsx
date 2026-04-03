import ReactMarkdown from 'react-markdown';
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
    <div className="report-markdown text-gray-800 dark:text-gray-200 text-sm leading-relaxed">
      <ReactMarkdown
        components={{
          h1: ({ children }) => <h1 className="text-xl font-bold text-gray-900 dark:text-gray-50 mt-6 mb-3 border-b border-gray-200 dark:border-gray-700 pb-2">{children}</h1>,
          h2: ({ children }) => <h2 className="text-lg font-bold text-gray-900 dark:text-gray-50 mt-5 mb-2 border-b border-gray-200 dark:border-gray-700 pb-1">{children}</h2>,
          h3: ({ children }) => <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mt-4 mb-2">{children}</h3>,
          h4: ({ children }) => <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-3 mb-1">{children}</h4>,
          p: ({ children }) => <p className="text-gray-700 dark:text-gray-300 mb-3">{children}</p>,
          strong: ({ children }) => <strong className="font-semibold text-gray-900 dark:text-gray-100">{children}</strong>,
          em: ({ children }) => <em className="text-gray-600 dark:text-gray-400">{children}</em>,
          ul: ({ children }) => <ul className="list-disc list-inside mb-3 space-y-1 text-gray-700 dark:text-gray-300">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal list-inside mb-3 space-y-1 text-gray-700 dark:text-gray-300">{children}</ol>,
          li: ({ children }) => <li className="text-gray-700 dark:text-gray-300">{children}</li>,
          blockquote: ({ children }) => <blockquote className="border-l-4 border-blue-400 dark:border-blue-600 pl-4 my-3 text-gray-600 dark:text-gray-400 italic">{children}</blockquote>,
          code: ({ className, children }) => {
            const isBlock = className?.includes('language-');
            if (isBlock) {
              return <code className="block bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 p-4 rounded-lg overflow-auto text-xs border border-gray-200 dark:border-gray-700 my-3">{children}</code>;
            }
            return <code className="bg-gray-100 dark:bg-gray-800 text-pink-600 dark:text-pink-400 px-1.5 py-0.5 rounded text-xs">{children}</code>;
          },
          pre: ({ children }) => <pre className="my-3">{children}</pre>,
          table: ({ children }) => (
            <div className="overflow-x-auto my-3">
              <table className="min-w-full border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-gray-100 dark:bg-gray-700">{children}</thead>,
          th: ({ children }) => <th className="px-3 py-2 text-left text-xs font-semibold text-gray-900 dark:text-gray-100 border-b border-gray-200 dark:border-gray-600">{children}</th>,
          td: ({ children }) => <td className="px-3 py-2 text-xs text-gray-700 dark:text-gray-300 border-b border-gray-100 dark:border-gray-700">{children}</td>,
          hr: () => <hr className="my-4 border-gray-200 dark:border-gray-700" />,
          a: ({ href, children }) => <a href={href} className="text-blue-600 dark:text-blue-400 underline" target="_blank" rel="noopener noreferrer">{children}</a>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
