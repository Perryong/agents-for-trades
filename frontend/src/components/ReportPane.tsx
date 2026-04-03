import { useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import type { AnalysisStatus } from '../types';

interface ReportPaneProps {
  content: string | null;
  status: AnalysisStatus;
  tabLabel?: string;
}

function CopyButton({ content }: { content: string }) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <button
      onClick={handleCopy}
      className="px-3 py-1.5 text-xs font-medium rounded-md border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
    >
      {copied ? 'Copied!' : 'Copy'}
    </button>
  );
}

function PdfButton({ contentRef, tabLabel }: { contentRef: React.RefObject<HTMLDivElement | null>; tabLabel: string }) {
  const [exporting, setExporting] = useState(false);

  async function handleExport() {
    if (!contentRef.current) return;
    setExporting(true);

    // Use browser print with a styled clone
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      setExporting(false);
      return;
    }

    const html = contentRef.current.innerHTML;

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>${tabLabel} Report</title>
        <style>
          body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 0 20px;
            color: #1a1a1a;
            font-size: 13px;
            line-height: 1.6;
          }
          h1 { font-size: 22px; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px; margin-top: 24px; }
          h2 { font-size: 18px; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; margin-top: 20px; }
          h3 { font-size: 15px; margin-top: 16px; }
          h4 { font-size: 13px; margin-top: 12px; }
          p { margin-bottom: 12px; }
          ul, ol { margin-bottom: 12px; padding-left: 24px; }
          li { margin-bottom: 4px; }
          table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 12px; }
          th { background: #f3f4f6; padding: 6px 10px; text-align: left; border: 1px solid #e5e7eb; font-weight: 600; }
          td { padding: 6px 10px; border: 1px solid #e5e7eb; }
          blockquote { border-left: 4px solid #3b82f6; padding-left: 16px; color: #6b7280; font-style: italic; }
          code { background: #f3f4f6; padding: 1px 4px; border-radius: 3px; font-size: 12px; }
          pre code { display: block; padding: 12px; overflow-x: auto; }
          hr { border: none; border-top: 1px solid #e5e7eb; margin: 16px 0; }
          strong { font-weight: 600; }
          .header { text-align: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 2px solid #1a1a1a; }
          .header h1 { border: none; margin: 0; font-size: 20px; }
          .header p { color: #6b7280; margin: 4px 0 0; font-size: 12px; }
          @media print { body { margin: 20px; } }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>TradingAgents — ${tabLabel} Report</h1>
          <p>Generated: ${new Date().toLocaleString()}</p>
        </div>
        ${html}
      </body>
      </html>
    `);
    printWindow.document.close();

    // Wait for content to render, then trigger print (Save as PDF)
    setTimeout(() => {
      printWindow.print();
      setExporting(false);
    }, 500);
  }

  return (
    <button
      onClick={handleExport}
      disabled={exporting}
      className="px-3 py-1.5 text-xs font-medium rounded-md border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
    >
      {exporting ? 'Exporting...' : 'Export PDF'}
    </button>
  );
}

export function ReportPane({ content, status, tabLabel = 'Report' }: ReportPaneProps) {
  const contentRef = useRef<HTMLDivElement>(null);

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
    <div>
      {/* Action bar */}
      <div className="flex gap-2 mb-4">
        <CopyButton content={content} />
        <PdfButton contentRef={contentRef} tabLabel={tabLabel} />
      </div>

      {/* Report content */}
      <div ref={contentRef} className="report-markdown text-gray-800 dark:text-gray-200 text-sm leading-relaxed">
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
    </div>
  );
}
