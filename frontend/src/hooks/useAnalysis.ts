import { useReducer, useRef, useCallback } from 'react';
import type { AnalysisState, AnalysisResult, AnalyzeRequest } from '../types';

const initialState: AnalysisState = {
  status: 'idle',
  currentNode: null,
  completedNodes: [],
  result: null,
  errorMsg: null,
};

type Action =
  | { type: 'RESET' }
  | { type: 'STARTED' }
  | { type: 'NODE_START'; node: string }
  | { type: 'NODE_END'; node: string }
  | { type: 'COMPLETE'; result: AnalysisResult }
  | { type: 'ERROR'; message: string };

function reducer(state: AnalysisState, action: Action): AnalysisState {
  switch (action.type) {
    case 'RESET':
      return initialState;
    case 'STARTED':
      return { ...initialState, status: 'running' };
    case 'NODE_START':
      return { ...state, currentNode: action.node };
    case 'NODE_END':
      return {
        ...state,
        currentNode: null,
        completedNodes: [...state.completedNodes, action.node],
      };
    case 'COMPLETE':
      return { ...state, status: 'done', currentNode: null, result: action.result };
    case 'ERROR':
      return { ...state, status: 'error', currentNode: null, errorMsg: action.message };
    default:
      return state;
  }
}

export function useAnalysis() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const esRef = useRef<EventSource | null>(null);
  // Track whether an analysis is running to avoid stale closure in onerror
  const isRunningRef = useRef<boolean>(false);

  const startAnalysis = useCallback(async (request: AnalyzeRequest) => {
    // Close any existing SSE connection
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }

    isRunningRef.current = true;
    dispatch({ type: 'STARTED' });

    // Step 1: Generate client-side run_id (UUID v4 via crypto.randomUUID)
    const runId = crypto.randomUUID();

    // Step 2: POST config to /api/analyze/{run_id}
    try {
      const response = await fetch(`/api/analyze/${runId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const text = await response.text();
        isRunningRef.current = false;
        dispatch({ type: 'ERROR', message: `API error ${response.status}: ${text}` });
        return;
      }
    } catch (err) {
      isRunningRef.current = false;
      dispatch({ type: 'ERROR', message: `Network error: ${err instanceof Error ? err.message : String(err)}` });
      return;
    }

    // Step 3: Open EventSource on GET /api/analyze/{run_id}/stream
    const es = new EventSource(`/api/analyze/${runId}/stream`);
    esRef.current = es;

    es.addEventListener('node_start', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      dispatch({ type: 'NODE_START', node: data.node });
    });

    es.addEventListener('node_end', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      dispatch({ type: 'NODE_END', node: data.node });
    });

    es.addEventListener('complete', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      const result: AnalysisResult = {
        market_report: data.state?.market_report ?? '',
        technical_report: data.state?.technical_report ?? '',
        sentiment_report: data.state?.sentiment_report ?? '',
        news_report: data.state?.news_report ?? '',
        fundamentals_report: data.state?.fundamentals_report ?? '',
        investment_plan: data.state?.investment_plan ?? '',
        trader_investment_plan: data.state?.trader_investment_plan ?? '',
        final_trade_decision: data.state?.final_trade_decision ?? '',
        volatility_report: data.state?.volatility_report ?? '',
        options_flow_report: data.state?.options_flow_report ?? '',
        options_strategy: data.state?.options_strategy ?? '',
        options_legs: data.state?.options_legs ?? '',
        options_pricing_report: data.state?.options_pricing_report ?? '',
        greeks_report: data.state?.greeks_report ?? '',
        signal: data.signal ?? '',
      };
      isRunningRef.current = false;
      dispatch({ type: 'COMPLETE', result });
      es.close();
    });

    es.addEventListener('error', (e: MessageEvent) => {
      // SSE error event — try to parse data if available
      try {
        const data = JSON.parse(e.data);
        isRunningRef.current = false;
        dispatch({ type: 'ERROR', message: data.message || 'Stream error' });
      } catch {
        isRunningRef.current = false;
        dispatch({ type: 'ERROR', message: 'Connection lost' });
      }
      es.close();
    });

    // Native EventSource onerror (connection errors)
    // Uses isRunningRef to avoid stale closure bug — state.status read inside
    // useCallback([]) would always see 'idle' due to closure capture.
    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED && isRunningRef.current) {
        isRunningRef.current = false;
        dispatch({ type: 'ERROR', message: 'Stream connection closed unexpectedly' });
      }
    };
  }, []);

  const reset = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    isRunningRef.current = false;
    dispatch({ type: 'RESET' });
  }, []);

  return { state, startAnalysis, reset };
}
