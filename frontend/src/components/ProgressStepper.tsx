import { getNodeList } from '../types';
import type { AnalysisStatus } from '../types';

interface ProgressStepperProps {
  completedNodes: string[];
  currentNode: string | null;
  status: AnalysisStatus;
  elapsedMs?: number;
  estimatedTotalMs?: number;
}

type NodeStatus = 'done' | 'running' | 'pending';

function getNodeStatus(
  node: string,
  completedNodes: string[],
  currentNode: string | null,
): NodeStatus {
  if (completedNodes.includes(node)) return 'done';
  if (currentNode === node) return 'running';
  return 'pending';
}

function StatusDot({ nodeStatus }: { nodeStatus: NodeStatus }) {
  const baseClass =
    'w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0';

  if (nodeStatus === 'done') {
    return (
      <div className={`${baseClass} bg-accent-green text-white`}>&#10003;</div>
    );
  }
  if (nodeStatus === 'running') {
    return (
      <div className={`${baseClass} bg-accent-blue text-white animate-pulse`}>
        &hellip;
      </div>
    );
  }
  return (
    <div className={`${baseClass} bg-bg-secondary text-text-tertiary`}>
      <span className="w-2 h-2 rounded-full border border-border-subtle block" />
    </div>
  );
}

function formatEtr(remainingMs: number): string {
  if (remainingMs <= 0) return 'finishing...';
  const mins = Math.ceil(remainingMs / 60_000);
  return `~${mins} min remaining`;
}

export function ProgressStepper({
  completedNodes,
  currentNode,
  status,
  elapsedMs,
  estimatedTotalMs,
}: ProgressStepperProps) {
  if (status === 'idle') {
    return (
      <p className="text-sm text-text-tertiary">
        Configure and click Analyze to start
      </p>
    );
  }

  const nodes = getNodeList();
  const etrText = (status === 'running' && elapsedMs != null && estimatedTotalMs != null && estimatedTotalMs > 0)
    ? formatEtr(estimatedTotalMs - elapsedMs)
    : null;

  return (
    <div className="space-y-1">
      {etrText && (
        <p className="text-[11px] font-mono text-text-secondary mb-1">{etrText}</p>
      )}
      {nodes.map(node => {
        const nodeStatus = getNodeStatus(node, completedNodes, currentNode);
        return (
          <div key={node} className="flex items-center gap-3 py-1">
            <StatusDot nodeStatus={nodeStatus} />
            <span
              className={`text-sm ${
                nodeStatus === 'done'
                  ? 'text-text-primary'
                  : nodeStatus === 'running'
                    ? 'text-accent-blue font-medium'
                    : 'text-text-tertiary'
              }`}
            >
              {node}
            </span>
          </div>
        );
      })}
    </div>
  );
}
