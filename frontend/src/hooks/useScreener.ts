import { useReducer, useCallback } from 'react';
import type { ScreenerState, ScreenerPick } from '../types';

const initialState: ScreenerState = {
  status: 'idle',
  picks: [],
  screenedAt: null,
  errorMsg: null,
};

type ScreenerAction =
  | { type: 'FETCH_START' }
  | { type: 'FETCH_SUCCESS'; picks: ScreenerPick[]; screenedAt: string }
  | { type: 'FETCH_ERROR'; message: string }
  | { type: 'RESET' };

function reducer(state: ScreenerState, action: ScreenerAction): ScreenerState {
  switch (action.type) {
    case 'FETCH_START':
      return { ...state, status: 'loading', errorMsg: null };
    case 'FETCH_SUCCESS':
      return {
        ...state,
        status: 'done',
        picks: action.picks,
        screenedAt: action.screenedAt,
        errorMsg: null,
      };
    case 'FETCH_ERROR':
      return { ...state, status: 'error', errorMsg: action.message };
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

export function useScreener() {
  const [state, dispatch] = useReducer(reducer, initialState);

  const runScreen = useCallback(async (provider = 'google', model = 'gemini-2.5-flash', strategy = 'momentum', maxPicks = 5) => {
    dispatch({ type: 'FETCH_START' });
    try {
      const res = await fetch('/api/screen', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          max_picks: maxPicks,
          universe: 'sp500',
          strategy,
          llm_provider: provider,
          quick_think_llm: model,
        }),
      });

      if (!res.ok) {
        dispatch({ type: 'FETCH_ERROR', message: `API error ${res.status}` });
        return;
      }

      const json = await res.json();

      if (json.status === 'error') {
        dispatch({
          type: 'FETCH_ERROR',
          message: json.data?.error ?? 'Screener error',
        });
        return;
      }

      dispatch({
        type: 'FETCH_SUCCESS',
        picks: json.data.picks,
        screenedAt: json.screened_at,
      });
    } catch (err) {
      dispatch({
        type: 'FETCH_ERROR',
        message: err instanceof Error ? err.message : String(err),
      });
    }
  }, []);

  return { state, runScreen };
}
