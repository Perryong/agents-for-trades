import { useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import type { AnalysisStatus } from '../types';

interface ReportPaneProps {
  content: string | null;
  status: AnalysisStatus;
  tabLabel?: string;
  volContext?: string;    // Vol narrative string; undefined or empty = no banner
  isEquityTab?: boolean; // Only equity tabs show the banner
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
      className="px-3 py-1.5 text-xs font-medium rounded-sm border border-border-default text-text-secondary hover:bg-bg-hover transition-colors"
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
      className="px-3 py-1.5 text-xs font-medium rounded-sm border border-border-default text-text-secondary hover:bg-bg-hover disabled:opacity-50 transition-colors"
    >
      {exporting ? 'Exporting...' : 'Export PDF'}
    </button>
  );
}

export function ReportPane({ content, status, tabLabel = 'Report', volContext, isEquityTab }: ReportPaneProps) {
  const contentRef = useRef<HTMLDivElement>(null);

  if (status === 'error') {
    return (
      <div className="text-accent-red text-sm">
        An error occurred during analysis.
      </div>
    );
  }

  if (status === 'idle') {
    return (
      <div className="text-text-tertiary text-sm">
        Run an analysis to see reports here.
      </div>
    );
  }

  if (!content) {
    return (
      <div className="text-text-tertiary text-sm animate-pulse">
        Waiting for results...
      </div>
    );
  }

  return (
    <div>
      {/* Vol Context Banner — equity tabs only, hidden when vol context unavailable */}
      {isEquityTab && volContext && (
        <details
          open
          className="mb-4 rounded-sm border border-accent-blue/30 bg-accent-blue/10 vol-context-banner"
        >
          <summary className="cursor-pointer px-4 py-2 text-xs font-semibold text-accent-blue select-none list-none flex items-center justify-between">
            <span>Vol Context</span>
            <span className="text-accent-blue/60 font-normal">click to collapse</span>
          </summary>
          <div className="px-4 pb-3 pt-1 text-xs leading-relaxed font-mono whitespace-pre-wrap">
            {volContext.split('\n\n').map((block, i) => {
              if (block.startsWith('VOLATILITY DIVERGENCE:')) {
                return <p key={i} className="text-accent-amber font-semibold mt-2">{block}</p>;
              }
              if (block.startsWith('Microstructure F')) {
                return <p key={i} className="text-accent-blue/80 mt-2">{block}</p>;
              }
              return <p key={i} className="text-accent-blue">{block}</p>;
            })}
          </div>
        </details>
      )}

      {/* Action bar */}
      <div className="flex gap-2 mb-4">
        <CopyButton content={content} />
        <PdfButton contentRef={contentRef} tabLabel={tabLabel} />
      </div>

      {/* Report content */}
      <div ref={contentRef} className="report-markdown text-text-primary text-sm leading-relaxed">
        <ReactMarkdown
          components={{
            h1: ({ children }) => <h1 className="text-xl font-bold text-text-primary mt-6 mb-3 border-b border-border-subtle pb-2">{children}</h1>,
            h2: ({ children }) => <h2 className="text-lg font-bold text-text-primary mt-5 mb-2 border-b border-border-subtle pb-1">{children}</h2>,
            h3: ({ children }) => <h3 className="text-base font-semibold text-text-primary mt-4 mb-2">{children}</h3>,
            h4: ({ children }) => <h4 className="text-sm font-semibold text-text-primary mt-3 mb-1">{children}</h4>,
            p: ({ children }) => <p className="text-text-secondary mb-3">{children}</p>,
            strong: ({ children }) => <strong className="font-semibold text-text-primary">{children}</strong>,
            em: ({ children }) => <em className="text-text-tertiary">{children}</em>,
            ul: ({ children }) => <ul className="list-disc list-inside mb-3 space-y-1 text-text-secondary">{children}</ul>,
            ol: ({ children }) => <ol className="list-decimal list-inside mb-3 space-y-1 text-text-secondary">{children}</ol>,
            li: ({ children }) => <li className="text-text-secondary">{children}</li>,
            blockquote: ({ children }) => <blockquote className="border-l-4 border-accent-blue pl-4 my-3 text-text-tertiary italic">{children}</blockquote>,
            code: ({ className, children }) => {
              const isBlock = className?.includes('language-');
              if (isBlock) {
                return <code className="block bg-bg-primary text-text-primary p-4 rounded-sm overflow-auto text-xs border border-border-subtle my-3">{children}</code>;
              }
              return <code className="bg-bg-primary text-accent-red px-1.5 py-0.5 rounded-sm text-xs">{children}</code>;
            },
            pre: ({ children }) => <pre className="my-3">{children}</pre>,
            table: ({ children }) => (
              <div className="overflow-x-auto my-3">
                <table className="min-w-full border border-border-subtle rounded-sm overflow-hidden">{children}</table>
              </div>
            ),
            thead: ({ children }) => <thead className="bg-bg-primary">{children}</thead>,
            th: ({ children }) => <th className="px-3 py-2 text-left text-xs font-semibold text-text-primary border-b border-border-default">{children}</th>,
            td: ({ children }) => <td className="px-3 py-2 text-xs text-text-secondary border-b border-border-subtle">{children}</td>,
            hr: () => <hr className="my-4 border-border-subtle" />,
            a: ({ href, children }) => <a href={href} className="text-accent-blue underline" target="_blank" rel="noopener noreferrer">{children}</a>,
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
}
