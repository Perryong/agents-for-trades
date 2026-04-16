import { useEffect, useState } from 'react';

interface AgentPerf {
  agent_name: string;
  accuracy: number;
  avg_confidence: number;
  total: number;
}

export function AgentPerformanceTable() {
  const [agents, setAgents] = useState<AgentPerf[]>([]);

  useEffect(() => {
    // Compute agent accuracy from predictions/performance data
    fetch('/api/predictions/performance')
      .then(res => res.ok ? res.json() : [])
      .then((preds: Array<{ agent_signals?: Array<{ agent_name: string; signal: string; confidence: number }>; outcome: string | null }>) => {
        // Note: prediction performance doesn't include agent_signals directly
        // Use agent-durations as a proxy for which agents have participated
        return fetch('/api/analysis/agent-durations').then(r => r.ok ? r.json() : []);
      })
      .then((durations: Array<{ agent_name: string; avg_duration_ms: number; sample_count: number }>) => {
        // Show agent participation stats (accuracy requires deeper linking)
        setAgents(durations.map(d => ({
          agent_name: d.agent_name,
          accuracy: 0, // Would require agent_results joined with trade outcomes
          avg_confidence: 0,
          total: d.sample_count,
        })));
      })
      .catch(() => {});
  }, []);

  if (agents.length === 0) return null;

  return (
    <div className="bg-bg-elevated border border-border-subtle rounded-sm p-3">
      <p className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-2">Agent Performance</p>
      <table className="w-full text-[13px]">
        <thead>
          <tr className="text-[10px] text-text-tertiary uppercase tracking-wider">
            <th className="text-left pb-2">Agent</th>
            <th className="text-right pb-2">Runs</th>
            <th className="text-right pb-2">Avg Duration</th>
          </tr>
        </thead>
        <tbody>
          {agents.map(a => (
            <tr key={a.agent_name} className="border-t border-border-subtle">
              <td className="py-1 text-text-primary">{a.agent_name}</td>
              <td className="py-1 text-right font-mono text-text-secondary">{a.total}</td>
              <td className="py-1 text-right font-mono text-text-secondary">—</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
