import { useState, useEffect } from 'react';
import type { AnalyzeRequest } from '../types';
import { TickerAutocomplete } from './TickerAutocomplete';

interface ConfigSidebarProps {
  onAnalyze: (request: AnalyzeRequest) => void;
  isRunning: boolean;
  prefillTicker?: string;  // NEW — from screener pick selection
}

const ANALYST_OPTIONS = [
  { id: 'market', label: 'Market' },
  { id: 'technical', label: 'Technical' },
  { id: 'social', label: 'Social Media' },
  { id: 'news', label: 'News' },
  { id: 'fundamentals', label: 'Fundamentals' },
];

const PROVIDER_MODELS: Record<string, { deep: string[]; quick: string[]; defaultDeep: string; defaultQuick: string; label: string }> = {
  openai: {
    label: 'OpenAI',
    deep: ['gpt-5.2', 'gpt-5', 'gpt-4.1', 'o4-mini', 'o3', 'o3-mini'],
    quick: ['gpt-5-mini', 'gpt-4.1-mini', 'gpt-4.1-nano', 'o4-mini', 'o3-mini'],
    defaultDeep: 'gpt-5.2',
    defaultQuick: 'gpt-5-mini',
  },
  google: {
    label: 'Google',
    deep: ['gemini-3.1-pro-preview', 'gemini-3-flash-preview', 'gemini-2.5-pro', 'gemini-2.5-flash'],
    quick: ['gemini-3-flash-preview', 'gemini-2.5-flash', 'gemini-3.1-flash-lite-preview', 'gemini-2.5-flash-lite'],
    defaultDeep: 'gemini-2.5-pro',
    defaultQuick: 'gemini-2.5-flash',
  },
  anthropic: {
    label: 'Anthropic',
    deep: ['claude-opus-4-6', 'claude-sonnet-4-6', 'claude-opus-4-5', 'claude-sonnet-4-5'],
    quick: ['claude-sonnet-4-6', 'claude-haiku-4-5', 'claude-sonnet-4-5'],
    defaultDeep: 'claude-sonnet-4-6',
    defaultQuick: 'claude-haiku-4-5',
  },
  test: {
    label: 'Test (Mock)',
    deep: ['test-mock'],
    quick: ['test-mock'],
    defaultDeep: 'test-mock',
    defaultQuick: 'test-mock',
  },
};

function todayISODate(): string {
  return new Date().toISOString().slice(0, 10);
}

export function ConfigSidebar({ onAnalyze, isRunning, prefillTicker }: ConfigSidebarProps) {
  const [ticker, setTicker] = useState('');
  const [date, setDate] = useState(todayISODate);
  const [analysts, setAnalysts] = useState<string[]>([
    'market',
    'technical',
    'social',
    'news',
    'fundamentals',
  ]);
  const [llmProvider, setLlmProvider] = useState('openai');
  const [deepThinkLlm, setDeepThinkLlm] = useState('gpt-5.2');
  const [quickThinkLlm, setQuickThinkLlm] = useState('gpt-5-mini');
  useEffect(() => {
    if (prefillTicker) {
      setTicker(prefillTicker.toUpperCase());
    }
  }, [prefillTicker]);

  useEffect(() => {
    const models = PROVIDER_MODELS[llmProvider];
    if (models) {
      setDeepThinkLlm(models.defaultDeep);
      setQuickThinkLlm(models.defaultQuick);
    }
  }, [llmProvider]);

  function toggleAnalyst(id: string) {
    setAnalysts(prev =>
      prev.includes(id) ? prev.filter(a => a !== id) : [...prev, id],
    );
  }

  function handleAnalyze() {
    onAnalyze({
      ticker,
      date,
      analysts,
      llm_provider: llmProvider,
      deep_think_llm: deepThinkLlm,
      quick_think_llm: quickThinkLlm,
    });
  }

  const inputClass =
    'w-full px-3 py-2 border border-border-default rounded-sm text-sm bg-bg-elevated text-text-primary focus:ring-2 focus:ring-accent-blue focus:border-accent-blue outline-none';

  return (
    <div className="space-y-6">
      {/* Ticker Symbol */}
      <div className="space-y-1">
        <label className="block text-sm font-medium text-text-secondary">
          Ticker Symbol
        </label>
        <TickerAutocomplete
          value={ticker}
          onChange={setTicker}
          className={inputClass}
        />
      </div>

      {/* Analysis Date */}
      <div className="space-y-1">
        <label className="block text-sm font-medium text-text-secondary">
          Analysis Date
        </label>
        <input
          type="date"
          value={date}
          onChange={e => setDate(e.target.value)}
          className={inputClass}
        />
      </div>

      {/* Analysts */}
      <fieldset className="space-y-2">
        <legend className="text-sm font-medium text-text-secondary">Analysts</legend>
        {ANALYST_OPTIONS.map(({ id, label }) => (
          <label key={id} className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={analysts.includes(id)}
              onChange={() => toggleAnalyst(id)}
              className="rounded-sm border-border-default text-accent-blue"
            />
            <span className="text-sm text-text-secondary">{label}</span>
          </label>
        ))}
      </fieldset>

      {/* LLM Provider */}
      <div className="space-y-1">
        <label className="block text-sm font-medium text-text-secondary">
          LLM Provider
        </label>
        <select
          value={llmProvider}
          onChange={e => setLlmProvider(e.target.value)}
          className={inputClass}
        >
          {Object.entries(PROVIDER_MODELS).map(([key, { label }]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>
      </div>

      {/* Deep Think Model */}
      <div className="space-y-1">
        <label className="block text-sm font-medium text-text-secondary">
          Deep Think Model
        </label>
        <select
          value={deepThinkLlm}
          onChange={e => setDeepThinkLlm(e.target.value)}
          className={inputClass}
        >
          {(PROVIDER_MODELS[llmProvider]?.deep ?? []).map(model => (
            <option key={model} value={model}>{model}</option>
          ))}
        </select>
      </div>

      {/* Quick Think Model */}
      <div className="space-y-1">
        <label className="block text-sm font-medium text-text-secondary">
          Quick Think Model
        </label>
        <select
          value={quickThinkLlm}
          onChange={e => setQuickThinkLlm(e.target.value)}
          className={inputClass}
        >
          {(PROVIDER_MODELS[llmProvider]?.quick ?? []).map(model => (
            <option key={model} value={model}>{model}</option>
          ))}
        </select>
      </div>

      {/* Analyze Button */}
      <button
        onClick={handleAnalyze}
        disabled={isRunning || !ticker.trim()}
        className="w-full py-2 px-4 bg-accent-blue text-white rounded-sm text-sm font-medium hover:bg-accent-blue/80 disabled:bg-bg-secondary disabled:text-text-tertiary disabled:cursor-not-allowed transition-colors"
      >
        {isRunning ? 'Analyzing...' : 'Analyze'}
      </button>
    </div>
  );
}
