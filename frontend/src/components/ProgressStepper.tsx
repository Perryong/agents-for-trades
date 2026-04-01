import {
  EQUITY_NODES,
  OPTIONS_NODES,
  RESEARCH_NODES,
  TRADING_NODES,
  RISK_NODES,
} from '../types';
import type { AnalysisStatus } from '../types';

interface ProgressStepperProps {
  completedNodes: string[];
  currentNode: string | null;
  enableOptions: boolean;
  status: AnalysisStatus;
}

function getNodeList(enableOptions: boolean): string[] {
  return [
    ...EQUITY_NODES,
    ...(enableOptions ? OPTIONS_NODES : []),
    ...RESEARCH_NODES,
    ...TRADING_NODES,
    ...RISK_NODES,
  ];
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
    <div className={`${baseClass} bg-gray-200 text-gray-400`}>
      <span className="w-2 h-2 rounded-full border border-gray-400 block" />
    </div>
  );
}

export function ProgressStepper({
  completedNodes,
  currentNode,
  enableOptions,
  status,
}: ProgressStepperProps) {
  if (status === 'idle') {
    return (
      <p className="text-sm text-gray-400">
        Configure and click Analyze to start
      </p>
    );
  }

  const nodes = getNodeList(enableOptions);

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
                  ? 'text-gray-700'
                  : nodeStatus === 'running'
                    ? 'text-blue-700 font-medium'
                    : 'text-gray-400'
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
