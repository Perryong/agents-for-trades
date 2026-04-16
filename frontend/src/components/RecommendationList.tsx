import { useState, useEffect, useMemo } from 'react';
import { RecommendationCard } from './RecommendationCard';
import { NoTradeSummary } from './NoTradeSummary';
import type { Recommendation } from '../types';

interface RecommendationListProps {
  recommendations: Recommendation[];
  loading: boolean;
  error: string | null;
  onApprove: (id: number) => void;
  onSkip: (id: number) => void;
}

export function RecommendationList({ recommendations, loading, error, onApprove, onSkip }: RecommendationListProps) {
  const [focusedIndex, setFocusedIndex] = useState<number>(-1);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  // Sort: pending first (by confidence desc), then approved, then skipped/expired at bottom
  const sorted = useMemo(() => {
    const pending = recommendations.filter(r => r.status === 'pending');
    const approved = recommendations.filter(r => r.status === 'approved');
    const rest = recommendations.filter(r => r.status === 'skipped' || r.status === 'expired');
    return [...pending, ...approved, ...rest];
  }, [recommendations]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = (document.activeElement?.tagName ?? '').toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return;
      if (sorted.length === 0) return;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setFocusedIndex(prev => Math.min(prev + 1, sorted.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setFocusedIndex(prev => Math.max(prev - 1, 0));
          break;
        case 'Escape':
          if (expandedId != null) {
            setExpandedId(null);
          } else {
            setFocusedIndex(-1);
          }
          break;
        case 'Enter':
          if (focusedIndex >= 0 && focusedIndex < sorted.length) {
            const rec = sorted[focusedIndex];
            setExpandedId(prev => prev === rec.id ? null : rec.id);
          }
          break;
        case 'a':
        case 'A':
          if (focusedIndex >= 0 && focusedIndex < sorted.length) {
            const rec = sorted[focusedIndex];
            if (rec.status === 'pending' && rec.direction) onApprove(rec.id);
          }
          break;
        case 's':
        case 'S':
          if (focusedIndex >= 0 && focusedIndex < sorted.length) {
            const rec = sorted[focusedIndex];
            if (rec.status === 'pending' && rec.direction) onSkip(rec.id);
          }
          break;
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [sorted, focusedIndex, expandedId, onApprove, onSkip]);

  if (loading) {
    return (
      <div className="space-y-2 p-4">
        {[1, 2, 3].map(i => (
          <div key={i} className="h-24 bg-bg-hover rounded-sm animate-pulse" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4">
        <p className="text-[13px] text-accent-red">Failed to load recommendations: {error}</p>
      </div>
    );
  }

  if (sorted.length === 0) {
    return (
      <div className="p-4">
        <p className="text-[13px] text-text-tertiary">
          No recommendations — run an analysis to generate recommendations
        </p>
      </div>
    );
  }

  // Check for no-trade discipline view
  const hasActionable = sorted.some(r => r.direction && r.status === 'pending');
  const allNoTrade = sorted.length > 0 && sorted.every(r => !r.direction);

  if (allNoTrade) {
    return <NoTradeSummary recommendations={sorted} />;
  }

  return (
    <div className="space-y-2 p-4 overflow-y-auto">
      {!hasActionable && sorted.length > 0 && <NoTradeSummary recommendations={sorted} />}
      {sorted.map((rec, idx) => (
        <RecommendationCard
          key={rec.id}
          recommendation={rec}
          focused={idx === focusedIndex}
          expanded={rec.id === expandedId}
          onToggleExpand={() => setExpandedId(prev => prev === rec.id ? null : rec.id)}
          onApprove={() => onApprove(rec.id)}
          onSkip={() => onSkip(rec.id)}
        />
      ))}
    </div>
  );
}
