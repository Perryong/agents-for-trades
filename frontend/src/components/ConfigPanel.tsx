import { useState } from 'react';
import { useConfig } from '../hooks/useConfig';

function NumberInput({ label, configKey, min, max, step, suffix, config, onUpdate }: {
  label: string; configKey: string; min: number; max: number; step?: number; suffix?: string;
  config: Record<string, unknown> | null;
  onUpdate: (key: string, value: unknown) => Promise<boolean>;
}) {
  const value = config ? Number(config[configKey] ?? 0) : 0;
  return (
    <div className="flex items-center justify-between">
      <span className="text-[13px] text-text-secondary">{label}</span>
      <div className="flex items-center gap-1">
        <input
          type="number"
          value={value}
          min={min}
          max={max}
          step={step ?? 1}
          onChange={e => {
            const v = parseFloat(e.target.value);
            if (!isNaN(v)) onUpdate(configKey, v);
          }}
          className="w-16 px-1 py-0.5 text-[13px] font-mono text-text-primary bg-bg-elevated border border-border-default rounded-sm text-right"
        />
        {suffix && <span className="text-[11px] text-text-tertiary">{suffix}</span>}
      </div>
    </div>
  );
}

export function ConfigPanel() {
  const { config, loading, update } = useConfig();
  const [newTicker, setNewTicker] = useState('');

  if (loading) return <div className="p-3 text-[13px] text-text-tertiary">Loading config...</div>;

  const watchlist = Array.isArray(config?.watchlist) ? (config.watchlist as string[]) : [];

  const addTicker = async () => {
    const t = newTicker.trim().toUpperCase();
    if (!t || watchlist.includes(t)) return;
    const success = await update('watchlist', [...watchlist, t]);
    if (success) setNewTicker('');
  };

  const removeTicker = (ticker: string) => {
    update('watchlist', watchlist.filter(t => t !== ticker));
  };

  return (
    <div className="space-y-4">
      {/* Watchlist */}
      <div>
        <p className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-2">Watchlist</p>
        <div className="flex flex-wrap gap-1 mb-2">
          {watchlist.length === 0 && <span className="text-[11px] text-text-tertiary">No tickers</span>}
          {watchlist.map(t => (
            <span key={t} className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-bg-elevated border border-border-subtle rounded-sm text-[11px] font-mono text-text-primary">
              {t}
              <button onClick={() => removeTicker(t)} className="text-text-tertiary hover:text-accent-red">&times;</button>
            </span>
          ))}
        </div>
        <div className="flex gap-1">
          <input
            value={newTicker}
            onChange={e => setNewTicker(e.target.value.toUpperCase())}
            onKeyDown={e => e.key === 'Enter' && addTicker()}
            placeholder="Add ticker"
            className="flex-1 px-2 py-1 text-[13px] font-mono bg-bg-elevated border border-border-default rounded-sm text-text-primary placeholder:text-text-tertiary"
          />
          <button onClick={addTicker} className="px-2 py-1 text-[11px] text-accent-blue hover:text-accent-blue/80">Add</button>
        </div>
      </div>

      {/* Risk Parameters */}
      <div>
        <p className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-2">Risk Parameters</p>
        <div className="space-y-2">
          <NumberInput label="Stop Loss" configKey="stop_loss_pct" min={0} max={50} step={0.5} suffix="%" config={config} onUpdate={update} />
          <NumberInput label="Max Position" configKey="max_position_pct" min={0} max={100} step={1} suffix="%" config={config} onUpdate={update} />
          <NumberInput label="Max Exposure" configKey="max_portfolio_exposure_pct" min={0} max={100} step={5} suffix="%" config={config} onUpdate={update} />
          <NumberInput label="Min Confidence" configKey="min_confidence_threshold" min={0} max={100} step={5} suffix="%" config={config} onUpdate={update} />
        </div>
      </div>

      {/* Agent Weights */}
      <div>
        <p className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-2">Agent Weights</p>
        <div className="space-y-2">
          <NumberInput label="Fundamentals" configKey="agent_weight_fundamentals" min={0} max={1} step={0.1} config={config} onUpdate={update} />
          <NumberInput label="News" configKey="agent_weight_news" min={0} max={1} step={0.1} config={config} onUpdate={update} />
          <NumberInput label="Market" configKey="agent_weight_market" min={0} max={1} step={0.1} config={config} onUpdate={update} />
          <NumberInput label="Social" configKey="agent_weight_social" min={0} max={1} step={0.1} config={config} onUpdate={update} />
        </div>
      </div>

      {/* Schedule */}
      <div>
        <p className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-2">Schedule</p>
        <div className="flex items-center justify-between">
          <span className="text-[13px] text-text-secondary">Pre-market run</span>
          <input
            type="time"
            value={String(config?.schedule_time ?? '08:00')}
            onChange={e => update('schedule_time', e.target.value)}
            className="px-2 py-0.5 text-[13px] font-mono bg-bg-elevated border border-border-default rounded-sm text-text-primary"
          />
        </div>
      </div>
    </div>
  );
}
