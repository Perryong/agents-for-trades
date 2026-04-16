import { useState } from 'react';
import { TickerAutocomplete } from './TickerAutocomplete';

const STORAGE_KEY = 'chart_recent_tickers';
const MAX_RECENT = 5;

function loadRecent(): string[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];
    const parsed = JSON.parse(stored);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveRecent(tickers: string[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tickers));
  } catch {
    // localStorage may be unavailable
  }
}

interface ChartTickerPickerProps {
  value: string;
  onChange: (ticker: string) => void;
}

export function ChartTickerPicker({ value, onChange }: ChartTickerPickerProps) {
  const [recentTickers, setRecentTickers] = useState<string[]>(loadRecent);

  function handleSelect(ticker: string) {
    if (!ticker) return;
    // Prepend, deduplicate, cap at MAX_RECENT
    const updated = [ticker, ...recentTickers.filter(t => t !== ticker)].slice(0, MAX_RECENT);
    setRecentTickers(updated);
    saveRecent(updated);
    onChange(ticker);
  }

  return (
    <div className="flex flex-col gap-2">
      <TickerAutocomplete
        value={value}
        onChange={handleSelect}
        className="w-48 px-3 py-1.5 text-sm border border-border-default rounded-sm bg-bg-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-blue"
      />
      {recentTickers.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {recentTickers.map(ticker => (
            <button
              key={ticker}
              onClick={() => handleSelect(ticker)}
              className="px-2 py-0.5 text-xs rounded-full bg-bg-primary text-text-secondary hover:bg-bg-hover hover:text-accent-blue transition-colors"
            >
              {ticker}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
