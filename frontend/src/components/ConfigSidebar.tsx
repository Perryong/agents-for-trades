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
    deep: ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash'],
    quick: ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-2.0-flash-lite'],
    defaultDeep: 'gemini-2.5-pro',
    defaultQuick: 'gemini-2.5-flash',
  },
  anthropic: {
    label: 'Anthropic',
    deep: ['claude-sonnet-4-5-20250514', 'claude-opus-4-20250514'],
    quick: ['claude-haiku-4-5-20251001', 'claude-sonnet-4-5-20250514'],
    defaultDeep: 'claude-sonnet-4-5-20250514',
    defaultQuick: 'claude-haiku-4-5-20251001',
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
  const [enableOptions, setEnableOptions] = useState(false);
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
      enable_options: enableOptions,
      llm_provider: llmProvider,
      deep_think_llm: deepThinkLlm,
      quick_think_llm: quickThinkLlm,
    });
  }

  const inputClass =
    'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none';

  return (
    <div className="space-y-6">
      {/* Ticker Symbol */}
      <div className="space-y-1">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
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
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
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
        <legend className="text-sm font-medium text-gray-700 dark:text-gray-300">Analysts</legend>
        {ANALYST_OPTIONS.map(({ id, label }) => (
          <label key={id} className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={analysts.includes(id)}
              onChange={() => toggleAnalyst(id)}
              className="rounded border-gray-300 dark:border-gray-600 text-blue-600"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">{label}</span>
          </label>
        ))}
      </fieldset>

      {/* Enable Options Analysis */}
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={enableOptions}
          onChange={e => setEnableOptions(e.target.checked)}
          className="rounded border-gray-300 dark:border-gray-600 text-blue-600"
        />
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
          Enable Options Analysis
        </span>
      </label>

      {/* LLM Provider */}
      <div className="space-y-1">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
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
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
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
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
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
        className="w-full py-2 px-4 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
      >
        {isRunning ? 'Analyzing...' : 'Analyze'}
      </button>
    </div>
  );
}
