interface StatusBarProps {
  sessionSummary?: string;
  lastRunTime?: string;
  pipelineStatus?: string;
}

function formatTime(isoOrLabel: string | undefined): string {
  if (!isoOrLabel) return '—';
  try {
    const date = new Date(isoOrLabel);
    if (isNaN(date.getTime())) return isoOrLabel;
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return isoOrLabel;
  }
}

export function StatusBar({ sessionSummary, lastRunTime, pipelineStatus }: StatusBarProps) {
  return (
    <footer className="h-[28px] flex items-center px-4 border-t border-border-subtle bg-bg-primary flex-shrink-0">
      <div className="flex items-center gap-4 w-full text-[11px] text-text-tertiary font-mono">
        {/* Session summary */}
        <span>{sessionSummary || '—'}</span>

        <span className="flex-1" />

        {/* Pipeline status */}
        {pipelineStatus && <span>{pipelineStatus}</span>}
        <span>Last run: {formatTime(lastRunTime)}</span>

        {/* Health indicator */}
        <span className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-accent-green" />
          Online
        </span>
      </div>
    </footer>
  );
}
