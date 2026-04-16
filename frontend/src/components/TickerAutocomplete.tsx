import { useState, useEffect, useRef } from 'react';

interface TickerInfo {
  ticker: string;
  name: string;
  sector: string;
}

interface TickerAutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

const LOGO_URL = (ticker: string) =>
  `https://assets.parqet.com/logos/symbol/${ticker}`;

export function TickerAutocomplete({ value, onChange, className }: TickerAutocompleteProps) {
  const [allTickers, setAllTickers] = useState<TickerInfo[]>([]);
  const [filtered, setFiltered] = useState<TickerInfo[]>([]);
  const [open, setOpen] = useState(false);
  const [highlightIdx, setHighlightIdx] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  useEffect(() => {
    fetch('/api/tickers')
      .then(res => res.json())
      .then(data => { if (Array.isArray(data)) setAllTickers(data); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!value.trim()) {
      setFiltered([]);
      setOpen(false);
      return;
    }
    const q = value.toUpperCase();
    const matches = allTickers.filter(
      t => t.ticker.startsWith(q) || t.name.toUpperCase().includes(q)
    ).slice(0, 8);
    setFiltered(matches);
    setOpen(matches.length > 0);
    setHighlightIdx(-1);
  }, [value, allTickers]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Scroll highlighted item into view
  useEffect(() => {
    if (highlightIdx >= 0 && listRef.current) {
      const item = listRef.current.children[highlightIdx] as HTMLElement;
      item?.scrollIntoView({ block: 'nearest' });
    }
  }, [highlightIdx]);

  function select(ticker: string) {
    onChange(ticker);
    setOpen(false);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!open) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightIdx(i => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightIdx(i => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && highlightIdx >= 0) {
      e.preventDefault();
      select(filtered[highlightIdx].ticker);
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  }

  return (
    <div ref={wrapperRef} className="relative">
      <input
        type="text"
        placeholder="e.g. AAPL"
        value={value}
        onChange={e => onChange(e.target.value.toUpperCase())}
        onFocus={() => { if (filtered.length > 0) setOpen(true); }}
        onKeyDown={handleKeyDown}
        className={className}
        autoComplete="off"
      />
      {open && (
        <ul
          ref={listRef}
          className="absolute z-50 left-0 right-0 mt-1 max-h-64 overflow-auto rounded-sm border border-border-default bg-bg-elevated shadow-lg"
        >
          {filtered.map((t, i) => (
            <li
              key={t.ticker}
              onMouseDown={() => select(t.ticker)}
              onMouseEnter={() => setHighlightIdx(i)}
              className={`flex items-center gap-3 px-3 py-2 cursor-pointer text-sm ${
                i === highlightIdx
                  ? 'bg-accent-blue/10'
                  : 'hover:bg-bg-hover'
              }`}
            >
              <img
                src={LOGO_URL(t.ticker)}
                alt=""
                className="w-6 h-6 rounded-sm object-contain flex-shrink-0 bg-white"
                onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-text-primary">{t.ticker}</span>
                  <span className="text-xs text-text-tertiary truncate">{t.sector}</span>
                </div>
                <div className="text-xs text-text-secondary truncate">{t.name}</div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
