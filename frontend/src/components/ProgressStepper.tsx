import { getNodeList } from '../types';
import type { AnalysisStatus } from '../types';

interface ProgressStepperProps {
  completedNodes: string[];
  currentNode: string | null;
  status: AnalysisStatus;
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
      <div className={`${baseClass} bg-green-500 text-white`}>&#10003;</div>
    );
  }
  if (nodeStatus === 'running') {
    return (
      <div className={`${baseClass} bg-blue-500 text-white animate-pulse`}>
        &hellip;
      </div>
    );
  }
  return (
    <div className={`${baseClass} bg-gray-200 dark:bg-gray-600 text-gray-400 dark:text-gray-500`}>
      <span className="w-2 h-2 rounded-full border border-gray-400 dark:border-gray-500 block" />
    </div>
  );
}

export function ProgressStepper({
  completedNodes,
  currentNode,
  status,
}: ProgressStepperProps) {
  if (status === 'idle') {
    return (
      <p className="text-sm text-gray-400 dark:text-gray-500">
        Configure and click Analyze to start
      </p>
    );
  }

  const nodes = getNodeList();

  return (
    <div className="space-y-1">
      {nodes.map(node => {
        const nodeStatus = getNodeStatus(node, completedNodes, currentNode);
        return (
          <div key={node} className="flex items-center gap-3 py-1">
            <StatusDot nodeStatus={nodeStatus} />
            <span
              className={`text-sm ${
                nodeStatus === 'done'
                  ? 'text-gray-700 dark:text-gray-300'
                  : nodeStatus === 'running'
                    ? 'text-blue-700 dark:text-blue-400 font-medium'
                    : 'text-gray-400 dark:text-gray-500'
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
