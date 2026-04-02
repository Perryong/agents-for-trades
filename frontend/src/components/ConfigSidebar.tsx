import { useState, useEffect } from 'react';
import type { AnalyzeRequest } from '../types';

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
        <input
          type="text"
          placeholder="e.g. AAPL"
          value={ticker}
          onChange={e => setTicker(e.target.value.toUpperCase())}
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
          <option value="openai">OpenAI</option>
          <option value="google">Google</option>
          <option value="anthropic">Anthropic</option>
        </select>
      </div>

      {/* Deep Think Model */}
      <div className="space-y-1">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Deep Think Model
        </label>
        <input
          type="text"
          value={deepThinkLlm}
          onChange={e => setDeepThinkLlm(e.target.value)}
          className={inputClass}
        />
      </div>

      {/* Quick Think Model */}
      <div className="space-y-1">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Quick Think Model
        </label>
        <input
          type="text"
          value={quickThinkLlm}
          onChange={e => setQuickThinkLlm(e.target.value)}
          className={inputClass}
        />
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
